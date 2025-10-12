"""Specialized agent for research and information gathering."""

from typing import Optional, List, Dict, Any
from rich.console import Console
import ollama
from contextlib import AsyncExitStack

from .base import SubAgent
from .communication import MessageBroker


class ResearcherAgent(SubAgent):
    """Specialized agent for research and information gathering.
    
    This agent is optimized for:
    - Web research and information gathering
    - Document analysis and summarization
    - Data collection and organization
    - Fact-checking and verification
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert research agent specializing in information gathering and analysis.

Your responsibilities include:
1. Conducting thorough research on topics using available tools
2. Analyzing and synthesizing information from multiple sources
3. Fact-checking and verifying information accuracy
4. Organizing findings in a clear, structured manner
5. Identifying knowledge gaps and areas needing further investigation
6. Providing citations and references for all findings

When conducting research:
- Use web search and browsing tools effectively
- Read and analyze relevant documents thoroughly
- Cross-reference information from multiple sources
- Distinguish between facts, opinions, and speculation
- Document sources and provide proper attribution
- Identify the most authoritative and recent sources
- Highlight contradictory information if found

Your research should be:
- Comprehensive: Cover all relevant aspects of the topic
- Accurate: Verify information from reliable sources
- Well-organized: Present findings in a logical structure
- Cited: Include proper references and sources
- Objective: Present balanced viewpoints when applicable
"""
    
    def __init__(
        self,
        name: str = "researcher",
        model: str = "qwen2.5:7b",
        console: Optional[Console] = None,
        ollama_client: Optional[ollama.AsyncClient] = None,
        parent_exit_stack: Optional[AsyncExitStack] = None,
        message_broker: Optional[MessageBroker] = None,
        custom_prompt: Optional[str] = None
    ):
        """Initialize Researcher agent.
        
        Args:
            name: Name for this agent instance
            model: Ollama model to use
            console: Rich console for output
            ollama_client: Ollama client instance
            parent_exit_stack: Parent's exit stack
            message_broker: Message broker for communication
            custom_prompt: Custom system prompt (uses default if None)
        """
        description = "Specialized agent for research and information gathering"
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
        
        # Research-specific state
        self.research_notes: List[Dict[str, Any]] = []
        self.sources: List[str] = []
        
    async def research_topic(
        self,
        topic: str,
        depth: str = "medium",
        max_sources: int = 5
    ) -> str:
        """Research a specific topic.
        
        Args:
            topic: Topic to research
            depth: Depth of research ("quick", "medium", "deep")
            max_sources: Maximum number of sources to consult
            
        Returns:
            str: Research findings
        """
        task = f"""Research the following topic in {depth} depth:

Topic: {topic}

Please:
1. Search for relevant information using available tools
2. Analyze and synthesize information from up to {max_sources} sources
3. Organize findings in a clear structure with sections
4. Provide citations for all claims
5. Highlight key findings and important points
6. Note any contradictions or uncertainties

Present your findings in a well-structured research report.
"""
        
        result = await self.execute_task(task)
        
        # Remember this research
        await self.remember(
            f"Researched topic: {topic}. Key findings: {result[:200]}...",
            importance=3,
            tags=["research", topic]
        )
        
        return result
    
    async def verify_fact(self, claim: str) -> str:
        """Verify a factual claim.
        
        Args:
            claim: Claim to verify
            
        Returns:
            str: Verification result
        """
        task = f"""Verify the following claim:

Claim: {claim}

Please:
1. Search for evidence supporting or refuting this claim
2. Consult authoritative sources
3. Check for recent updates or changes
4. Present the verification result with evidence
5. Rate confidence level (High/Medium/Low)
6. Provide sources for verification

Format your response clearly indicating whether the claim is:
- Verified (True)
- Refuted (False)
- Partially True
- Cannot be verified
"""
        
        result = await self.execute_task(task)
        
        await self.remember(
            f"Fact check: {claim}. Result: {result[:100]}...",
            importance=2,
            tags=["fact-check", "verification"]
        )
        
        return result
    
    async def summarize_document(self, document_path: str) -> str:
        """Summarize a document.
        
        Args:
            document_path: Path to document
            
        Returns:
            str: Document summary
        """
        task = f"""Read and summarize the document at: {document_path}

Please provide:
1. Executive summary (2-3 sentences)
2. Main points and key findings
3. Important details or data
4. Conclusions or recommendations (if applicable)
5. Any questions or areas needing clarification

Keep the summary concise but comprehensive.
"""
        
        return await self.execute_task(task)
    
    def add_research_note(
        self,
        topic: str,
        content: str,
        source: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> None:
        """Add a research note.
        
        Args:
            topic: Research topic
            content: Note content
            source: Optional source citation
            tags: Optional tags
        """
        note = {
            "topic": topic,
            "content": content,
            "source": source,
            "tags": tags or [],
            "timestamp": self.chat_history[-1] if self.chat_history else None
        }
        self.research_notes.append(note)
        
        if source and source not in self.sources:
            self.sources.append(source)
    
    def get_research_summary(self) -> Dict[str, Any]:
        """Get summary of research conducted.
        
        Returns:
            Dict with research statistics
        """
        return {
            "total_notes": len(self.research_notes),
            "sources_consulted": len(self.sources),
            "topics_researched": len(set(note["topic"] for note in self.research_notes)),
            "recent_notes": self.research_notes[-5:] if self.research_notes else []
        }
