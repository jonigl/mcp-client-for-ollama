"""Specialized agent for writing documentation and reports."""

from typing import Optional, List, Dict, Any
from rich.console import Console
import ollama
from contextlib import AsyncExitStack

from .base import SubAgent
from .communication import MessageBroker


class WriterAgent(SubAgent):
    """Specialized agent for documentation and report writing.
    
    This agent is optimized for:
    - Technical documentation
    - API documentation
    - User guides and tutorials
    - Reports and summaries
    - README files
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert technical writer specializing in clear, comprehensive documentation.

Your responsibilities include:
1. Writing clear, well-structured documentation
2. Creating user guides and tutorials
3. Documenting APIs and code
4. Writing technical reports
5. Creating README files and project documentation
6. Ensuring consistency in style and terminology

When writing documentation:
- Use clear, concise language
- Organize content logically with proper headings
- Include examples and code snippets where appropriate
- Consider the target audience's technical level
- Use consistent formatting and terminology
- Include diagrams or visuals when helpful
- Provide step-by-step instructions
- Anticipate common questions and address them

Documentation should be:
- Clear: Easy to understand for the target audience
- Complete: Cover all necessary information
- Correct: Technically accurate
- Consistent: Uniform style and terminology
- Concise: No unnecessary verbosity
- Well-formatted: Use markdown or appropriate formatting
"""
    
    def __init__(
        self,
        name: str = "writer",
        model: str = "qwen2.5:7b",
        console: Optional[Console] = None,
        ollama_client: Optional[ollama.AsyncClient] = None,
        parent_exit_stack: Optional[AsyncExitStack] = None,
        message_broker: Optional[MessageBroker] = None,
        custom_prompt: Optional[str] = None
    ):
        """Initialize Writer agent."""
        description = "Specialized agent for documentation and report writing"
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
        
        self.documents_created: List[str] = []
    
    async def write_documentation(
        self,
        topic: str,
        doc_type: str = "general",
        details: Optional[Dict[str, Any]] = None
    ) -> str:
        """Write documentation.
        
        Args:
            topic: Topic to document
            doc_type: Type of documentation (readme, api, guide, tutorial, etc.)
            details: Additional details and context
            
        Returns:
            str: Generated documentation
        """
        details_text = "\n".join(
            f"{k}: {v}" for k, v in (details or {}).items()
        )
        
        task = f"""Write {doc_type} documentation for: {topic}

{f'Additional Details:\n{details_text}' if details else ''}

Please create comprehensive documentation that includes:
1. Overview/Introduction
2. Main content organized with clear headings
3. Examples and code snippets (if applicable)
4. Usage instructions
5. Configuration or setup (if applicable)
6. Common issues and troubleshooting
7. References or further reading

Use markdown formatting for clarity.
"""
        
        result = await self.execute_task(task)
        
        await self.remember(
            f"Wrote {doc_type} documentation for: {topic}",
            importance=2,
            tags=["documentation", doc_type]
        )
        
        return result
    
    async def write_readme(
        self,
        project_name: str,
        description: str,
        features: Optional[List[str]] = None,
        installation: Optional[str] = None,
        usage: Optional[str] = None
    ) -> str:
        """Write a README file.
        
        Args:
            project_name: Name of the project
            description: Project description
            features: List of features
            installation: Installation instructions
            usage: Usage instructions
            
        Returns:
            str: README content
        """
        features_text = "\n".join(f"- {f}" for f in (features or []))
        
        task = f"""Write a comprehensive README.md for the project: {project_name}

Description: {description}

{f'Features:\n{features_text}' if features else ''}
{f'Installation: {installation}' if installation else ''}
{f'Usage: {usage}' if usage else ''}

The README should include:
1. Project title and description
2. Key features
3. Installation instructions
4. Usage examples
5. Configuration options
6. Contributing guidelines
7. License information
8. Contact/support information

Use markdown formatting with appropriate badges and structure.
"""
        
        return await self.execute_task(task)
    
    async def write_api_docs(
        self,
        api_name: str,
        endpoints: List[Dict[str, Any]]
    ) -> str:
        """Write API documentation.
        
        Args:
            api_name: Name of the API
            endpoints: List of endpoint information
            
        Returns:
            str: API documentation
        """
        endpoints_text = "\n".join(
            f"- {ep.get('method', 'GET')} {ep.get('path', '/')}: {ep.get('description', '')}"
            for ep in endpoints
        )
        
        task = f"""Write comprehensive API documentation for: {api_name}

Endpoints:
{endpoints_text}

For each endpoint, document:
1. HTTP method and path
2. Description and purpose
3. Request parameters
4. Request body (if applicable)
5. Response format
6. Status codes
7. Example request/response
8. Error handling

Include:
- Authentication requirements
- Rate limiting
- Base URL
- Common headers
- General usage guidelines

Use markdown formatting with clear examples.
"""
        
        return await self.execute_task(task)
    
    async def generate_report(
        self,
        title: str,
        data: Dict[str, Any],
        report_type: str = "general"
    ) -> str:
        """Generate a report.
        
        Args:
            title: Report title
            data: Data to include in report
            report_type: Type of report
            
        Returns:
            str: Generated report
        """
        data_text = "\n".join(f"{k}: {v}" for k, v in data.items())
        
        task = f"""Generate a {report_type} report titled: {title}

Data:
{data_text}

The report should include:
1. Executive summary
2. Detailed findings organized by topic
3. Data analysis and insights
4. Visualizations or tables (described in text)
5. Conclusions
6. Recommendations
7. Appendices (if needed)

Use professional formatting with clear sections.
"""
        
        result = await self.execute_task(task)
        self.documents_created.append(title)
        
        return result
