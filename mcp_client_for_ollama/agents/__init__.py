"""Agents module for MCP Client for Ollama.

This module provides specialized subagent functionality for complex workflows
like Web3 security auditing, code generation, testing, documentation, and more.

Features:
- Multiple specialized agent types (Researcher, Coder, Writer, Tester, Reviewer, Web3 Auditor, FileSystem, RAG)
- Agent-to-agent communication and collaboration
- Persistent agent memory
- Multi-agent orchestration
- Autonomous agent operation
- Workflow execution
- File system operations (read, write, edit, delete)
- RAG capabilities for knowledge management
"""

from .base import SubAgent
from .manager import AgentManager
from .web3_audit import Web3AuditAgent
from .researcher import ResearcherAgent
from .coder import CoderAgent
from .writer import WriterAgent
from .tester import TesterAgent
from .reviewer import ReviewerAgent
from .filesystem import FileSystemAgent
from .rag import RAGAgent
from .communication import MessageBroker, AgentMessage, MessageType
from .memory import AgentMemory, MemoryEntry
from .orchestrator import AgentOrchestrator, Task, TaskStatus

__all__ = [
    "SubAgent",
    "AgentManager",
    "Web3AuditAgent",
    "ResearcherAgent",
    "CoderAgent",
    "WriterAgent",
    "TesterAgent",
    "ReviewerAgent",
    "FileSystemAgent",
    "RAGAgent",
    "MessageBroker",
    "AgentMessage",
    "MessageType",
    "AgentMemory",
    "MemoryEntry",
    "AgentOrchestrator",
    "Task",
    "TaskStatus",
]
