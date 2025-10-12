# Autonomous Multi-Agent System

## Overview

The MCP Client for Ollama now features a **true autonomous multi-agent system** with sophisticated capabilities for collaboration, orchestration, and persistent state management. This system enables multiple specialized AI agents to work together simultaneously on complex tasks, similar to advanced systems like Crush or Claude Code.

## Key Features

### 🤖 Multiple Specialized Agent Types

Create agents optimized for specific tasks:

- **ResearcherAgent**: Information gathering, web research, fact-checking, document analysis
- **CoderAgent**: Code generation, bug fixes, refactoring, feature implementation
- **WriterAgent**: Documentation, README files, reports, API docs, tutorials
- **TesterAgent**: Unit tests, integration tests, test execution, coverage analysis
- **ReviewerAgent**: Code review, security analysis, performance review, architecture review
- **Web3AuditAgent**: Smart contract security auditing (existing, enhanced)

### 🔗 Agent-to-Agent Communication

Agents can communicate and collaborate through a sophisticated messaging system:

- **Message Broker**: Central hub for inter-agent communication
- **Message Types**: Task requests, responses, information sharing, status updates, errors
- **Conversation Threading**: Track multi-turn conversations between agents
- **Message History**: Full audit trail of all agent interactions

### 🧠 Persistent Memory

Each agent maintains its own persistent memory:

- **Short-term Memory**: Recent interactions and context
- **Long-term Memory**: Important information consolidated over time
- **Working Memory**: Temporary state for active tasks
- **Memory Search**: Query memories by content, tags, and importance
- **Context Summarization**: Automatic context generation for tasks
- **File Persistence**: Save and load agent memories between sessions

### 🎭 Autonomous Operation

Agents can operate autonomously:

- **Background Listening**: Continuously listen for messages and tasks
- **Auto-Response**: Automatically handle incoming requests
- **Task Delegation**: Delegate subtasks to other specialized agents
- **Collaborative Work**: Multiple agents working in parallel

### 🎼 Orchestration System

Coordinate multiple agents for complex workflows:

- **Task Decomposition**: Break down complex tasks into subtasks
- **Intelligent Agent Selection**: Auto-select the best agent for each task
- **Parallel Execution**: Run multiple agents simultaneously
- **Sequential Workflows**: Execute tasks in a specific order
- **Dependency Management**: Handle task dependencies automatically
- **Workload Monitoring**: Track agent status and task progress

## Quick Start

### Creating Specialized Agents

```python
from mcp_client_for_ollama.agents import AgentManager

# Create manager (already initialized in the client)
manager = agent_manager

# Create a researcher agent
researcher = manager.create_agent(
    agent_type="researcher",
    name="my-researcher",
    model="qwen2.5:7b"
)

# Create a coder agent
coder = manager.create_agent(
    agent_type="coder",
    name="my-coder",
    model="qwen2.5-coder:7b"
)

# Create a writer agent
writer = manager.create_agent(
    agent_type="writer",
    name="my-writer",
    model="qwen2.5:7b"
)
```

### Executing Tasks

```python
# Single agent task
result = await manager.execute_agent_task(
    "my-researcher",
    "Research the latest developments in AI agents"
)

# Multi-agent workflow (sequential)
workflow = await manager.execute_workflow(
    workflow_name="research-and-document",
    tasks=[
        "Research autonomous agent systems",
        "Write a comprehensive report on findings",
        "Generate example code implementations"
    ],
    parallel=False  # Execute sequentially
)

# Multi-agent workflow (parallel)
workflow = await manager.execute_workflow(
    workflow_name="parallel-analysis",
    tasks=[
        "Analyze codebase for bugs",
        "Check test coverage",
        "Review security vulnerabilities"
    ],
    parallel=True  # Execute in parallel
)
```

### Agent Collaboration

```python
# Start agents in autonomous mode
await manager.start_autonomous_agents(["researcher", "coder", "writer"])

# Agents can now communicate and delegate tasks
# For example, researcher can delegate code examples to coder
# Or coder can ask writer to document the code

# Stop autonomous mode when done
await manager.stop_autonomous_agents()
```

### Using Agent Memory

```python
# Store information in agent memory
await researcher.remember(
    "Important finding about multi-agent systems",
    importance=5,
    tags=["research", "multi-agent"]
)

# Recall information
memories = await researcher.recall(
    query="multi-agent",
    limit=5
)

# Get context summary
context = researcher.memory.get_context_summary(max_items=10)
```

## Agent Types Reference

### ResearcherAgent

**Purpose**: Information gathering and analysis

**Specialized Methods**:
- `research_topic(topic, depth, max_sources)`: Research a topic comprehensively
- `verify_fact(claim)`: Verify factual claims with sources
- `summarize_document(path)`: Summarize documents
- `add_research_note()`: Track research findings

