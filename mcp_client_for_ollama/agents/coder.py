"""Specialized agent for code generation and modification."""

from typing import Optional, List, Dict, Any
from rich.console import Console
import ollama
from contextlib import AsyncExitStack

from .base import SubAgent
from .communication import MessageBroker


class CoderAgent(SubAgent):
    """Specialized agent for code generation and modification.
    
    This agent is optimized for:
    - Writing new code in various languages
    - Refactoring existing code
    - Fixing bugs and issues
    - Implementing features
    - Code optimization
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert software engineer specializing in code generation and modification.

Your responsibilities include:
1. Writing clean, efficient, and maintainable code
2. Following best practices and design patterns
3. Implementing features according to specifications
4. Refactoring code to improve quality
5. Fixing bugs and errors
6. Optimizing code performance
7. Writing comprehensive documentation and comments

When writing code:
- Follow the language's style guide and conventions
- Write self-documenting code with clear variable/function names
- Add comments for complex logic
- Handle edge cases and errors appropriately
- Consider performance and scalability
- Use appropriate design patterns
- Write modular, reusable code
- Include type hints where applicable

Supported languages:
- Python, JavaScript/TypeScript, Solidity, Rust, Go, Java, C++, and more

Always provide complete, working code that can be directly used or tested.
"""
    
    def __init__(
        self,
        name: str = "coder",
        model: str = "qwen2.5-coder:7b",
        console: Optional[Console] = None,
        ollama_client: Optional[ollama.AsyncClient] = None,
        parent_exit_stack: Optional[AsyncExitStack] = None,
        message_broker: Optional[MessageBroker] = None,
        custom_prompt: Optional[str] = None
    ):
        """Initialize Coder agent."""
        description = "Specialized agent for code generation and modification"
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
        
        self.code_files_created: List[str] = []
        self.code_files_modified: List[str] = []
    
    async def implement_feature(
        self,
        feature_description: str,
        language: str,
        context: Optional[str] = None
    ) -> str:
        """Implement a new feature.
        
        Args:
            feature_description: Description of feature to implement
            language: Programming language
            context: Optional context about the codebase
            
        Returns:
            str: Implementation code
        """
        task = f"""Implement the following feature in {language}:

Feature: {feature_description}

{f'Context: {context}' if context else ''}

Please provide:
1. Complete, working code
2. Inline comments explaining complex logic
3. Usage examples
4. Any dependencies or requirements
5. Error handling

Ensure the code is production-ready and follows best practices.
"""
        
        result = await self.execute_task(task)
        
        await self.remember(
            f"Implemented feature: {feature_description} in {language}",
            importance=3,
            tags=["coding", "feature", language]
        )
        
        return result
    
    async def fix_bug(self, bug_description: str, code: str, language: str) -> str:
        """Fix a bug in code.
        
        Args:
            bug_description: Description of the bug
            code: Code containing the bug
            language: Programming language
            
        Returns:
            str: Fixed code with explanation
        """
        task = f"""Fix the following bug in {language} code:

Bug Description: {bug_description}

Code:
```{language}
{code}
```

Please provide:
1. Explanation of what caused the bug
2. Fixed code
3. Explanation of the fix
4. Any additional improvements made
5. How to verify the fix
"""
        
        return await self.execute_task(task)
    
    async def refactor_code(self, code: str, language: str, goals: Optional[List[str]] = None) -> str:
        """Refactor code to improve quality.
        
        Args:
            code: Code to refactor
            language: Programming language
            goals: Optional specific refactoring goals
            
        Returns:
            str: Refactored code with explanation
        """
        goals_text = "\n".join(f"- {goal}" for goal in (goals or ["Improve readability", "Improve maintainability"]))
        
        task = f"""Refactor the following {language} code:

Refactoring Goals:
{goals_text}

Code:
```{language}
{code}
```

Please provide:
1. Refactored code
2. Explanation of changes made
3. Benefits of the refactoring
4. Any potential risks or considerations
"""
        
        return await self.execute_task(task)
    
    async def create_file(self, filepath: str, content: str, description: str) -> str:
        """Create a new code file.
        
        Args:
            filepath: Path for the new file
            content: File content
            description: Description of the file
            
        Returns:
            str: Confirmation message
        """
        task = f"""Create a new file at {filepath}:

Description: {description}

Content:
{content}

Use the filesystem tools to create this file.
"""
        
        result = await self.execute_task(task)
        self.code_files_created.append(filepath)
        
        return result
    
    async def execute_code(
        self,
        code: str,
        language: str,
        args: Optional[List[str]] = None
    ) -> str:
        """Execute code and return output.
        
        Args:
            code: Code to execute
            language: Programming language
            args: Optional command-line arguments
            
        Returns:
            str: Execution output
        """
        task = f"""Execute the following {language} code:

```{language}
{code}
```

{f'Arguments: {args}' if args else ''}

Use the bash/shell tools to:
1. Save the code to a temporary file
2. Execute it with the appropriate interpreter/compiler
3. Capture and return the output
4. Include any errors or warnings
"""
        
        return await self.execute_task(task)
