# Web3 Security Audit Quick Start Guide

This guide will help you get started with using specialized agents for Web3 smart contract security auditing.

## Prerequisites

1. **Ollama** installed and running
2. **MCP Client for Ollama** installed
3. At least one MCP server with filesystem and/or bash tools
4. Optional: Security tools installed (Slither, Mythril, Foundry)

## Basic Setup

### 1. Start the Client

```bash
ollmcp
```

### 2. Connect to MCP Servers (if not auto-discovered)

If you haven't configured MCP servers yet:

```bash
# Option 1: Use command-line arguments
ollmcp --mcp-server /path/to/filesystem-server.py

# Option 2: Use a configuration file
ollmcp --servers-json ~/.config/ollmcp/servers.json
```

### 3. Open the Agent Menu

In the client, type:
```
agent
```
or
```
ag
```

## Creating Your First Audit Agent

### Method 1: Interactive Creation

1. In the agent menu, select **"1. Create a new agent"**
2. Choose agent type: `web3_audit`
3. Enter agent name: `my-auditor`
4. Enter model: `qwen2.5:7b` (or your preferred model)
5. Connect to MCP servers: `yes`
6. Choose: `1` (Use same servers as main client)

### Method 2: Load from Configuration

1. In the agent menu, select **"4. Load agent from config file"**
2. Enter path: `config/agents/web3_auditor.yaml`
3. Update the server paths in the YAML file first!

## Running Your First Audit

### Simple Contract Analysis

1. In the agent menu, select **"3. Execute task with agent"**
2. Select your agent: `my-auditor`
3. Enter task:
```
Analyze the smart contract at /path/to/MyContract.sol and identify any security vulnerabilities
```

### Comprehensive Project Audit

Task example:
```
Perform a comprehensive security audit of the Solidity project at /path/to/project. 
Check all contracts in the src/ directory, run Slither if available, and generate 
a detailed report with findings classified by severity.
```

### Foundry Project Analysis

Task example:
```
Analyze the Foundry project at /path/to/foundry-project. 
Run the existing test suite with 'forge test -vvv', analyze the results, 
and suggest additional tests for uncovered scenarios.
```

## Example Workflows

### Workflow 1: Quick Security Scan

**Goal**: Quickly scan a contract for common vulnerabilities

**Steps**:
1. Create agent: `quick-scanner`
2. Task: `Read /path/to/Contract.sol and check for: reentrancy, integer overflow, access control issues, and unsafe external calls`
3. Review findings in the response

**Expected Output**:
- List of potential vulnerabilities
- Code locations
- Risk levels
- Quick recommendations

### Workflow 2: Deep Security Audit

**Goal**: Comprehensive security audit with tool execution

**Steps**:
1. Create agent: `deep-auditor` (with bash tools enabled)
2. Task: 
```
Perform a deep security audit on /path/to/Contract.sol:
1. Read and analyze the contract code
2. Run Slither: slither /path/to/Contract.sol
3. Check for common vulnerabilities
4. Generate a detailed audit report with severity ratings
```

**Expected Output**:
- Complete audit report
- Slither analysis results
- Manual code review findings
- Recommendations for fixes

### Workflow 3: Test Coverage Analysis

**Goal**: Analyze and improve test coverage

**Steps**:
1. Load agent: `config/agents/foundry_tester.yaml`
2. Task:
```
Analyze the Foundry project at /path/to/project:
1. Run existing tests: forge test
2. Check coverage: forge coverage
3. Identify untested scenarios
4. Suggest additional test cases
```

**Expected Output**:
- Test results
- Coverage report
- List of untested code paths
- Suggested test cases

### Workflow 4: Multi-Contract Analysis

**Goal**: Audit multiple related contracts

**Steps**:
1. Create agent: `project-auditor`
2. Task:
```
Audit all contracts in /path/to/project/src:
1. List all Solidity files
2. Analyze each contract for vulnerabilities
3. Check for cross-contract interaction issues
4. Generate a project-wide security report
```

**Expected Output**:
- Per-contract analysis
- Cross-contract vulnerability assessment
- Project-level security report

## Advanced Usage

### Using Multiple Specialized Agents

Create different agents for different tasks:

```
Agent 1: "vulnerability-scanner"
- Focus: Finding vulnerabilities
- System prompt: Emphasizes security issues

Agent 2: "code-optimizer"
- Focus: Gas optimization
- System prompt: Emphasizes efficiency

Agent 3: "test-engineer"
- Focus: Test coverage
- System prompt: Emphasizes testing strategies
```

