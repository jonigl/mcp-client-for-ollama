"""Specialized agent for test creation and execution."""

from typing import Optional, List, Dict, Any
from rich.console import Console
import ollama
from contextlib import AsyncExitStack

from .base import SubAgent
from .communication import MessageBroker


class TesterAgent(SubAgent):
    """Specialized agent for test creation and execution.
    
    This agent is optimized for:
    - Writing unit tests
    - Writing integration tests
    - Running test suites
    - Analyzing test coverage
    - Identifying test cases
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert QA engineer specializing in software testing.

Your responsibilities include:
1. Writing comprehensive test cases
2. Creating unit and integration tests
3. Running test suites and analyzing results
4. Identifying edge cases and scenarios
5. Ensuring adequate test coverage
6. Performing bug verification
7. Writing test documentation

When creating tests:
- Cover normal, edge, and error cases
- Use appropriate testing frameworks
- Write clear, descriptive test names
- Include assertions for all important behaviors
- Test both positive and negative scenarios
- Consider boundary conditions
- Mock external dependencies appropriately
- Ensure tests are deterministic and isolated

Test types:
- Unit tests: Test individual functions/methods
- Integration tests: Test component interactions
- End-to-end tests: Test complete workflows
- Property-based tests: Test with generated inputs
- Performance tests: Test speed and efficiency

Always aim for high code coverage while ensuring tests are meaningful and maintainable.
"""
    
    def __init__(
        self,
        name: str = "tester",
        model: str = "qwen2.5:7b",
        console: Optional[Console] = None,
        ollama_client: Optional[ollama.AsyncClient] = None,
        parent_exit_stack: Optional[AsyncExitStack] = None,
        message_broker: Optional[MessageBroker] = None,
        custom_prompt: Optional[str] = None
    ):
        """Initialize Tester agent."""
        description = "Specialized agent for test creation and execution"
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
        
        self.test_results: List[Dict[str, Any]] = []
        self.test_files_created: List[str] = []
    
    async def write_unit_tests(
        self,
        code: str,
        language: str,
        test_framework: Optional[str] = None
    ) -> str:
        """Write unit tests for code.
        
        Args:
            code: Code to test
            language: Programming language
            test_framework: Testing framework to use
            
        Returns:
            str: Generated unit tests
        """
        framework_text = f"using {test_framework}" if test_framework else ""
        
        task = f"""Write comprehensive unit tests {framework_text} for the following {language} code:

```{language}
{code}
```

Please provide:
1. Complete test file with imports
2. Test cases covering:
   - Normal/happy path scenarios
   - Edge cases
   - Error conditions
   - Boundary conditions
3. Clear, descriptive test names
4. Appropriate assertions
5. Setup/teardown if needed
6. Mock external dependencies

Aim for high code coverage while keeping tests clear and maintainable.
"""
        
        result = await self.execute_task(task)
        
        await self.remember(
            f"Created unit tests for {language} code",
            importance=2,
            tags=["testing", "unit-tests", language]
        )
        
        return result
    
    async def run_tests(
        self,
        test_path: str,
        test_framework: str,
        options: Optional[List[str]] = None
    ) -> str:
        """Run a test suite.
        
        Args:
            test_path: Path to test file or directory
            test_framework: Testing framework (pytest, jest, etc.)
            options: Optional test runner options
            
        Returns:
            str: Test results
        """
        options_text = " ".join(options or [])
        
        task = f"""Run the {test_framework} test suite at: {test_path}

{f'Options: {options_text}' if options else ''}

Please:
1. Execute the tests using bash/shell tools
2. Capture the output including:
   - Number of tests run
   - Passed/failed counts
   - Any error messages
   - Coverage report if available
3. Analyze the results
4. Identify any failing tests
5. Suggest fixes for failures if any

Provide a summary of test results.
"""
        
        result = await self.execute_task(task)
        
        # Store results
        self.test_results.append({
            "test_path": test_path,
            "framework": test_framework,
            "result": result[:500]  # Store summary
        })
        
        return result
    
    async def identify_test_cases(self, requirements: str) -> str:
        """Identify test cases from requirements.
        
        Args:
            requirements: Feature or function requirements
            
        Returns:
            str: List of test cases
        """
        task = f"""Identify comprehensive test cases for the following requirements:

Requirements:
{requirements}

Please provide:
1. List of test scenarios organized by category
2. For each test case:
   - Test name
   - Description
   - Preconditions
   - Steps to execute
   - Expected results
   - Priority (High/Medium/Low)
3. Include:
   - Positive test cases
   - Negative test cases
   - Edge cases
   - Boundary conditions
   - Error handling scenarios

Format as a clear, actionable test plan.
"""
        
        return await self.execute_task(task)
    
    async def analyze_coverage(self, project_path: str, language: str) -> str:
        """Analyze test coverage.
        
        Args:
            project_path: Path to project
            language: Programming language
            
        Returns:
            str: Coverage analysis
        """
        task = f"""Analyze test coverage for the {language} project at: {project_path}

Please:
1. Run the appropriate coverage tool
2. Generate coverage report
3. Analyze the results
4. Identify areas with low coverage
5. Suggest additional tests for uncovered code
6. Highlight critical paths that need testing

Provide a comprehensive coverage analysis with recommendations.
"""
        
        return await self.execute_task(task)
    
    async def write_integration_tests(
        self,
        components: List[str],
        language: str,
        test_framework: Optional[str] = None
    ) -> str:
        """Write integration tests.
        
        Args:
            components: List of components to test together
            language: Programming language
            test_framework: Testing framework to use
            
        Returns:
            str: Generated integration tests
        """
        components_text = ", ".join(components)
        framework_text = f"using {test_framework}" if test_framework else ""
        
        task = f"""Write integration tests {framework_text} for the following {language} components:

Components: {components_text}

Please provide:
1. Complete test file(s)
2. Tests for component interactions
3. Setup for test environment
4. Mock external services if needed
5. Test data setup/teardown
6. Assertions for integrated behavior
7. Error handling and edge cases

Focus on testing how components work together, not individual units.
"""
        
        result = await self.execute_task(task)
        self.test_files_created.append(f"integration_tests_{len(self.test_files_created)}")
        
        return result
    
    def get_test_summary(self) -> Dict[str, Any]:
        """Get summary of testing activities.
        
        Returns:
            Dict with test statistics
        """
        total_runs = len(self.test_results)
        files_created = len(self.test_files_created)
        
        return {
            "test_runs": total_runs,
            "test_files_created": files_created,
            "recent_results": self.test_results[-5:] if self.test_results else []
        }
