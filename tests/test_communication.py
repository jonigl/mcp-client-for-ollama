"""Tests for multi-agent communication and collaboration."""

import pytest
import asyncio
from unittest.mock import Mock

from mcp_client_for_ollama.agents.communication import (
    MessageBroker, AgentMessage, MessageType
)


class TestMessageBroker:
    """Tests for MessageBroker."""
    
    def test_register_agent(self):
        """Test agent registration."""
        broker = MessageBroker()
        broker.register_agent("agent1")
        
        assert "agent1" in broker.message_queues
        assert "agent1" in broker.subscribers
    
    def test_unregister_agent(self):
        """Test agent unregistration."""
        broker = MessageBroker()
        broker.register_agent("agent1")
        broker.unregister_agent("agent1")
        
        assert "agent1" not in broker.message_queues
        assert "agent1" not in broker.subscribers
    
    @pytest.mark.asyncio
    async def test_send_and_receive_message(self):
        """Test sending and receiving messages."""
        broker = MessageBroker()
        broker.register_agent("agent1")
        broker.register_agent("agent2")
        
        message = AgentMessage(
            sender="agent1",
            recipient="agent2",
            message_type=MessageType.INFORMATION_SHARE,
            content={"data": "test"}
        )
        
        sent = await broker.send_message(message)
        assert sent is True
        
        received = await broker.receive_message("agent2")
        assert received is not None
        assert received.sender == "agent1"
        assert received.content["data"] == "test"
    
    @pytest.mark.asyncio
    async def test_receive_timeout(self):
        """Test message receive timeout."""
        broker = MessageBroker()
        broker.register_agent("agent1")
        
        received = await broker.receive_message("agent1", timeout=0.1)
        assert received is None
    
    def test_get_pending_messages(self):
        """Test getting pending message count."""
        broker = MessageBroker()
        broker.register_agent("agent1")
        
        assert broker.get_pending_messages("agent1") == 0
    
    def test_get_conversation_history(self):
        """Test getting conversation history."""
        broker = MessageBroker()
        broker.register_agent("agent1")
        broker.register_agent("agent2")
        
        # Send some messages
        msg1 = AgentMessage(
            sender="agent1",
            recipient="agent2",
            message_type=MessageType.TASK_REQUEST
        )
        msg2 = AgentMessage(
            sender="agent2",
            recipient="agent1",
            message_type=MessageType.TASK_RESPONSE
        )
        
        asyncio.run(broker.send_message(msg1))
        asyncio.run(broker.send_message(msg2))
        
        history = broker.get_conversation_history("agent1", "agent2")
        assert len(history) == 2


class TestAgentMessage:
    """Tests for AgentMessage."""
    
    def test_message_creation(self):
        """Test creating a message."""
        message = AgentMessage(
            sender="agent1",
            recipient="agent2",
            message_type=MessageType.TASK_REQUEST,
            content={"task": "test"}
        )
        
        assert message.sender == "agent1"
        assert message.recipient == "agent2"
        assert message.message_type == MessageType.TASK_REQUEST
        assert message.content["task"] == "test"
        assert message.id is not None
    
    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        message = AgentMessage(
            sender="agent1",
            recipient="agent2",
            message_type=MessageType.INFORMATION_SHARE,
            content={"data": "test"}
        )
        
        msg_dict = message.to_dict()
        
        assert msg_dict["sender"] == "agent1"
        assert msg_dict["recipient"] == "agent2"
        assert msg_dict["message_type"] == "information_share"
        assert msg_dict["content"]["data"] == "test"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