Then orchestrate them:
1. Run vulnerability scan with Agent 1
2. Get optimization suggestions from Agent 2
3. Generate test cases with Agent 3

### Customizing Agent Prompts

Edit configuration files to specialize agents:

```yaml
type: web3_audit
name: defi-specialist
model: qwen2.5:7b

system_prompt: |
  You are a DeFi security specialist focusing on:
  - AMM vulnerabilities (price manipulation, sandwich attacks)
  - Flash loan attack vectors
  - Oracle manipulation
  - Liquidity pool exploits
  - MEV considerations
  
  Prioritize DeFi-specific vulnerabilities in your analysis.
```

### Integration with CI/CD

Use agents programmatically for automated audits:

```python
from mcp_client_for_ollama.agents.manager import AgentManager

# Create agent
manager = AgentManager(console, ollama_client, exit_stack)
agent = await manager.create_agent_from_config("config/agents/web3_auditor.yaml")

# Connect to servers
await agent.connect_to_servers(config_path="~/.config/ollmcp/servers.json")

# Run audit
result = await agent.execute_task(
    "Audit all contracts in ./src and fail if critical issues found"
)

# Parse results and exit with appropriate code
if "Critical" in result or "High" in result:
    sys.exit(1)
```

## Tips and Best Practices

### 1. Start Small
- Begin with single contract analysis
- Test agent responses before complex workflows
- Verify tool availability before running commands

### 2. Be Specific in Tasks
Good: "Analyze MyToken.sol for reentrancy vulnerabilities in the transfer function"
Bad: "Check the contract"

### 3. Use Appropriate Models
- `qwen2.5:7b`: Good for general analysis
- `llama3:13b`: Better for complex reasoning
- `deepseek-r1`: Best for deep analysis (if available)

### 4. Enable Relevant Tools
Only enable tools the agent actually needs:
- Filesystem: For reading contracts
- Bash: For running security tools
- Avoid unnecessary tools to reduce confusion

### 5. Review and Verify
- Always review agent findings manually
- Run suggested commands to verify
- Cross-reference with known vulnerabilities
- Use multiple tools for confirmation

### 6. Maintain Context
For multi-step audits, keep agents in conversation:
- Don't create new agent for each step
- Build on previous findings
- Reference earlier analysis

## Common Issues and Solutions

### Issue: Agent can't read files

**Solution**: 
- Ensure filesystem MCP server is connected
- Verify file paths are correct
- Check file permissions

### Issue: Security tools not found

**Solution**:
- Ensure bash MCP server is connected
- Install required tools (Slither, Mythril, etc.)
- Use full paths to executables
- Check PATH environment variable

### Issue: Agent responses are too general

**Solution**:
- Be more specific in task description
- Mention specific vulnerability types to check
- Request code snippets in findings
- Ask for specific tool execution

### Issue: Agent timeout on large projects

**Solution**:
- Break analysis into smaller tasks
- Analyze contracts individually
- Use file listings first, then detailed analysis
- Increase task-specific timeouts if possible

## Security Considerations

### Agent Safety
- Agents execute commands through MCP servers
- Always review commands before execution if HIL is enabled
- Be cautious with write operations
- Test in isolated environments first

### Data Privacy
- Don't use agents with proprietary code in cloud setups
- Keep sensitive contracts in local analysis only
- Review agent system prompts for data handling

### Validation
- Never rely solely on agent findings
- Always perform manual verification
- Use multiple analysis tools
- Have human experts review critical findings

## Next Steps

1. **Learn More**: Read [docs/AGENTS.md](AGENTS.md) for detailed documentation
2. **Customize**: Create your own agent configurations
3. **Integrate**: Add agents to your development workflow
4. **Contribute**: Share useful agent configurations with the community

## Resources

- [Slither Documentation](https://github.com/crytic/slither)
- [Foundry Book](https://book.getfoundry.sh/)
- [Smart Contract Security Best Practices](https://consensys.github.io/smart-contract-best-practices/)
- [MCP Protocol](https://modelcontextprotocol.io/)

## Getting Help

If you encounter issues:
1. Check the [troubleshooting section](AGENTS.md#troubleshooting) in the main docs
2. Review [config/agents/README.md](../config/agents/README.md) for configuration help
3. Open an issue on GitHub with:
   - Agent configuration used
   - Task description
   - Error messages or unexpected behavior
   - MCP servers connected
