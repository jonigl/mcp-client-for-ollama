"""Agent orchestrator for coordinating multi-agent systems."""

import asyncio
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, TaskID

from .communication import MessageBroker, AgentMessage, MessageType
from .base import SubAgent


class TaskStatus(Enum):
    """Status of a task."""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    DELEGATED = "delegated"


@dataclass
class Task:
    """A task to be executed by agents."""
    id: str
    description: str
    assigned_to: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 1
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Any] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    parent_task_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "description": self.description,
            "assigned_to": self.assigned_to,
            "status": self.status.value,
            "priority": self.priority,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parent_task_id": self.parent_task_id,
            "subtasks": self.subtasks
        }


class AgentOrchestrator:
    """Orchestrates multiple agents to accomplish complex tasks."""
    
    def __init__(
        self,
        console: Optional[Console] = None,
        message_broker: Optional[MessageBroker] = None
    ):
        """Initialize the orchestrator.
        
        Args:
            console: Rich console for output
            message_broker: Message broker for agent communication
        """
        self.console = console or Console()
        self.message_broker = message_broker or MessageBroker()
        self.agents: Dict[str, SubAgent] = {}
        self.tasks: Dict[str, Task] = {}
        self.agent_capabilities: Dict[str, List[str]] = {}
        self.active_workflows: Dict[str, List[str]] = {}
        
    def register_agent(
        self,
        agent: SubAgent,
        capabilities: Optional[List[str]] = None
    ) -> None:
        """Register an agent with the orchestrator.
        
        Args:
            agent: Agent to register
            capabilities: List of capabilities this agent has
        """
        self.agents[agent.name] = agent
        self.agent_capabilities[agent.name] = capabilities or []
        self.message_broker.register_agent(agent.name)
        
        self.console.print(
            f"[green]Registered agent '{agent.name}' with capabilities: "
            f"{', '.join(capabilities or ['general'])}[/green]"
        )
    
    def unregister_agent(self, agent_name: str) -> None:
        """Unregister an agent.
        
        Args:
            agent_name: Name of agent to unregister
        """
        if agent_name in self.agents:
            del self.agents[agent_name]
            del self.agent_capabilities[agent_name]
            self.message_broker.unregister_agent(agent_name)
    
    def select_agent_for_task(self, task_description: str) -> Optional[str]:
        """Select the most appropriate agent for a task.
        
        Args:
            task_description: Description of the task
            
        Returns:
            str: Name of selected agent, or None if no suitable agent
        """
        task_lower = task_description.lower()
        
        # Score each agent based on capabilities
        scores: Dict[str, int] = {}
        for agent_name, capabilities in self.agent_capabilities.items():
            score = 0
            for capability in capabilities:
                if capability.lower() in task_lower:
                    score += 10
            
            # Check agent type
            agent = self.agents[agent_name]
            agent_type = type(agent).__name__
            if "research" in task_lower and "research" in agent_type.lower():
                score += 5
            if "code" in task_lower and "coder" in agent_type.lower():
                score += 5
            if "test" in task_lower and "tester" in agent_type.lower():
                score += 5
            if "write" in task_lower and "writer" in agent_type.lower():
                score += 5
            if "review" in task_lower and "review" in agent_type.lower():
                score += 5
            
            scores[agent_name] = score
        
        # Return agent with highest score, or first available agent
        if scores:
            best_agent = max(scores.items(), key=lambda x: x[1])
            if best_agent[1] > 0:
                return best_agent[0]
        
        # Return first available agent as fallback
        return list(self.agents.keys())[0] if self.agents else None
    
    async def decompose_task(self, task_description: str) -> List[str]:
        """Decompose a complex task into subtasks.
        
        Args:
            task_description: Description of the complex task
            
        Returns:
            List of subtask descriptions
        """
        # For now, return as single task
        # In a real implementation, you might use an LLM to decompose
        return [task_description]
    
    async def create_task(
        self,
        description: str,
        priority: int = 1,
        dependencies: Optional[List[str]] = None,
        parent_task_id: Optional[str] = None
    ) -> str:
        """Create a new task.
        
        Args:
            description: Task description
            priority: Task priority (1-5)
            dependencies: List of task IDs this task depends on
            parent_task_id: ID of parent task if this is a subtask
            
        Returns:
            str: Task ID
        """
        import uuid
        task_id = str(uuid.uuid4())
        
        task = Task(
            id=task_id,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            parent_task_id=parent_task_id
        )
        
        self.tasks[task_id] = task
        
        return task_id
    
    async def assign_task(self, task_id: str, agent_name: Optional[str] = None) -> bool:
        """Assign a task to an agent.
        
        Args:
            task_id: ID of the task
            agent_name: Name of agent to assign to (auto-select if None)
            
        Returns:
            bool: True if assigned successfully
        """
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        
        # Auto-select agent if not specified
        if not agent_name:
            agent_name = self.select_agent_for_task(task.description)
        
        if not agent_name or agent_name not in self.agents:
            return False
        
        task.assigned_to = agent_name
        task.status = TaskStatus.ASSIGNED
        
        # Send message to agent
        message = AgentMessage(
            sender="orchestrator",
            recipient=agent_name,
            message_type=MessageType.TASK_REQUEST,
            content={
                "task_id": task_id,
                "description": task.description,
                "priority": task.priority
            }
        )
        
        await self.message_broker.send_message(message)
        
        return True
    
    async def execute_task(self, task_id: str) -> Tuple[bool, Optional[Any]]:
        """Execute a task.
        
        Args:
            task_id: ID of the task to execute
            
        Returns:
            Tuple of (success, result)
        """
        if task_id not in self.tasks:
            return False, None
        
        task = self.tasks[task_id]
        
        # Check dependencies
        for dep_id in task.dependencies:
            if dep_id in self.tasks:
                dep_task = self.tasks[dep_id]
                if dep_task.status != TaskStatus.COMPLETED:
                    task.status = TaskStatus.PENDING
                    return False, None
        
        # Assign if not already assigned
        if not task.assigned_to:
            await self.assign_task(task_id)
        
        if not task.assigned_to or task.assigned_to not in self.agents:
            task.status = TaskStatus.FAILED
            task.error = "No suitable agent available"
            return False, None
        
        agent = self.agents[task.assigned_to]
        
        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        
        try:
            self.console.print(Panel(
                f"[cyan]Agent:[/cyan] {task.assigned_to}\n"
                f"[cyan]Task:[/cyan] {task.description}",
                title="Executing Task",
                border_style="cyan"
            ))
            
            result = await agent.execute_task(task.description)
            
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now()
            task.result = result
            
            self.console.print(Panel(
                f"[green]✓[/green] Task completed by {task.assigned_to}",
                border_style="green"
            ))
            
            return True, result
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            task.error = str(e)
            
            self.console.print(Panel(
                f"[red]✗[/red] Task failed: {str(e)}",
                border_style="red"
            ))
            
            return False, None
    
    async def execute_workflow(
        self,
        workflow_id: str,
        task_descriptions: List[str],
        parallel: bool = False
    ) -> Dict[str, Any]:
        """Execute a workflow of multiple tasks.
        
        Args:
            workflow_id: ID for this workflow
            task_descriptions: List of task descriptions
            parallel: Whether to execute tasks in parallel
            
        Returns:
            Dict with workflow results
        """
        self.console.print(Panel(
            f"Starting workflow: {workflow_id}\n"
            f"Tasks: {len(task_descriptions)}\n"
            f"Mode: {'Parallel' if parallel else 'Sequential'}",
            title="Workflow Execution",
            border_style="blue"
        ))
        
        # Create tasks
        task_ids = []
        for desc in task_descriptions:
            task_id = await self.create_task(desc)
            task_ids.append(task_id)
        
        self.active_workflows[workflow_id] = task_ids
        
        # Execute tasks
        results = {}
        
        if parallel:
            # Execute all tasks in parallel
            tasks = [self.execute_task(task_id) for task_id in task_ids]
            task_results = await asyncio.gather(*tasks)
            
            for task_id, (success, result) in zip(task_ids, task_results):
                results[task_id] = {
                    "success": success,
                    "result": result,
                    "task": self.tasks[task_id].to_dict()
                }
        else:
            # Execute tasks sequentially
            for task_id in task_ids:
                success, result = await self.execute_task(task_id)
                results[task_id] = {
                    "success": success,
                    "result": result,
                    "task": self.tasks[task_id].to_dict()
                }
        
        # Summary
        successful = sum(1 for r in results.values() if r["success"])
        failed = len(results) - successful
        
        self.console.print(Panel(
            f"[green]Completed:[/green] {successful}\n"
            f"[red]Failed:[/red] {failed}",
            title=f"Workflow {workflow_id} Complete",
            border_style="blue"
        ))
        
        return {
            "workflow_id": workflow_id,
            "total_tasks": len(task_ids),
            "successful": successful,
            "failed": failed,
            "results": results
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a task.
        
        Args:
            task_id: ID of the task
            
        Returns:
            Dict with task status or None
        """
        if task_id not in self.tasks:
            return None
        
        return self.tasks[task_id].to_dict()
    
    def get_agent_workload(self) -> Dict[str, Dict[str, int]]:
        """Get workload statistics for all agents.
        
        Returns:
            Dict mapping agent names to workload stats
        """
        workload = {}
        
        for agent_name in self.agents:
            workload[agent_name] = {
                "assigned": 0,
                "in_progress": 0,
                "completed": 0,
                "failed": 0
            }
        
        for task in self.tasks.values():
            if task.assigned_to and task.assigned_to in workload:
                if task.status == TaskStatus.ASSIGNED:
                    workload[task.assigned_to]["assigned"] += 1
                elif task.status == TaskStatus.IN_PROGRESS:
                    workload[task.assigned_to]["in_progress"] += 1
                elif task.status == TaskStatus.COMPLETED:
                    workload[task.assigned_to]["completed"] += 1
                elif task.status == TaskStatus.FAILED:
                    workload[task.assigned_to]["failed"] += 1
        
        return workload
