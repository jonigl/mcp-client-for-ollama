# Multi-Agent System Examples

This directory contains example scripts demonstrating the autonomous multi-agent system capabilities.

## Examples

### multi_agent_example.py

Comprehensive example showing:
- Creating multiple specialized agents (Researcher, Coder, Writer)
- Agent information and status display
- Single agent task execution
- Multi-agent workflow orchestration
- Agent collaboration and communication
- Persistent agent memory
- Orchestrator status monitoring

**Run the example:**
```bash
python examples/multi_agent_example.py
```

**Note**: For full functionality, ensure:
1. Ollama is running (`ollama serve`)
2. Required models are downloaded:
   - `ollama pull qwen2.5:7b`
   - `ollama pull qwen2.5-coder:7b`

## Creating Your Own Multi-Agent Workflows

### Example 1: Research and Documentation Pipeline

```python
import asyncio
from mcp_client_for_ollama.agents import AgentManager

async def research_pipeline():
    # Create agents
    manager = AgentManager(console, ollama_client, exit_stack)
    manager.create_agent("researcher", "researcher", "qwen2.5:7b")
    manager.create_agent("writer", "writer", "qwen2.5:7b")
    
    # Execute workflow
    result = await manager.execute_workflow(
        "research-pipeline",
        [
            "Research the latest AI trends",
            "Write a comprehensive report on the findings"
        ],
        parallel=False
    )
    
    print(f"Workflow completed: {result['successful']}/{result['total_tasks']} tasks")

asyncio.run(research_pipeline())
```

### Example 2: Code Development Team

```python
async def dev_team():
    # Create full development team
    manager = AgentManager(console, ollama_client, exit_stack)
    manager.create_agent("coder", "dev", "qwen2.5-coder:7b")
    manager.create_agent("tester", "qa", "qwen2.5:7b")
    manager.create_agent("reviewer", "reviewer", "qwen2.5:7b")
    manager.create_agent("writer", "docs", "qwen2.5:7b")
    
    # Parallel code review and testing
    await manager.execute_workflow(
        "code-review",
        [
            "Review code for security issues",
            "Run all test suites",
            "Check code coverage"
        ],
        parallel=True  # Run in parallel
    )

asyncio.run(dev_team())
```

### Example 3: Autonomous Agent Collaboration

```python
async def autonomous_collaboration():
    manager = AgentManager(console, ollama_client, exit_stack)
    
    # Create agents
    researcher = manager.create_agent("researcher", "researcher", "qwen2.5:7b")
    coder = manager.create_agent("coder", "coder", "qwen2.5-coder:7b")
    
    # Start autonomous mode
    await manager.start_autonomous_agents()
    
    # Researcher can now delegate coding tasks to coder
    await researcher.delegate_task(
        "coder",
        "Implement the algorithm we just researched"
    )
    
    # Agents communicate autonomously
    # ...work happens in the background...
    
    # Stop autonomous mode when done
    await manager.stop_autonomous_agents()

asyncio.run(autonomous_collaboration())
```

## More Information

- [Multi-Agent System Documentation](../docs/MULTI_AGENT_SYSTEM.md)
- [Agent Basics](../docs/AGENTS.md)
- [Configuration Examples](../config/agents/)
