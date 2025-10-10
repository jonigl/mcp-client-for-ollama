"""Tests for specialized agents functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from contextlib import AsyncExitStack

from mcp_client_for_ollama.agents.base import SubAgent
from mcp_client_for_ollama.agents.web3_audit import Web3AuditAgent
from mcp_client_for_ollama.agents.manager import AgentManager


class TestSubAgent:
    """Tests for SubAgent base class."""
    
    def test_subagent_initialization(self):
        """Test SubAgent initialization with basic parameters."""
        agent = SubAgent(
            name="test-agent",
            description="Test agent",
            model="qwen2.5:7b",
            system_prompt="Test prompt"
        )
        
        assert agent.name == "test-agent"
        assert agent.description == "Test agent"
        assert agent.model_manager.get_current_model() == "qwen2.5:7b"
        assert agent.model_config_manager.get_system_prompt() == "Test prompt"
    
    def test_subagent_get_info(self):
        """Test getting agent information."""
        agent = SubAgent(
            name="test-agent",
            description="Test agent",
            model="qwen2.5:7b",
            system_prompt="Test prompt"
        )
        
        info = agent.get_info()
        
        assert info["name"] == "test-agent"
        assert info["description"] == "Test agent"
        assert info["model"] == "qwen2.5:7b"
        assert info["system_prompt"] == "Test prompt"
        assert "enabled_tools" in info
        assert "connected_servers" in info
        assert "task_count" in info


class TestWeb3AuditAgent:
    """Tests for Web3AuditAgent."""
    
    def test_web3_audit_agent_initialization(self):
        """Test Web3AuditAgent initialization with defaults."""
        agent = Web3AuditAgent()
        
        assert agent.name == "web3-auditor"
        assert "security auditor" in agent.description.lower()
        assert agent.model_manager.get_current_model() == "qwen2.5:7b"
        assert "security" in agent.model_config_manager.get_system_prompt().lower()
        assert len(agent.audit_findings) == 0
        assert len(agent.contracts_analyzed) == 0
    
    def test_web3_audit_agent_custom_initialization(self):
        """Test Web3AuditAgent initialization with custom parameters."""
        custom_prompt = "Custom security prompt"
        agent = Web3AuditAgent(
            name="custom-auditor",
            model="llama2:7b",
            custom_prompt=custom_prompt
        )
        
        assert agent.name == "custom-auditor"
        assert agent.model_manager.get_current_model() == "llama2:7b"
        assert agent.model_config_manager.get_system_prompt() == custom_prompt
    
    def test_add_finding(self):
        """Test adding audit findings."""
        agent = Web3AuditAgent()
        
        agent.add_finding(
            title="Test Vulnerability",
            severity="High",
            description="Test description",
            location="Contract.sol:42",
            recommendation="Fix it"
        )
        
        assert len(agent.audit_findings) == 1
        assert agent.audit_findings[0]["title"] == "Test Vulnerability"
        assert agent.audit_findings[0]["severity"] == "High"
    
    def test_get_findings_summary(self):
        """Test getting findings summary."""
        agent = Web3AuditAgent()
        
        agent.add_finding(
            title="Critical Issue",
            severity="Critical",
            description="Test",
            location="Test",
            recommendation="Fix"
        )
        agent.add_finding(
            title="High Issue",
            severity="High",
            description="Test",
            location="Test",
            recommendation="Fix"
        )
        agent.add_finding(
            title="High Issue 2",
            severity="High",
            description="Test",
            location="Test",
            recommendation="Fix"
        )
        
        summary = agent.get_findings_summary()
        
        assert summary["Critical"] == 1
        assert summary["High"] == 2
        assert summary["Medium"] == 0


class TestAgentManager:
    """Tests for AgentManager."""
    
    def test_agent_manager_initialization(self):
        """Test AgentManager initialization."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        
        manager = AgentManager(console, ollama_client, exit_stack)
        
        assert manager.console == console
        assert manager.ollama == ollama_client
        assert manager.exit_stack == exit_stack
        assert len(manager.agents) == 0
    
    def test_create_web3_audit_agent(self):
        """Test creating a Web3 audit agent."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        agent = manager.create_agent(
            agent_type="web3_audit",
            name="test-auditor",
            model="qwen2.5:7b"
        )
        
        assert agent is not None
        assert isinstance(agent, Web3AuditAgent)
        assert agent.name == "test-auditor"
        assert "test-auditor" in manager.agents
    
    def test_create_base_agent(self):
        """Test creating a base agent."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        config = {
            "description": "Test agent",
            "system_prompt": "Test prompt"
        }
        
        agent = manager.create_agent(
            agent_type="base",
            name="test-base",
            model="qwen2.5:7b",
            config=config
        )
        
        assert agent is not None
        assert isinstance(agent, SubAgent)
        assert agent.name == "test-base"
        assert "test-base" in manager.agents
    
    def test_get_agent(self):
        """Test getting an agent by name."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        created_agent = manager.create_agent(
            agent_type="web3_audit",
            name="test-auditor",
            model="qwen2.5:7b"
        )
        
        retrieved_agent = manager.get_agent("test-auditor")
        
        assert retrieved_agent is created_agent
    
    def test_list_agents(self):
        """Test listing all agents."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        manager.create_agent("web3_audit", "agent1", "qwen2.5:7b")
        manager.create_agent("web3_audit", "agent2", "qwen2.5:7b")
        
        agents = manager.list_agents()
        
        assert len(agents) == 2
        assert "agent1" in agents
        assert "agent2" in agents
    
    def test_remove_agent(self):
        """Test removing an agent."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        manager.create_agent("web3_audit", "test-auditor", "qwen2.5:7b")
        
        assert "test-auditor" in manager.agents
        
        result = manager.remove_agent("test-auditor")
        
        assert result is True
        assert "test-auditor" not in manager.agents
    
    def test_duplicate_agent_creation(self):
        """Test that creating duplicate agents is prevented."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        agent1 = manager.create_agent("web3_audit", "test-auditor", "qwen2.5:7b")
        agent2 = manager.create_agent("web3_audit", "test-auditor", "qwen2.5:7b")
        
        assert agent1 is not None
        assert agent2 is None
        assert len(manager.agents) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
