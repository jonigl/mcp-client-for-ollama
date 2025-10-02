"""Agents module for MCP Client for Ollama.

This module provides specialized subagent functionality for complex workflows
like Web3 security auditing.
"""

from .base import SubAgent
from .manager import AgentManager
from .web3_audit import Web3AuditAgent

__all__ = ["SubAgent", "AgentManager", "Web3AuditAgent"]