**Best For**:
- Web research and information gathering
- Fact-checking and verification
- Document analysis and summarization
- Competitive analysis

### CoderAgent

**Purpose**: Code generation and modification

**Specialized Methods**:
- `implement_feature(description, language, context)`: Implement new features
- `fix_bug(description, code, language)`: Fix bugs in code
- `refactor_code(code, language, goals)`: Refactor for better quality
- `create_file(path, content, description)`: Create new code files
- `execute_code(code, language, args)`: Execute code and get output

**Best For**:
- Writing new code
- Fixing bugs
- Refactoring existing code
- Code optimization

### WriterAgent

**Purpose**: Documentation and report writing

**Specialized Methods**:
- `write_documentation(topic, doc_type, details)`: Write documentation
- `write_readme(project_name, description, ...)`: Create README files
- `write_api_docs(api_name, endpoints)`: Document APIs
- `generate_report(title, data, report_type)`: Generate reports

**Best For**:
- Technical documentation
- User guides and tutorials
- API documentation
- Reports and summaries

### TesterAgent

**Purpose**: Test creation and execution

**Specialized Methods**:
- `write_unit_tests(code, language, framework)`: Generate unit tests
- `run_tests(test_path, framework, options)`: Execute test suites
- `identify_test_cases(requirements)`: Create test plan from requirements
- `analyze_coverage(project_path, language)`: Analyze test coverage
- `write_integration_tests(components, language)`: Create integration tests

**Best For**:
- Writing test cases
- Running test suites
- Analyzing coverage
- Test planning

### ReviewerAgent

**Purpose**: Code review and quality assurance

**Specialized Methods**:
- `review_code(code, language, focus_areas, context)`: Comprehensive code review
- `security_review(code, language)`: Security-focused review
- `performance_review(code, language)`: Performance analysis
- `architecture_review(project_path, description)`: Architecture review
- `review_pull_request(diff, description, language)`: Review PRs

**Best For**:
- Code quality review
- Security analysis
- Performance optimization
- Architecture validation

### Web3AuditAgent

**Purpose**: Smart contract security auditing

**Specialized Methods**:
- `analyze_contract(path, analysis_type)`: Analyze smart contracts
- `run_foundry_tests(project_path)`: Run Foundry tests
- `run_slither_analysis(path)`: Run Slither static analysis
- `generate_audit_report()`: Create audit reports
- `add_finding()`: Track vulnerabilities

**Best For**:
- Smart contract security audits
- Vulnerability detection
- Web3 testing with Foundry/Hardhat

## Advanced Usage

### Custom Agent Creation

```python
# Create a custom agent with specific capabilities
config = {
    "description": "Database optimization specialist",
    "system_prompt": "You are an expert in database optimization...",
    "capabilities": ["database", "sql", "optimization"]
}

db_agent = manager.create_agent(
    agent_type="base",
    name="db-optimizer",
    model="qwen2.5:7b",
    config=config
)
```

### Agent-to-Agent Messaging

```python
# Send a message from one agent to another
await researcher.send_message(
    recipient="coder",
    message_type=MessageType.INFORMATION_SHARE,
    content={
        "findings": "Discovered new design pattern...",
        "example_code": "..."
    }
)

# Delegate a task
await coder.delegate_task(
    recipient="tester",
    task="Write tests for the new feature implementation"
)

# Share information
await tester.share_information(
    recipient="reviewer",
    information={
        "test_results": "All tests passed",
        "coverage": "95%"
    }
)
```

### Workflow Orchestration

```python
# Complex multi-stage workflow
workflow_result = await manager.execute_workflow(
    workflow_name="full-feature-development",
    tasks=[
        # Stage 1: Research
        "Research best practices for the feature",
        
        # Stage 2: Implementation
        "Implement the feature based on research",
        
        # Stage 3: Testing
        "Write comprehensive tests for the feature",
        
        # Stage 4: Review
        "Review the implementation and tests",
        
        # Stage 5: Documentation
        "Document the feature and update README"
    ],
    parallel=False  # Sequential execution
)

# Check results
print(f"Completed: {workflow_result['successful']}/{workflow_result['total_tasks']}")
```

### Monitoring and Status

```python
# Get orchestrator status
status = manager.get_orchestrator_status()
print(f"Active agents: {status['registered_agents']}")
print(f"Total tasks: {status['total_tasks']}")
print(f"Active workflows: {status['active_workflows']}")

# Get agent workload
workload = status['agent_workload']
for agent_name, stats in workload.items():
    print(f"{agent_name}: {stats['in_progress']} in progress, {stats['completed']} completed")

# Get individual agent info
agent_info = researcher.get_info()
print(f"Agent: {agent_info['name']}")
print(f"Autonomous: {agent_info['autonomous']}")
print(f"Pending messages: {agent_info['pending_messages']}")
print(f"Tasks completed: {agent_info['task_count']}")
```

