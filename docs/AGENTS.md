# Specialized Agents

## Overview

MCP Client for Ollama now supports **specialized subagents** - independent AI agents that can be configured for specific tasks with their own system prompts, tool selections, and MCP server connections. This is particularly powerful for complex workflows like Web3 security auditing.

## Key Features

- 🎯 **Task-Specific Agents**: Create agents optimized for specific workflows (auditing, testing, analysis)
- 🧠 **Custom System Prompts**: Each agent has its own personality and expertise
- 🔧 **Independent Tool Access**: Agents can have different tool configurations
- 🌐 **Separate Server Connections**: Connect agents to different MCP servers
- 📝 **Configuration Files**: Define agents using YAML or JSON files
- 🔄 **Agent Orchestration**: Coordinate multiple agents for complex tasks

## Built-in Agent Types

### Web3 Audit Agent

Pre-configured for smart contract security auditing with expertise in:
- Vulnerability detection (reentrancy, overflow, access control, etc.)
- Running security tools (Slither, Mythril, Foundry tests)
- Code review and best practices
- Gas optimization analysis
- Severity classification of findings

### Base Agent

Generic agent type for custom configurations. Requires:
- Description of agent's purpose
- Custom system prompt
- Tool configuration

## Quick Start

### Using the Interactive Menu

1. In the main client, type `agent` or `ag` to open the agent menu
2. Choose from available actions:
   - Create a new agent
   - List all agents
   - Execute task with agent
   - Load agent from config file
   - Remove an agent
   - Show agent details

### Creating a Web3 Audit Agent

```python
# In the agent menu, choose "Create a new agent"
Agent type: web3_audit
Agent name: my-auditor
Model: qwen2.5:7b
Connect to MCP servers: yes
```

### Loading from Configuration

```bash
# In the agent menu, choose "Load agent from config file"
Config file path: config/agents/web3_auditor.yaml
```

## Configuration Files

### YAML Format

```yaml
# Web3 Security Auditor Agent Configuration
type: web3_audit
name: web3-auditor
model: qwen2.5:7b

# Optional: Custom system prompt
system_prompt: |
  Your custom prompt here...

# MCP Servers to connect to
servers:
  paths:
    - /path/to/filesystem-server.py
  urls:
    - https://audit-tools.example.com/mcp
  config_file: ~/.config/ollmcp/audit-servers.json

# Tools to enable
enabled_tools:
  - filesystem.read_file
  - filesystem.list_directory
  - bash.execute_command
```

### JSON Format

```json
{
  "type": "base",
  "name": "hardhat-analyzer",
  "model": "qwen2.5:7b",
  "description": "Specialized agent for Hardhat project analysis",
  "system_prompt": "You are an expert in Hardhat development...",
  "servers": {
    "paths": ["/path/to/filesystem-server.py"]
  },
  "enabled_tools": [
    "filesystem.read_file",
    "nodejs.run_npm_command"
  ]
}
```

## Example Configurations

Three example configurations are provided in `config/agents/`:

1. **web3_auditor.yaml**: General Web3 security auditing
2. **foundry_tester.yaml**: Foundry testing and fuzzing specialist
3. **hardhat_analyzer.json**: Hardhat project analysis

## Use Cases

### Smart Contract Security Audit

```
1. Create a Web3 audit agent
2. Connect it to filesystem and bash MCP servers
3. Execute task: "Analyze the smart contract at /path/to/Contract.sol"
4. Agent will:
   - Read the contract file
   - Run static analysis tools (Slither)
   - Execute tests if available
   - Generate a comprehensive security report
```

### Foundry Test Suite Development

```
1. Load the foundry_tester agent from config
2. Execute task: "Create comprehensive tests for /path/to/project"
3. Agent will:
   - Analyze existing contracts
   - Write property-based tests
   - Set up fuzzing campaigns
   - Generate coverage reports
```

### Multi-Agent Workflow

```
# Agent 1: Code Auditor
Task: "Analyze all contracts in /project/src for vulnerabilities"

# Agent 2: Test Developer
Task: "Create tests for the vulnerabilities found"

# Agent 3: Report Generator
Task: "Generate a comprehensive audit report with findings and test results"
```

## Agent-Specific Features

### Web3AuditAgent Methods

