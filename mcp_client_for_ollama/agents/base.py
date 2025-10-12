"""Base class for specialized subagents."""

import asyncio
from contextlib import AsyncExitStack
from typing import Dict, List, Optional, Any, Callable
from rich.console import Console
from rich.panel import Panel
import ollama
from pathlib import Path

from ..server.connector import ServerConnector
from ..tools.manager import ToolManager
from ..models.manager import ModelManager
from ..models.config_manager import ModelConfigManager
from .memory import AgentMemory
from .communication import MessageBroker, AgentMessage, MessageType


class SubAgent:
    """Base class for specialized subagents.
    
    SubAgents are specialized instances that can be configured for specific tasks,
    with their own tool selections, system prompts, and MCP server connections.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        model: str,
        system_prompt: str,
        console: Optional[Console] = None,
        ollama_client: Optional[ollama.AsyncClient] = None,
        parent_exit_stack: Optional[AsyncExitStack] = None,
        message_broker: Optional[MessageBroker] = None,
        enable_memory: bool = True
    ):
        """Initialize a SubAgent.
        
        Args:
            name: Unique name for the subagent
            description: Description of the subagent's purpose
            model: Ollama model to use for this agent
            system_prompt: System prompt defining the agent's behavior
            console: Rich console for output (optional, creates new if None)
            ollama_client: Ollama client (optional, creates new if None)
            parent_exit_stack: Parent's exit stack for resource management
            message_broker: Message broker for agent communication
            enable_memory: Whether to enable persistent memory
        """
        self.name = name
        self.description = description
        self.console = console or Console()
        self.ollama = ollama_client
        
        # Create agent's own exit stack or use parent's
        self.exit_stack = parent_exit_stack or AsyncExitStack()
        self._owns_exit_stack = parent_exit_stack is None
        
        # Initialize managers for this agent
        self.server_connector = ServerConnector(self.exit_stack, self.console)
        self.model_manager = ModelManager(
            console=self.console,
            default_model=model,
            ollama=self.ollama
        )
        self.model_config_manager = ModelConfigManager(console=self.console)
        self.tool_manager = ToolManager(
            console=self.console,
            server_connector=self.server_connector
        )
        
        # Set system prompt
        self.model_config_manager.system_prompt = system_prompt
        
        # Agent state
        self.sessions = {}
        self.chat_history = []
        self.enabled_tools: List[str] = []
        self.server_configs: List[Dict[str, Any]] = []
        
        # Enhanced multi-agent capabilities
        self.message_broker = message_broker
        self.memory = AgentMemory(name) if enable_memory else None
        self.message_handlers: Dict[MessageType, Callable] = {}
        self.is_autonomous = False
        self._message_listener_task: Optional[asyncio.Task] = None
        
        # Register with message broker if provided
        if self.message_broker:
            self.message_broker.register_agent(self.name)
        
    async def connect_to_servers(
        self,
        server_paths: Optional[List[str]] = None,
        server_urls: Optional[List[str]] = None,
        config_path: Optional[str] = None
    ) -> bool:
        """Connect the agent to specified MCP servers.
        
        Args:
            server_paths: List of paths to server scripts
            server_urls: List of URLs for SSE or HTTP servers
            config_path: Path to server configuration file
            
        Returns:
            bool: True if at least one server connected successfully
        """
        sessions, available_tools, enabled_tools = await self.server_connector.connect_to_servers(
            server_paths=server_paths,
            server_urls=server_urls,
            config_path=config_path,
            auto_discovery=False
        )
        
        self.sessions = sessions
        self.tool_manager.set_available_tools(available_tools)
        self.tool_manager.set_enabled_tools(enabled_tools)
        
        return len(sessions) > 0
    
    def enable_tools(self, tool_names: List[str]) -> None:
        """Enable specific tools for this agent.
        
        Args:
            tool_names: List of tool names to enable
        """
        for tool_name in tool_names:
            self.tool_manager.set_tool_status(tool_name, True)
    
    def disable_tools(self, tool_names: List[str]) -> None:
        """Disable specific tools for this agent.
        
        Args:
            tool_names: List of tool names to disable
        """
        for tool_name in tool_names:
            self.tool_manager.set_tool_status(tool_name, False)
    
    async def execute_task(self, task: str) -> str:
        """Execute a task using this agent.
        
        Args:
            task: The task description/query to execute
            
        Returns:
            str: The agent's response
        """
        # Create message with task
        messages = [{
            "role": "user",
            "content": task
        }]
        
        # Add system prompt
        system_prompt = self.model_config_manager.get_system_prompt()
        if system_prompt:
            messages.insert(0, {
                "role": "system",
                "content": system_prompt
            })
        
        # Get enabled tools
        enabled_tool_objects = self.tool_manager.get_enabled_tool_objects()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in enabled_tool_objects]
        
        # Get current model
        model = self.model_manager.get_current_model()
        
        # Get model options
        model_options = self.model_config_manager.get_ollama_options()
        
        # Execute query
        chat_params = {
            "model": model,
            "messages": messages,
            "stream": False,
            "tools": available_tools,
            "options": model_options
        }
        
        response = await self.ollama.chat(**chat_params)
        
        # Handle tool calls if present
        if response.get('message', {}).get('tool_calls'):
            tool_calls = response['message']['tool_calls']
            
            for tool_call in tool_calls:
                tool_name = tool_call['function']['name']
                tool_args = tool_call['function']['arguments']
                
                # Parse server name and actual tool name
                server_name, actual_tool_name = tool_name.split('.', 1) if '.' in tool_name else (None, tool_name)
                
                if not server_name or server_name not in self.sessions:
                    self.console.print(f"[red]Agent {self.name}: Unknown server for tool {tool_name}[/red]")
                    continue
                
                # Call the tool
                result = await self.sessions[server_name]["session"].call_tool(actual_tool_name, tool_args)
                tool_response = f"{result.content[0].text}"
                
                # Add tool response to messages
                messages.append({
                    "role": "tool",
                    "content": tool_response,
                    "name": tool_name
                })
            
            # Get final response with tool results
            chat_params_followup = {
                "model": model,
                "messages": messages,
                "stream": False,
                "options": model_options
            }
            
            response = await self.ollama.chat(**chat_params_followup)
        
        response_text = response.get('message', {}).get('content', '')
        
        # Store in history
        self.chat_history.append({
            "query": task,
            "response": response_text
        })
        
        return response_text
    
    async def cleanup(self) -> None:
        """Clean up agent resources."""
        # Stop message listener
        if self._message_listener_task:
            self._message_listener_task.cancel()
            try:
                await self._message_listener_task
            except asyncio.CancelledError:
                pass
        
        # Save memory if enabled
        if self.memory:
            memory_dir = Path.home() / ".ollmcp" / "agent_memory"
            await self.memory.save_to_file(memory_dir / f"{self.name}.json")
        
        # Unregister from broker
        if self.message_broker:
            self.message_broker.unregister_agent(self.name)
        
        if self._owns_exit_stack:
            await self.exit_stack.aclose()
    
    async def send_message(
        self,
        recipient: str,
        message_type: MessageType,
        content: Dict[str, Any],
        thread_id: Optional[str] = None
    ) -> bool:
        """Send a message to another agent.
        
        Args:
            recipient: Name of the recipient agent
            message_type: Type of message
            content: Message content
            thread_id: Optional thread ID for conversation tracking
            
        Returns:
            bool: True if message sent successfully
        """
        if not self.message_broker:
            self.console.print("[yellow]No message broker configured[/yellow]")
            return False
        
        message = AgentMessage(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            content=content,
            thread_id=thread_id
        )
        
        return await self.message_broker.send_message(message)
    
    async def receive_message(self, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """Receive a message.
        
        Args:
            timeout: Optional timeout in seconds
            
        Returns:
            AgentMessage or None
        """
        if not self.message_broker:
            return None
        
        return await self.message_broker.receive_message(self.name, timeout)
    
    async def delegate_task(self, recipient: str, task: str, thread_id: Optional[str] = None) -> bool:
        """Delegate a task to another agent.
        
        Args:
            recipient: Name of agent to delegate to
            task: Task description
            thread_id: Optional thread ID
            
        Returns:
            bool: True if delegated successfully
        """
        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.TASK_REQUEST,
            content={"task": task},
            thread_id=thread_id
        )
    
    async def share_information(self, recipient: str, information: Dict[str, Any]) -> bool:
        """Share information with another agent.
        
        Args:
            recipient: Name of agent to share with
            information: Information to share
            
        Returns:
            bool: True if shared successfully
        """
        return await self.send_message(
            recipient=recipient,
            message_type=MessageType.INFORMATION_SHARE,
            content=information
        )
    
    def register_message_handler(self, message_type: MessageType, handler: Callable) -> None:
        """Register a handler for a specific message type.
        
        Args:
            message_type: Type of message to handle
            handler: Async function to handle the message
        """
        self.message_handlers[message_type] = handler
    
    async def _message_listener(self) -> None:
        """Background task to listen for messages."""
        while True:
            try:
                message = await self.receive_message(timeout=1.0)
                if message:
                    await self._handle_message(message)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.console.print(f"[red]Error in message listener: {str(e)}[/red]")
    
    async def _handle_message(self, message: AgentMessage) -> None:
        """Handle a received message.
        
        Args:
            message: Message to handle
        """
        # Use custom handler if registered
        if message.message_type in self.message_handlers:
            await self.message_handlers[message.message_type](message)
            return
        
        # Default handling
        if message.message_type == MessageType.TASK_REQUEST:
            task = message.content.get("task", "")
            if task:
                try:
                    result = await self.execute_task(task)
                    await self.send_message(
                        recipient=message.sender,
                        message_type=MessageType.TASK_RESPONSE,
                        content={"result": result, "task_id": message.id},
                        thread_id=message.thread_id
                    )
                except Exception as e:
                    await self.send_message(
                        recipient=message.sender,
                        message_type=MessageType.ERROR_REPORT,
                        content={"error": str(e), "task_id": message.id},
                        thread_id=message.thread_id
                    )
    
    def start_autonomous_mode(self) -> None:
        """Start autonomous mode with message listening."""
        if not self.message_broker:
            self.console.print("[yellow]Cannot start autonomous mode without message broker[/yellow]")
            return
        
        if self._message_listener_task:
            return  # Already running
        
        self.is_autonomous = True
        self._message_listener_task = asyncio.create_task(self._message_listener())
        self.console.print(f"[green]Agent '{self.name}' started in autonomous mode[/green]")
    
    def stop_autonomous_mode(self) -> None:
        """Stop autonomous mode."""
        self.is_autonomous = False
        if self._message_listener_task:
            self._message_listener_task.cancel()
            self._message_listener_task = None
        self.console.print(f"[yellow]Agent '{self.name}' stopped autonomous mode[/yellow]")
    
    async def remember(self, content: str, importance: int = 1, tags: Optional[List[str]] = None) -> None:
        """Store information in agent memory.
        
        Args:
            content: Content to remember
            importance: Importance level (1-5)
            tags: Optional tags for categorization
        """
        if self.memory:
            await self.memory.add_memory(content, importance, tags)
    
    async def recall(self, query: Optional[str] = None, tags: Optional[List[str]] = None, limit: int = 5) -> str:
        """Recall information from memory.
        
        Args:
            query: Optional search query
            tags: Optional tags to filter by
            limit: Maximum number of memories to recall
            
        Returns:
            str: Formatted memory content
        """
        if not self.memory:
            return "Memory not enabled for this agent"
        
        memories = await self.memory.search_memories(query, tags, limit=limit)
        
        if not memories:
            return "No relevant memories found"
        
        result = []
        for mem in memories:
            result.append(f"- {mem.content} (importance: {mem.importance})")
        
        return "\n".join(result)
    
    async def load_memory(self) -> bool:
        """Load memory from persistent storage.
        
        Returns:
            bool: True if loaded successfully
        """
        if not self.memory:
            return False
        
        memory_dir = Path.home() / ".ollmcp" / "agent_memory"
        filepath = memory_dir / f"{self.name}.json"
        
        return await self.memory.load_from_file(filepath)
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information.
        
        Returns:
            Dict containing agent information
        """
        return {
            "name": self.name,
            "description": self.description,
            "model": self.model_manager.get_current_model(),
            "system_prompt": self.model_config_manager.get_system_prompt(),
            "enabled_tools": list(self.tool_manager.get_enabled_tools().keys()),
            "connected_servers": list(self.sessions.keys()),
            "task_count": len(self.chat_history),
            "autonomous": self.is_autonomous,
            "memory_enabled": self.memory is not None,
            "pending_messages": self.message_broker.get_pending_messages(self.name) if self.message_broker else 0
        }

