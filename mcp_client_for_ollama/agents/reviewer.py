"""Specialized agent for code review and quality assurance."""

from typing import Optional, List, Dict, Any
from rich.console import Console
import ollama
from contextlib import AsyncExitStack

from .base import SubAgent
from .communication import MessageBroker


class ReviewerAgent(SubAgent):
    """Specialized agent for code review and quality assurance.
    
    This agent is optimized for:
    - Code review and feedback
    - Security analysis
    - Performance review
    - Best practices validation
    - Architecture review
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert code reviewer specializing in quality assurance and best practices.

Your responsibilities include:
1. Reviewing code for quality, maintainability, and correctness
2. Identifying security vulnerabilities
3. Suggesting improvements and optimizations
4. Ensuring adherence to best practices
5. Checking code style and consistency
6. Reviewing architecture and design decisions
7. Providing constructive feedback

When reviewing code, check for:
- Correctness: Does the code work as intended?
- Security: Are there security vulnerabilities?
- Performance: Are there optimization opportunities?
- Maintainability: Is the code easy to understand and modify?
- Style: Does it follow conventions and style guides?
- Testing: Is there adequate test coverage?
- Documentation: Is the code well-documented?
- Error handling: Are errors handled appropriately?
- Edge cases: Are edge cases considered?
- Design: Is the architecture sound?

Provide feedback that is:
- Specific: Point to exact lines or issues
- Constructive: Suggest improvements, not just criticism
- Prioritized: Highlight critical issues first
- Actionable: Provide clear steps to address issues
- Balanced: Acknowledge good practices as well

Use a professional, helpful tone in all reviews.
"""
    
    def __init__(
        self,
        name: str = "reviewer",
        model: str = "qwen2.5:7b",
        console: Optional[Console] = None,
        ollama_client: Optional[ollama.AsyncClient] = None,
        parent_exit_stack: Optional[AsyncExitStack] = None,
        message_broker: Optional[MessageBroker] = None,
        custom_prompt: Optional[str] = None
    ):
        """Initialize Reviewer agent."""
        description = "Specialized agent for code review and quality assurance"
        system_prompt = custom_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        super().__init__(
            name=name,
            description=description,
            model=model,
            system_prompt=system_prompt,
            console=console,
            ollama_client=ollama_client,
            parent_exit_stack=parent_exit_stack,
            message_broker=message_broker,
            enable_memory=True
        )
        
        self.reviews_conducted: List[Dict[str, Any]] = []
        self.issues_found: List[Dict[str, Any]] = []
    
    async def review_code(
        self,
        code: str,
        language: str,
        focus_areas: Optional[List[str]] = None,
        context: Optional[str] = None
    ) -> str:
        """Review code and provide feedback.
        
        Args:
            code: Code to review
            language: Programming language
            focus_areas: Specific areas to focus on
            context: Additional context about the code
            
        Returns:
            str: Review feedback
        """
        focus_text = "\n".join(f"- {area}" for area in (focus_areas or ["General quality"]))
        
        task = f"""Review the following {language} code:

{f'Context: {context}' if context else ''}

Focus Areas:
{focus_text}

Code:
```{language}
{code}
```

Please provide a comprehensive code review including:
1. Overall assessment
2. Issues found (categorized by severity: Critical/High/Medium/Low)
3. Specific feedback on:
   - Code correctness
   - Security concerns
   - Performance issues
   - Maintainability
   - Style and conventions
   - Error handling
   - Edge cases
4. Positive aspects (what's done well)
5. Recommended improvements with examples
6. Priority of changes (what to fix first)

Format the review clearly with sections and actionable items.
"""
        
        result = await self.execute_task(task)
        
        self.reviews_conducted.append({
            "language": language,
            "focus_areas": focus_areas or [],
            "summary": result[:200]
        })
        
        await self.remember(
            f"Reviewed {language} code focusing on: {', '.join(focus_areas or ['general quality'])}",
            importance=2,
            tags=["review", language]
        )
        
        return result
    
    async def security_review(self, code: str, language: str) -> str:
        """Perform security-focused code review.
        
        Args:
            code: Code to review
            language: Programming language
            
        Returns:
            str: Security review
        """
        task = f"""Perform a security review of the following {language} code:

```{language}
{code}
```

Please analyze for:
1. Common vulnerabilities (OWASP Top 10)
2. Input validation issues
3. Authentication/authorization flaws
4. Injection vulnerabilities
5. Insecure data handling
6. Cryptography issues
7. Access control problems
8. Information disclosure
9. Dependency vulnerabilities
10. Configuration issues

For each issue found:
- Severity level
- Exact location
- Description of vulnerability
- Potential impact
- Remediation steps

Provide a security risk assessment summary.
"""
        
        result = await self.execute_task(task)
        
        # Track security issues
        self.issues_found.append({
            "type": "security",
            "language": language,
            "summary": result[:200]
        })
        
        return result
    
    async def performance_review(self, code: str, language: str) -> str:
        """Review code for performance issues.
        
        Args:
            code: Code to review
            language: Programming language
            
        Returns:
            str: Performance review
        """
        task = f"""Review the following {language} code for performance:

```{language}
{code}
```

Please analyze:
1. Time complexity of algorithms
2. Space complexity and memory usage
3. Unnecessary iterations or operations
4. Database query optimization
5. Caching opportunities
6. Resource management
7. Scalability concerns
8. Bottlenecks

For each issue:
- Current implementation
- Performance impact
- Optimization suggestion
- Expected improvement

Provide an overall performance assessment.
"""
        
        return await self.execute_task(task)
    
    async def architecture_review(
        self,
        project_path: str,
        description: str
    ) -> str:
        """Review software architecture.
        
        Args:
            project_path: Path to project
            description: Description of the system
            
        Returns:
            str: Architecture review
        """
        task = f"""Review the architecture of the project at: {project_path}

Project Description: {description}

Please analyze:
1. Overall architecture and design patterns
2. Component organization and separation of concerns
3. Dependencies and coupling
4. Scalability and extensibility
5. Maintainability
6. Testability
7. Security design
8. Error handling strategy
9. Data flow and state management
10. Adherence to SOLID principles

Provide:
- Strengths of current architecture
- Areas for improvement
- Specific recommendations
- Potential risks

Include both high-level and specific technical feedback.
"""
        
        return await self.execute_task(task)
    
    async def review_pull_request(
        self,
        diff: str,
        pr_description: str,
        language: str
    ) -> str:
        """Review a pull request.
        
        Args:
            diff: Git diff of changes
            pr_description: PR description
            language: Primary programming language
            
        Returns:
            str: PR review
        """
        task = f"""Review the following pull request:

Description: {pr_description}

Changes:
```diff
{diff}
```

Please provide:
1. Overall assessment (Approve/Request Changes/Comment)
2. Changes review:
   - What's being changed and why
   - Impact of changes
   - Potential risks
3. Code quality feedback
4. Security considerations
5. Performance implications
6. Test coverage adequacy
7. Documentation updates needed
8. Specific inline comments on critical issues

Be thorough but constructive in your feedback.
"""
        
        result = await self.execute_task(task)
        
        self.reviews_conducted.append({
            "type": "pull_request",
            "language": language,
            "summary": pr_description[:100]
        })
        
        return result
    
    def add_issue(
        self,
        severity: str,
        category: str,
        description: str,
        location: str,
        recommendation: str
    ) -> None:
        """Add an issue found during review.
        
        Args:
            severity: Issue severity
            category: Issue category
            description: Issue description
            location: Location in code
            recommendation: Recommended fix
        """
        issue = {
            "severity": severity,
            "category": category,
            "description": description,
            "location": location,
            "recommendation": recommendation
        }
        self.issues_found.append(issue)
    
    def get_review_summary(self) -> Dict[str, Any]:
        """Get summary of reviews conducted.
        
        Returns:
            Dict with review statistics
        """
        return {
            "total_reviews": len(self.reviews_conducted),
            "total_issues": len(self.issues_found),
            "issues_by_severity": self._count_by_severity(),
            "recent_reviews": self.reviews_conducted[-5:]
        }
    
    def _count_by_severity(self) -> Dict[str, int]:
        """Count issues by severity."""
        counts = {"Critical": 0, "High": 0, "Medium": 0, "Low": 0}
        for issue in self.issues_found:
            severity = issue.get("severity", "Low")
            if severity in counts:
                counts[severity] += 1
        return counts
