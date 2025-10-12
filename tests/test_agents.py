"""Tests for specialized agents functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from contextlib import AsyncExitStack

from mcp_client_for_ollama.agents.base import SubAgent
from mcp_client_for_ollama.agents.web3_audit import Web3AuditAgent
from mcp_client_for_ollama.agents.researcher import ResearcherAgent
from mcp_client_for_ollama.agents.coder import CoderAgent
from mcp_client_for_ollama.agents.writer import WriterAgent
from mcp_client_for_ollama.agents.tester import TesterAgent
from mcp_client_for_ollama.agents.reviewer import ReviewerAgent
from mcp_client_for_ollama.agents.manager import AgentManager
from mcp_client_for_ollama.agents.communication import MessageBroker, MessageType


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
        assert "security auditing" in agent.description.lower()
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
        assert manager.message_broker is not None
        assert manager.orchestrator is not None
    
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
    
    def test_create_researcher_agent(self):
        """Test creating a researcher agent."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        agent = manager.create_agent(
            agent_type="researcher",
            name="test-researcher",
            model="qwen2.5:7b"
        )
        
        assert agent is not None
        assert isinstance(agent, ResearcherAgent)
        assert agent.name == "test-researcher"
    
    def test_create_coder_agent(self):
        """Test creating a coder agent."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        agent = manager.create_agent(
            agent_type="coder",
            name="test-coder",
            model="qwen2.5-coder:7b"
        )
        
        assert agent is not None
        assert isinstance(agent, CoderAgent)
        assert agent.name == "test-coder"
    
    def test_create_writer_agent(self):
        """Test creating a writer agent."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        agent = manager.create_agent(
            agent_type="writer",
            name="test-writer",
            model="qwen2.5:7b"
        )
        
        assert agent is not None
        assert isinstance(agent, WriterAgent)
        assert agent.name == "test-writer"
    
    def test_create_tester_agent(self):
        """Test creating a tester agent."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        agent = manager.create_agent(
            agent_type="tester",
            name="test-tester",
            model="qwen2.5:7b"
        )
        
        assert agent is not None
        assert isinstance(agent, TesterAgent)
        assert agent.name == "test-tester"
    
    def test_create_reviewer_agent(self):
        """Test creating a reviewer agent."""
        console = Mock()
        ollama_client = Mock()
        exit_stack = AsyncExitStack()
        manager = AgentManager(console, ollama_client, exit_stack)
        
        agent = manager.create_agent(
            agent_type="reviewer",
            name="test-reviewer",
            model="qwen2.5:7b"
        )
        
        assert agent is not None
        assert isinstance(agent, ReviewerAgent)
        assert agent.name == "test-reviewer"
    
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
        manager.create_agent("researcher", "agent2", "qwen2.5:7b")
        
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


class TestSubAgentCollaboration:
    """Tests for agent collaboration features."""
    
    @pytest.mark.asyncio
    async def test_agent_messaging(self):
        """Test agent-to-agent messaging."""
        broker = MessageBroker()
        
        agent1 = SubAgent(
            name="agent1",
            description="Test agent 1",
            model="qwen2.5:7b",
            system_prompt="Test",
            message_broker=broker
        )
        
        agent2 = SubAgent(
            name="agent2",
            description="Test agent 2",
            model="qwen2.5:7b",
            system_prompt="Test",
            message_broker=broker
        )
        
        # Send message from agent1 to agent2
        sent = await agent1.send_message(
            recipient="agent2",
            message_type=MessageType.INFORMATION_SHARE,
            content={"data": "test"}
        )
        
        assert sent is True
        
        # Receive message at agent2
        message = await agent2.receive_message(timeout=1.0)
        assert message is not None
        assert message.sender == "agent1"
    
    @pytest.mark.asyncio
    async def test_agent_delegation(self):
        """Test task delegation between agents."""
        broker = MessageBroker()
        
        agent1 = SubAgent(
            name="agent1",
            description="Test agent 1",
            model="qwen2.5:7b",
            system_prompt="Test",
            message_broker=broker
        )
        
        agent2 = SubAgent(
            name="agent2",
            description="Test agent 2",
            model="qwen2.5:7b",
            system_prompt="Test",
            message_broker=broker
        )
        
        # Delegate task
        delegated = await agent1.delegate_task(
            recipient="agent2",
            task="Test task"
        )
        
        assert delegated is True
        
        # Check message received
        message = await agent2.receive_message(timeout=1.0)
        assert message.message_type == MessageType.TASK_REQUEST
        assert message.content["task"] == "Test task"


class TestSpecializedAgents:
    """Tests for specialized agent types."""
    
    def test_researcher_agent_initialization(self):
        """Test ResearcherAgent initialization."""
        agent = ResearcherAgent()
        
        assert agent.name == "researcher"
        assert "research" in agent.description.lower()
        assert len(agent.research_notes) == 0
    
    def test_coder_agent_initialization(self):
        """Test CoderAgent initialization."""
        agent = CoderAgent()
        
        assert agent.name == "coder"
        assert "code" in agent.description.lower()
        assert len(agent.code_files_created) == 0
    
    def test_writer_agent_initialization(self):
        """Test WriterAgent initialization."""
        agent = WriterAgent()
        
        assert agent.name == "writer"
        assert "documentation" in agent.description.lower()
        assert len(agent.documents_created) == 0
    
    def test_tester_agent_initialization(self):
        """Test TesterAgent initialization."""
        agent = TesterAgent()
        
        assert agent.name == "tester"
        assert "test" in agent.description.lower()
        assert len(agent.test_results) == 0
    
    def test_reviewer_agent_initialization(self):
        """Test ReviewerAgent initialization."""
        agent = ReviewerAgent()
        
        assert agent.name == "reviewer"
        assert "review" in agent.description.lower()
        assert len(agent.reviews_conducted) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