The Web3AuditAgent class provides specialized methods:

```python
# Analyze a contract
await agent.analyze_contract(
    contract_path="/path/to/Contract.sol",
    analysis_type="full"  # "quick", "full", or "deep"
)

# Run Foundry tests
await agent.run_foundry_tests("/path/to/project")

# Run Slither analysis
await agent.run_slither_analysis("/path/to/Contract.sol")

# Generate audit report
report = await agent.generate_audit_report()

# Add manual findings
agent.add_finding(
    title="Reentrancy Vulnerability",
    severity="High",
    description="...",
    location="Contract.sol:42",
    recommendation="Use ReentrancyGuard"
)

# Get findings summary
summary = agent.get_findings_summary()
# Returns: {"Critical": 0, "High": 2, "Medium": 5, ...}
```

## Best Practices

1. **Specialized Agents**: Create separate agents for different tasks rather than one general-purpose agent
2. **Tool Access**: Only enable the tools each agent actually needs
3. **System Prompts**: Be specific about the agent's expertise and responsibilities
4. **Server Connections**: Connect agents to appropriate MCP servers for their tasks
5. **Model Selection**: Choose models based on task complexity (larger models for complex analysis)

## Programmatic Usage

### Creating Agents Programmatically

```python
from mcp_client_for_ollama.agents.manager import AgentManager
from mcp_client_for_ollama.agents.web3_audit import Web3AuditAgent

# Create agent manager
agent_manager = AgentManager(console, ollama_client, exit_stack)

# Create a Web3 audit agent
agent = agent_manager.create_agent(
    agent_type="web3_audit",
    name="my-auditor",
    model="qwen2.5:7b"
)

# Connect to servers
await agent.connect_to_servers(
    server_paths=["/path/to/filesystem-server.py"],
    config_path="~/.config/ollmcp/servers.json"
)

# Execute a task
result = await agent_manager.execute_agent_task(
    agent_name="my-auditor",
    task="Analyze the contract at /path/to/Contract.sol"
)
```

### Loading from Configuration

```python
# Load agent from config file
agent = await agent_manager.create_agent_from_config(
    "config/agents/web3_auditor.yaml"
)

# Execute task
result = await agent.execute_task(
    "Run a comprehensive security audit on /path/to/project"
)
```

## Advanced Features

### Agent Orchestration

Coordinate multiple agents for complex workflows:

```python
# Agent 1: Initial scan
scan_result = await auditor.analyze_contract(contract_path)

# Agent 2: Deep dive on findings
for finding in scan_result.high_severity:
    analysis = await deep_analyzer.execute_task(
        f"Analyze this vulnerability: {finding}"
    )

# Agent 3: Generate report
report = await reporter.generate_audit_report()
```

### Custom Agent Types

Create your own agent types by extending `SubAgent`:

```python
from mcp_client_for_ollama.agents.base import SubAgent

class MyCustomAgent(SubAgent):
    def __init__(self, name, ...):
        super().__init__(
            name=name,
            description="My custom agent",
            model="qwen2.5:7b",
            system_prompt="Custom system prompt..."
        )
    
    async def custom_method(self):
        # Your custom functionality
        pass
```

## Troubleshooting

### Agent Creation Fails

- Ensure the model specified is available in Ollama
- Check that configuration file syntax is valid YAML/JSON
- Verify server paths exist and are accessible

### Agent Can't Connect to Servers

- Confirm MCP servers are running
- Check server paths/URLs in configuration
- Ensure proper permissions for server files

### Agent Tasks Fail

- Verify agent has necessary tools enabled
- Check that tools are available in connected MCP servers
- Review agent's system prompt for task compatibility

## Future Enhancements

Planned features for agents:
- Agent templates library
- Agent conversation history export
- Multi-agent collaboration protocols
- Agent performance metrics
- Agent state persistence
- Remote agent deployment

## Contributing

To add new agent types or improve existing ones:
1. Create a new class extending `SubAgent` or specialized agents
2. Add configuration examples in `config/agents/`
3. Update documentation
4. Submit a pull request

## Related Documentation

- [MCP Protocol](https://modelcontextprotocol.io/)
- [Ollama Models](https://ollama.com/library)
- [Web3 Security Tools](https://github.com/topics/smart-contract-security)
