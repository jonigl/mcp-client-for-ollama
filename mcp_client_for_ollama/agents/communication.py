"""Agent communication protocol for inter-agent messaging and collaboration."""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid


class MessageType(Enum):
    """Types of inter-agent messages."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    INFORMATION_SHARE = "information_share"
    COLLABORATION_REQUEST = "collaboration_request"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"


@dataclass
class AgentMessage:
    """Message passed between agents."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipient: str = ""
    message_type: MessageType = MessageType.INFORMATION_SHARE
    content: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    thread_id: Optional[str] = None
    priority: int = 1  # 1-5, higher is more urgent
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "id": self.id,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "thread_id": self.thread_id,
            "priority": self.priority
        }


class MessageBroker:
    """Central message broker for agent communication."""
    
    def __init__(self):
        """Initialize the message broker."""
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.subscribers: Dict[str, List[Callable]] = {}
        self.message_history: List[AgentMessage] = []
        self.max_history = 1000
        
    def register_agent(self, agent_name: str) -> None:
        """Register an agent with the broker.
        
        Args:
            agent_name: Name of the agent to register
        """
        if agent_name not in self.message_queues:
            self.message_queues[agent_name] = asyncio.Queue()
            self.subscribers[agent_name] = []
    
    def unregister_agent(self, agent_name: str) -> None:
        """Unregister an agent from the broker.
        
        Args:
            agent_name: Name of the agent to unregister
        """
        if agent_name in self.message_queues:
            del self.message_queues[agent_name]
            del self.subscribers[agent_name]
    
    async def send_message(self, message: AgentMessage) -> bool:
        """Send a message to an agent.
        
        Args:
            message: Message to send
            
        Returns:
            bool: True if message was queued successfully
        """
        if message.recipient not in self.message_queues:
            return False
        
        await self.message_queues[message.recipient].put(message)
        
        # Store in history
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history.pop(0)
        
        # Notify subscribers
        for callback in self.subscribers.get(message.recipient, []):
            try:
                await callback(message)
            except Exception:
                pass  # Don't let subscriber errors break message delivery
        
        return True
    
    async def receive_message(self, agent_name: str, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """Receive a message for an agent.
        
        Args:
            agent_name: Name of the agent receiving the message
            timeout: Optional timeout in seconds
            
        Returns:
            AgentMessage or None if timeout
        """
        if agent_name not in self.message_queues:
            return None
        
        try:
            if timeout:
                message = await asyncio.wait_for(
                    self.message_queues[agent_name].get(),
                    timeout=timeout
                )
            else:
                message = await self.message_queues[agent_name].get()
            return message
        except asyncio.TimeoutError:
            return None
    
    def subscribe(self, agent_name: str, callback: Callable) -> None:
        """Subscribe to messages for an agent.
        
        Args:
            agent_name: Name of the agent
            callback: Async function to call when message received
        """
        if agent_name not in self.subscribers:
            self.subscribers[agent_name] = []
        self.subscribers[agent_name].append(callback)
    
    def get_pending_messages(self, agent_name: str) -> int:
        """Get count of pending messages for an agent.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            int: Number of pending messages
        """
        if agent_name not in self.message_queues:
            return 0
        return self.message_queues[agent_name].qsize()
    
    def get_conversation_history(self, agent1: str, agent2: str, limit: int = 50) -> List[AgentMessage]:
        """Get conversation history between two agents.
        
        Args:
            agent1: First agent name
            agent2: Second agent name
            limit: Maximum number of messages to return
            
        Returns:
            List of messages between the agents
        """
        messages = [
            msg for msg in self.message_history
            if (msg.sender == agent1 and msg.recipient == agent2) or
               (msg.sender == agent2 and msg.recipient == agent1)
        ]
        return messages[-limit:]
    
    def get_thread_messages(self, thread_id: str) -> List[AgentMessage]:
        """Get all messages in a conversation thread.
        
        Args:
            thread_id: ID of the thread
            
        Returns:
            List of messages in the thread
        """
        return [msg for msg in self.message_history if msg.thread_id == thread_id]