## Use Cases

### Full-Stack Development Workflow

```python
# Create a team of agents
manager.create_agent("researcher", "researcher", "qwen2.5:7b")
manager.create_agent("coder", "coder", "qwen2.5-coder:7b")
manager.create_agent("tester", "tester", "qwen2.5:7b")
manager.create_agent("reviewer", "reviewer", "qwen2.5:7b")
manager.create_agent("writer", "writer", "qwen2.5:7b")

# Execute development workflow
await manager.execute_workflow(
    "feature-development",
    [
        "Research: Best practices for user authentication",
        "Code: Implement authentication system",
        "Test: Write unit and integration tests",
        "Review: Security and code quality review",
        "Document: Create API documentation"
    ],
    parallel=False
)
```

### Automated Code Review Pipeline

```python
# Start autonomous agents
await manager.start_autonomous_agents(["reviewer", "tester", "writer"])

# Reviewer analyzes code, delegates testing, requests documentation
result = await manager.execute_agent_task(
    "reviewer",
    "Review the pull request and coordinate with other agents for testing and documentation"
)
```

### Research and Report Generation

```python
# Parallel research with multiple researchers
manager.create_agent("researcher", "researcher1", "qwen2.5:7b")
manager.create_agent("researcher", "researcher2", "qwen2.5:7b")
manager.create_agent("writer", "report-writer", "qwen2.5:7b")

# Research different aspects
await manager.execute_workflow(
    "comprehensive-research",
    [
        "Research technical aspects",
        "Research market analysis",
        "Research competitive landscape",
        "Compile all findings into comprehensive report"
    ],
    parallel=True  # First 3 in parallel, then report
)
```

## Configuration

### Agent Configuration Files

Create YAML configuration files for reusable agent setups:

```yaml
# config/agents/full-stack-coder.yaml
type: coder
name: full-stack-dev
model: qwen2.5-coder:7b
capabilities:
  - frontend
  - backend
  - database
system_prompt: |
  You are an expert full-stack developer...
servers:
  paths:
    - /path/to/filesystem-server.py
    - /path/to/bash-server.py
enabled_tools:
  - filesystem.read_file
  - filesystem.write_file
  - bash.execute_command
```

Load from configuration:

```python
agent = await manager.create_agent_from_config(
    "config/agents/full-stack-coder.yaml"
)
```

## Best Practices

1. **Specialize Agents**: Use specific agent types for their intended purpose
2. **Use Memory**: Store important context in agent memory for better continuity
3. **Autonomous Mode**: Enable autonomous mode for collaborative workflows
4. **Parallel Execution**: Use parallel workflows when tasks are independent
5. **Monitor Status**: Regularly check orchestrator status for large workflows
6. **Clear Communication**: Use descriptive task descriptions for better results
7. **Capability Tagging**: Tag agents with their capabilities for better selection
8. **Save State**: Persist agent memories for long-running projects

## Troubleshooting

### Agents Not Communicating

- Ensure agents have `message_broker` configured
- Check that agents are registered with the orchestrator
- Verify autonomous mode is enabled if expecting auto-responses

### Tasks Failing

- Check agent has necessary tools enabled
- Verify model is available in Ollama
- Review task description for clarity
- Check agent logs for specific errors

### Memory Not Persisting

- Ensure memory is enabled for the agent
- Check write permissions for `~/.ollmcp/agent_memory/`
- Verify `cleanup()` is called to save memory

### Performance Issues

- Limit parallel agents based on system resources
- Use smaller models for simpler tasks
- Monitor task queue sizes
- Consider task priorities

## Migration from Simple Agents

If you're upgrading from the simple agent system:

1. **Existing agents still work**: All existing Web3AuditAgent functionality is preserved
2. **New features are opt-in**: Memory and communication are optional
3. **Gradual migration**: Start using new features incrementally
4. **Backward compatible**: Old configuration files still work

## Contributing

To add new agent types:

1. Extend `SubAgent` class in a new file
2. Define specialized methods for the agent type
3. Add default system prompt
4. Register agent type in `AgentManager.create_agent()`
5. Add tests in `tests/test_agents.py`
6. Update this documentation

## Related Documentation

- [Agent Basics (AGENTS.md)](AGENTS.md)
- [Implementation Summary](IMPLEMENTATION_SUMMARY.md)
- [Web3 Audit Quick Start](WEB3_AUDIT_QUICKSTART.md)
