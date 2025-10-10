"""Specialized agent for Web3 security auditing."""

from typing import Optional, List, Dict, Any
from rich.console import Console
import ollama
from contextlib import AsyncExitStack

from .base import SubAgent


class Web3AuditAgent(SubAgent):
    """Specialized agent for Web3 smart contract security auditing.
    
    This agent is pre-configured with tools and prompts optimized for:
    - Smart contract security analysis
    - Vulnerability detection
    - Code review and best practices
    - Integration with Foundry, Hardhat, Slither, and other audit tools
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert Web3 security auditor specializing in smart contract security analysis.

Your responsibilities include:
1. Analyzing smart contracts for security vulnerabilities
2. Identifying common attack vectors (reentrancy, overflow, access control, etc.)
3. Reviewing code for best practices and optimization opportunities
4. Running automated security tools (Slither, Mythril, Foundry tests)
5. Providing detailed reports with severity classifications
6. Suggesting fixes and improvements

When analyzing contracts:
- Always check for common vulnerabilities first
- Use available tools to verify findings
- Provide clear explanations with code examples
- Prioritize findings by severity (Critical, High, Medium, Low, Info)
- Consider gas optimization opportunities
- Verify against the latest security standards

You have access to tools for:
- Running Foundry tests and fuzzing
- Executing Hardhat scripts and tests
- Running static analysis with Slither
- Checking with Mythril
- File system operations for reading contracts
- Running shell commands for build and test operations
"""
    
    def __init__(
        self,
        name: str = "web3-auditor",
        model: str = "qwen2.5:7b",
        console: Optional[Console] = None,
        ollama_client: Optional[ollama.AsyncClient] = None,
        parent_exit_stack: Optional[AsyncExitStack] = None,
        custom_prompt: Optional[str] = None
    ):
        """Initialize Web3 audit agent.
        
        Args:
            name: Name for this agent instance
            model: Ollama model to use (default: qwen2.5:7b)
            console: Rich console for output
            ollama_client: Ollama client instance
            parent_exit_stack: Parent's exit stack for resource management
            custom_prompt: Custom system prompt (uses default if None)
        """
        description = "Specialized agent for Web3 smart contract security auditing"
        system_prompt = custom_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        super().__init__(
            name=name,
            description=description,
            model=model,
            system_prompt=system_prompt,
            console=console,
            ollama_client=ollama_client,
            parent_exit_stack=parent_exit_stack
        )
        
        # Audit-specific settings
        self.audit_findings: List[Dict[str, Any]] = []
        self.contracts_analyzed: List[str] = []
    
    async def analyze_contract(self, contract_path: str, analysis_type: str = "full") -> str:
        """Analyze a smart contract file.
        
        Args:
            contract_path: Path to the contract file
            analysis_type: Type of analysis ("quick", "full", "deep")
            
        Returns:
            str: Analysis report
        """
        task = f"""Analyze the smart contract at {contract_path}.
        
Analysis type: {analysis_type}

Please:
1. Read the contract file
2. Identify potential vulnerabilities
3. Run available static analysis tools
4. Provide a comprehensive report with findings
5. Classify findings by severity
6. Suggest fixes for identified issues
"""
        
        result = await self.execute_task(task)
        self.contracts_analyzed.append(contract_path)
        return result
    
    async def run_foundry_tests(self, project_path: str) -> str:
        """Run Foundry tests for a project.
        
        Args:
            project_path: Path to the Foundry project
            
        Returns:
            str: Test results
        """
        task = f"""Run Foundry tests for the project at {project_path}.

Please:
1. Navigate to the project directory
2. Run `forge test -vvv` to execute tests
3. Analyze any test failures
4. Provide a summary of test coverage and results
"""
        
        return await self.execute_task(task)
    
    async def run_slither_analysis(self, contract_or_project_path: str) -> str:
        """Run Slither static analysis.
        
        Args:
            contract_or_project_path: Path to contract file or project
            
        Returns:
            str: Slither analysis results
        """
        task = f"""Run Slither static analysis on {contract_or_project_path}.

Please:
1. Execute `slither {contract_or_project_path}`
2. Parse and categorize the findings
3. Filter out false positives if any
4. Provide a detailed report of vulnerabilities found
"""
        
        return await self.execute_task(task)
    
    async def generate_audit_report(self) -> str:
        """Generate a comprehensive audit report.
        
        Returns:
            str: Formatted audit report
        """
        task = f"""Generate a comprehensive audit report based on all analysis performed.

Contracts analyzed: {', '.join(self.contracts_analyzed) if self.contracts_analyzed else 'None'}

Please create a professional audit report including:
1. Executive Summary
2. Scope of Review
3. Findings (categorized by severity)
4. Detailed Vulnerability Descriptions
5. Recommendations
6. Conclusion

Format the report in markdown.
"""
        
        return await self.execute_task(task)
    
    def add_finding(
        self,
        title: str,
        severity: str,
        description: str,
        location: str,
        recommendation: str
    ) -> None:
        """Add a finding to the audit report.
        
        Args:
            title: Finding title
            severity: Severity level (Critical, High, Medium, Low, Info)
            description: Detailed description
            location: Code location
            recommendation: Recommended fix
        """
        finding = {
            "title": title,
            "severity": severity,
            "description": description,
            "location": location,
            "recommendation": recommendation
        }
        self.audit_findings.append(finding)
    
    def get_findings_summary(self) -> Dict[str, int]:
        """Get summary of findings by severity.
        
        Returns:
            Dict mapping severity to count
        """
        summary = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0,
            "Info": 0
        }
        
        for finding in self.audit_findings:
            severity = finding.get("severity", "Info")
            if severity in summary:
                summary[severity] += 1
        
        return summary
