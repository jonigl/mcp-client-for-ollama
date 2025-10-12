"""
Example demonstrating the autonomous multi-agent system.

This script shows how to:
1. Create multiple specialized agents
2. Execute a coordinated multi-agent workflow
3. Use agent collaboration and communication
4. Track agent status and progress
"""

import asyncio
from rich.console import Console
from contextlib import AsyncExitStack
import ollama

from mcp_client_for_ollama.agents import AgentManager


async def main():
    """Run multi-agent system example."""
    console = Console()
    console.print("\n[bold blue]🤖 Multi-Agent System Example[/bold blue]\n")
    
    # Initialize components
    ollama_client = ollama.AsyncClient()
    exit_stack = AsyncExitStack()
    
    # Create agent manager
    manager = AgentManager(console, ollama_client, exit_stack)
    
    # Example 1: Create specialized agents
    console.print("[bold cyan]Step 1: Creating Specialized Agents[/bold cyan]")
    
    researcher = manager.create_agent(
        agent_type="researcher",
        name="researcher",
        model="qwen2.5:7b"
    )
    
    coder = manager.create_agent(
        agent_type="coder",
        name="coder",
        model="qwen2.5-coder:7b"
    )
    
    writer = manager.create_agent(
        agent_type="writer",
        name="writer",
        model="qwen2.5:7b"
    )
    
    console.print(f"\n✓ Created {len(manager.agents)} agents")
    
    # Example 2: Display agent information
    console.print("\n[bold cyan]Step 2: Agent Information[/bold cyan]")
    manager.display_agents()
    
    # Example 3: Execute single agent task
    console.print("\n[bold cyan]Step 3: Single Agent Task[/bold cyan]")
    
    # Note: This would actually require Ollama to be running and models downloaded
    # For this example, we'll just show the structure
    console.print("Would execute: Research task with researcher agent")
    # result = await manager.execute_agent_task(
    #     "researcher",
    #     "Research the concept of autonomous agents in AI"
    # )
    
    # Example 4: Multi-agent workflow (sequential)
    console.print("\n[bold cyan]Step 4: Multi-Agent Workflow (Sequential)[/bold cyan]")
    console.print("Would execute workflow:")
    console.print("  1. Researcher: Research autonomous agents")
    console.print("  2. Coder: Implement example code")
    console.print("  3. Writer: Document the implementation")
    
    # workflow_result = await manager.execute_workflow(
    #     workflow_name="research-code-document",
    #     tasks=[
    #         "Research autonomous agent architectures",
    #         "Implement a simple autonomous agent example",
    #         "Create comprehensive documentation"
    #     ],
    #     parallel=False
    # )
    
    # Example 5: Agent collaboration
    console.print("\n[bold cyan]Step 5: Agent Collaboration[/bold cyan]")
    console.print("Agents can:")
    console.print("  • Send messages to each other")
    console.print("  • Delegate tasks to specialized agents")
    console.print("  • Share information and context")
    console.print("  • Work autonomously in the background")
    
    # Example: Start autonomous mode
    # await manager.start_autonomous_agents()
    console.print("\n✓ Agents would now be in autonomous mode")
    
    # Example 6: Agent memory
    console.print("\n[bold cyan]Step 6: Agent Memory[/bold cyan]")
    
    if researcher and researcher.memory:
        # Add some memories
        await researcher.remember(
            "Autonomous agents can communicate and delegate tasks",
            importance=4,
            tags=["research", "agents"]
        )
        
        await researcher.remember(
            "Multi-agent systems enable parallel task execution",
            importance=5,
            tags=["research", "architecture"]
        )
        
        console.print("✓ Added memories to researcher agent")
        
        # Recall memories
        memories = await researcher.recall(query="agents", limit=3)
        console.print(f"✓ Recalled memories:\n{memories}")
    
    # Example 7: Orchestrator status
    console.print("\n[bold cyan]Step 7: Orchestrator Status[/bold cyan]")
    
    status = manager.get_orchestrator_status()
    console.print(f"Registered agents: {status['registered_agents']}")
    console.print(f"Total tasks: {status['total_tasks']}")
    console.print(f"Active workflows: {status['active_workflows']}")
    
    # Cleanup
    console.print("\n[bold cyan]Cleanup[/bold cyan]")
    await manager.cleanup_all()
    await exit_stack.aclose()
    console.print("✓ All agents cleaned up\n")
    
    # Summary
    console.print("[bold green]✓ Multi-Agent System Example Complete![/bold green]")
    console.print("\nKey Features Demonstrated:")
    console.print("  • Multiple specialized agent types")
    console.print("  • Agent creation and management")
    console.print("  • Workflow orchestration")
    console.print("  • Agent collaboration")
    console.print("  • Persistent memory")
    console.print("  • Status monitoring")
    console.print("\nFor full functionality, ensure Ollama is running with required models.")


if __name__ == "__main__":
    asyncio.run(main())
