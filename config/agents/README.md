# Agent Configuration Examples

This directory contains example configuration files for specialized agents.

## Available Configurations

### 1. web3_auditor.yaml

**Purpose**: General-purpose Web3 smart contract security auditing agent.

**Capabilities**:
- Smart contract vulnerability detection
- Running security analysis tools (Slither, Mythril)
- Code review and best practices
- Severity classification of findings

**Tools Required**:
- Filesystem MCP server (for reading contracts)
- Bash MCP server (for running security tools)

**Usage**:
```bash
# In the agent menu, select "Load agent from config file"
Config file path: config/agents/web3_auditor.yaml
```

### 2. foundry_tester.yaml

**Purpose**: Specialized agent for Foundry testing and fuzzing.

**Capabilities**:
- Writing comprehensive Foundry tests
- Setting up fuzzing campaigns
- Analyzing test results and coverage
- Identifying edge cases and failure modes
- Optimizing test suites

**Tools Required**:
- Filesystem MCP server (for reading/writing test files)
- Bash MCP server (for running forge commands)

**Usage**:
```bash
# In the agent menu, select "Load agent from config file"
Config file path: config/agents/foundry_tester.yaml
```

### 3. hardhat_analyzer.json

**Purpose**: Specialized agent for Hardhat project analysis.

**Capabilities**:
- Analyzing Hardhat project structure
- Reviewing deployment scripts
- Executing and analyzing tests
- Optimizing gas usage
- Verifying contract interactions

**Tools Required**:
- Filesystem MCP server
- Node.js MCP server (for running npm/hardhat commands)

**Usage**:
```bash
# In the agent menu, select "Load agent from config file"
Config file path: config/agents/hardhat_analyzer.json
```

## Customizing Configurations

### Updating Server Paths

Before using these configurations, update the server paths to match your setup:

```yaml
servers:
  paths:
    - /path/to/your/filesystem-server.py  # Update this
    - /path/to/your/bash-server.py        # Update this
```

### Using Remote MCP Servers

You can also configure agents to use remote MCP servers via URLs:

```yaml
servers:
  urls:
    - https://your-audit-server.com/mcp
    - https://analysis-tools.example.com/mcp
```

### Using Existing Server Configurations

Point to your existing MCP server configuration file:

```yaml
servers:
  config_file: ~/.config/ollmcp/servers.json
```

### Customizing System Prompts

Each agent can have a custom system prompt. For example, to specialize the Web3 auditor:

```yaml
type: web3_audit
name: defi-auditor
model: qwen2.5:7b

system_prompt: |
  You are an expert DeFi security auditor specializing in:
  - Automated Market Makers (AMMs)
  - Lending protocols
  - Yield farming contracts
  - Flash loan attack vectors
  - Oracle manipulation
  
  Focus on DeFi-specific vulnerabilities and best practices.
```

### Selecting Different Models

You can specify different Ollama models based on task complexity:

```yaml
model: qwen2.5:7b        # Good for general tasks
# model: llama3:13b      # Better for complex analysis
# model: deepseek-r1     # Best for reasoning-heavy tasks
```

## Creating Your Own Agent Configurations

### YAML Format Template

```yaml
type: web3_audit  # or "base" for custom agents
name: my-custom-agent
model: qwen2.5:7b

# For base agents, include:
# description: Purpose of this agent
# system_prompt: |
#   Your detailed system prompt here...

servers:
  paths:
    - /path/to/server1.py
    - /path/to/server2.js
  # Or use URLs:
  # urls:
  #   - https://server.example.com/mcp
  # Or reference a config file:
  # config_file: ~/.config/ollmcp/my-servers.json

enabled_tools:
  - server1.tool_name
  - server2.other_tool
  # List specific tools to enable, or omit to enable all
```

### JSON Format Template

```json
{
  "type": "base",
  "name": "my-custom-agent",
  "model": "qwen2.5:7b",
  "description": "Purpose of this agent",
  "system_prompt": "Your detailed system prompt here...",
  "servers": {
    "paths": ["/path/to/server.py"],
    "urls": ["https://server.example.com/mcp"],
    "config_file": "~/.config/ollmcp/servers.json"
  },
  "enabled_tools": [
    "server.tool_name"
  ]
}
```

## Best Practices

1. **Specific Prompts**: Make system prompts as specific as possible to the agent's task
2. **Minimal Tools**: Only enable tools the agent actually needs
3. **Model Selection**: Use more capable models for complex analysis tasks
4. **Testing**: Test agents with simple tasks before complex workflows
5. **Documentation**: Document any custom agents you create for team use

## Example Workflows

### Complete Security Audit

1. Load `web3_auditor.yaml`
2. Task: "Perform a comprehensive security audit of /project/src"
3. Agent will analyze all contracts and generate a report

### Test Development

1. Load `foundry_tester.yaml`
2. Task: "Create a test suite for Contract.sol with 100% coverage"
3. Agent will write tests and run them

### Project Analysis

1. Load `hardhat_analyzer.json`
2. Task: "Analyze the Hardhat project at /project and identify deployment issues"
3. Agent will review configuration and scripts

## Troubleshooting

### Server Connection Issues

If the agent fails to connect to servers:
1. Verify server paths exist and are executable
2. Check that servers are compatible with MCP protocol
3. Ensure proper permissions on server files

### Tool Availability

If tools are not available:
1. Check that the specified tools exist on the connected servers
2. Verify tool names match the server's tool definitions
3. Enable tools manually if needed

### Configuration Parsing Errors

If the config file fails to load:
1. Validate YAML/JSON syntax using an online validator
2. Check for proper indentation (YAML is indent-sensitive)
3. Ensure all required fields are present

## Contributing

To contribute new agent configurations:
1. Create a new YAML or JSON file following the templates
2. Test thoroughly with actual tasks
3. Document the agent's purpose and capabilities
4. Submit a pull request

## Related Documentation

- [Main Agents Documentation](../../docs/AGENTS.md)
- [MCP Protocol](https://modelcontextprotocol.io/)
- [Ollama Models](https://ollama.com/library)
