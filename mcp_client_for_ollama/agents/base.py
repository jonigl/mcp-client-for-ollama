"""Base class for specialized subagents."""

import asyncio
from contextlib import AsyncExitStack
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.panel import Panel
import ollama

from ..server.connector import ServerConnector
from ..tools.manager import ToolManager
from ..models.manager import ModelManager
from ..models.config_manager import ModelConfigManager


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
        parent_exit_stack: Optional[AsyncExitStack] = None
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
        if self._owns_exit_stack:
            await self.exit_stack.aclose()
    
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
            "task_count": len(self.chat_history)
        }
