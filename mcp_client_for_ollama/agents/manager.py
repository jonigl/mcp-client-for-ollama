"""Agent manager for creating and coordinating subagents."""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import ollama
from contextlib import AsyncExitStack

from .base import SubAgent
from .web3_audit import Web3AuditAgent
from .researcher import ResearcherAgent
from .coder import CoderAgent
from .writer import WriterAgent
from .tester import TesterAgent
from .reviewer import ReviewerAgent
from .filesystem import FileSystemAgent
from .rag import RAGAgent
from .communication import MessageBroker
from .orchestrator import AgentOrchestrator


class AgentManager:
    """Manages creation and coordination of specialized subagents."""
    
    def __init__(
        self,
        console: Console,
        ollama_client: ollama.AsyncClient,
        exit_stack: AsyncExitStack
    ):
        """Initialize the agent manager.
        
        Args:
            console: Rich console for output
            ollama_client: Ollama client instance
            exit_stack: Exit stack for resource management
        """
        self.console = console
        self.ollama = ollama_client
        self.exit_stack = exit_stack
        self.agents: Dict[str, SubAgent] = {}
        
        # Multi-agent system components
        self.message_broker = MessageBroker()
        self.orchestrator = AgentOrchestrator(console, self.message_broker)
    
    def create_agent(
        self,
        agent_type: str,
        name: str,
        model: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[SubAgent]:
        """Create a new specialized agent.
        
        Args:
            agent_type: Type of agent ("web3_audit", "researcher", "coder", "writer", "tester", "reviewer", "filesystem", "rag", "base")
            name: Unique name for the agent
            model: Ollama model to use
            config: Additional configuration options
            
        Returns:
            SubAgent: The created agent, or None if creation failed
        """
        if name in self.agents:
            self.console.print(f"[yellow]Agent '{name}' already exists[/yellow]")
            return None
        
        try:
            # Common parameters
            common_params = {
                "name": name,
                "console": self.console,
                "ollama_client": self.ollama,
                "parent_exit_stack": self.exit_stack,
                "message_broker": self.message_broker
            }
            
            if agent_type == "web3_audit":
                agent = Web3AuditAgent(
                    model=model or "qwen2.5:7b",
                    custom_prompt=config.get("system_prompt") if config else None,
                    **common_params
                )
            elif agent_type == "researcher":
                agent = ResearcherAgent(
                    model=model or "qwen2.5:7b",
                    custom_prompt=config.get("system_prompt") if config else None,
                    **common_params
                )
            elif agent_type == "coder":
                agent = CoderAgent(
                    model=model or "qwen2.5-coder:7b",
                    custom_prompt=config.get("system_prompt") if config else None,
                    **common_params
                )
            elif agent_type == "writer":
                agent = WriterAgent(
                    model=model or "qwen2.5:7b",
                    custom_prompt=config.get("system_prompt") if config else None,
                    **common_params
                )
            elif agent_type == "tester":
                agent = TesterAgent(
                    model=model or "qwen2.5:7b",
                    custom_prompt=config.get("system_prompt") if config else None,
                    **common_params
                )
            elif agent_type == "reviewer":
                agent = ReviewerAgent(
                    model=model or "qwen2.5:7b",
                    custom_prompt=config.get("system_prompt") if config else None,
                    **common_params
                )
            elif agent_type == "filesystem":
                agent = FileSystemAgent(
                    model=model or "qwen2.5:7b",
                    custom_prompt=config.get("system_prompt") if config else None,
                    **common_params
                )
            elif agent_type == "rag":
                agent = RAGAgent(
                    model=model or "qwen2.5:7b",
                    custom_prompt=config.get("system_prompt") if config else None,
                    **common_params
                )
            elif agent_type == "base":
                if not config or "description" not in config or "system_prompt" not in config:
                    self.console.print(
                        "[red]Base agent requires 'description' and 'system_prompt' in config[/red]"
                    )
                    return None
                
                agent = SubAgent(
                    description=config["description"],
                    model=model or "qwen2.5:7b",
                    system_prompt=config["system_prompt"],
                    **common_params
                )
            else:
                self.console.print(f"[red]Unknown agent type: {agent_type}[/red]")
                return None
            
            self.agents[name] = agent
            
            # Register with orchestrator if capabilities are specified
            capabilities = config.get("capabilities", []) if config else []
            if agent_type != "base":
                # Add type as a capability
                capabilities.append(agent_type)
            self.orchestrator.register_agent(agent, capabilities)
            
            self.console.print(f"[green]Created agent '{name}' of type '{agent_type}'[/green]")
            return agent
            
        except Exception as e:
            self.console.print(f"[red]Failed to create agent: {str(e)}[/red]")
            return None
    
    async def create_agent_from_config(self, config_path: str) -> Optional[SubAgent]:
        """Create an agent from a configuration file.
        
        Args:
            config_path: Path to YAML or JSON configuration file
            
        Returns:
            SubAgent: The created agent, or None if creation failed
        """
        try:
            path = Path(config_path)
            
            if not path.exists():
                self.console.print(f"[red]Config file not found: {config_path}[/red]")
                return None
            
            # Load configuration
            with open(path, 'r') as f:
                if path.suffix in ['.yaml', '.yml']:
                    config = yaml.safe_load(f)
                elif path.suffix == '.json':
                    config = json.load(f)
                else:
                    self.console.print(f"[red]Unsupported config format: {path.suffix}[/red]")
                    return None
            
            # Extract agent configuration
            agent_type = config.get("type", "base")
            name = config.get("name", f"agent-{len(self.agents)}")
            model = config.get("model", "qwen2.5:7b")
            
            # Create agent
            agent = self.create_agent(agent_type, name, model, config)
            
            if agent:
                # Connect to servers if specified
                if "servers" in config:
                    server_config = config["servers"]
                    await agent.connect_to_servers(
                        server_paths=server_config.get("paths"),
                        server_urls=server_config.get("urls"),
                        config_path=server_config.get("config_file")
                    )
                
                # Enable specific tools if specified
                if "enabled_tools" in config:
                    agent.enable_tools(config["enabled_tools"])
            
            return agent
            
        except Exception as e:
            self.console.print(f"[red]Failed to load agent config: {str(e)}[/red]")
            self.console.print_exception()
            return None
    
    def get_agent(self, name: str) -> Optional[SubAgent]:
        """Get an agent by name.
        
        Args:
            name: Agent name
            
        Returns:
            SubAgent or None if not found
        """
        return self.agents.get(name)
    
    def list_agents(self) -> List[str]:
        """Get list of agent names.
        
        Returns:
            List of agent names
        """
        return list(self.agents.keys())
    
    def remove_agent(self, name: str) -> bool:
        """Remove an agent.
        
        Args:
            name: Agent name
            
        Returns:
            bool: True if removed, False if not found
        """
        if name in self.agents:
            del self.agents[name]
            self.console.print(f"[green]Removed agent '{name}'[/green]")
            return True
        else:
            self.console.print(f"[yellow]Agent '{name}' not found[/yellow]")
            return False
    
    def display_agents(self) -> None:
        """Display all agents in a formatted table."""
        if not self.agents:
            self.console.print("[yellow]No agents created yet[/yellow]")
            return
        
        table = Table(title="Specialized Agents")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Model", style="green")
        table.add_column("Servers", style="blue")
        table.add_column("Tools", style="yellow")
        table.add_column("Tasks", style="white")
        
        for name, agent in self.agents.items():
            info = agent.get_info()
            agent_type = "Web3 Audit" if isinstance(agent, Web3AuditAgent) else "Base"
            servers = ", ".join(info["connected_servers"]) if info["connected_servers"] else "None"
            tool_count = len([t for t, enabled in agent.tool_manager.get_enabled_tools().items() if enabled])
            
            table.add_row(
                name,
                agent_type,
                info["model"],
                servers,
                str(tool_count),
                str(info["task_count"])
            )
        
        self.console.print(table)
    
    async def execute_agent_task(self, agent_name: str, task: str) -> Optional[str]:
        """Execute a task using a specific agent.
        
        Args:
            agent_name: Name of the agent
            task: Task description
            
        Returns:
            str: Agent's response, or None if agent not found
        """
        agent = self.get_agent(agent_name)
        
        if not agent:
            self.console.print(f"[red]Agent '{agent_name}' not found[/red]")
            return None
        
        try:
            self.console.print(Panel(
                f"[cyan]Agent:[/cyan] {agent_name}\n[cyan]Task:[/cyan] {task}",
                title="Executing Agent Task",
                border_style="cyan"
            ))
            
            result = await agent.execute_task(task)
            
            self.console.print(Panel(
                result,
                title=f"Agent Response: {agent_name}",
                border_style="green"
            ))
            
            return result
            
        except Exception as e:
            self.console.print(f"[red]Error executing task: {str(e)}[/red]")
            self.console.print_exception()
            return None
    
    async def cleanup_all(self) -> None:
        """Clean up all agents."""
        for agent in self.agents.values():
            await agent.cleanup()
        self.agents.clear()
    
    async def execute_workflow(
        self,
        workflow_name: str,
        tasks: List[str],
        parallel: bool = False
    ) -> Dict[str, Any]:
        """Execute a multi-agent workflow.
        
        Args:
            workflow_name: Name for this workflow
            tasks: List of task descriptions
            parallel: Whether to execute tasks in parallel
            
        Returns:
            Dict with workflow results
        """
        return await self.orchestrator.execute_workflow(workflow_name, tasks, parallel)
    
    async def start_autonomous_agents(self, agent_names: Optional[List[str]] = None) -> None:
        """Start agents in autonomous mode.
        
        Args:
            agent_names: List of agent names to start (all if None)
        """
        agents_to_start = agent_names or list(self.agents.keys())
        
        for name in agents_to_start:
            if name in self.agents:
                self.agents[name].start_autonomous_mode()
        
        self.console.print(Panel(
            f"Started {len(agents_to_start)} agents in autonomous mode",
            title="Autonomous Mode",
            border_style="green"
        ))
    
    async def stop_autonomous_agents(self, agent_names: Optional[List[str]] = None) -> None:
        """Stop autonomous mode for agents.
        
        Args:
            agent_names: List of agent names to stop (all if None)
        """
        agents_to_stop = agent_names or list(self.agents.keys())
        
        for name in agents_to_stop:
            if name in self.agents:
                self.agents[name].stop_autonomous_mode()
        
        self.console.print(Panel(
            f"Stopped {len(agents_to_stop)} agents",
            title="Autonomous Mode Stopped",
            border_style="yellow"
        ))
    
    def get_orchestrator_status(self) -> Dict[str, Any]:
        """Get orchestrator status and statistics.
        
        Returns:
            Dict with orchestrator information
        """
        workload = self.orchestrator.get_agent_workload()
        
        return {
            "registered_agents": len(self.orchestrator.agents),
            "total_tasks": len(self.orchestrator.tasks),
            "active_workflows": len(self.orchestrator.active_workflows),
            "agent_workload": workload
        }
