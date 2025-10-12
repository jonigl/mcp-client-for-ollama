"""Persistent memory and state management for agents."""

import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import asyncio


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: str
    timestamp: datetime
    importance: int = 1  # 1-5, higher is more important
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "importance": self.importance,
            "tags": self.tags,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            importance=data.get("importance", 1),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )


class AgentMemory:
    """Memory system for persistent agent state."""
    
    def __init__(self, agent_name: str, max_size: int = 1000):
        """Initialize agent memory.
        
        Args:
            agent_name: Name of the agent
            max_size: Maximum number of memories to keep
        """
        self.agent_name = agent_name
        self.max_size = max_size
        self.short_term: List[MemoryEntry] = []
        self.long_term: List[MemoryEntry] = []
        self.working_memory: Dict[str, Any] = {}
        self.lock = asyncio.Lock()
        
    async def add_memory(
        self,
        content: str,
        importance: int = 1,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a memory entry.
        
        Args:
            content: Memory content
            importance: Importance level (1-5)
            tags: Optional tags for categorization
            metadata: Additional metadata
            
        Returns:
            str: ID of the memory entry
        """
        async with self.lock:
            import uuid
            memory_id = str(uuid.uuid4())
            
            entry = MemoryEntry(
                id=memory_id,
                content=content,
                timestamp=datetime.now(),
                importance=importance,
                tags=tags or [],
                metadata=metadata or {}
            )
            
            self.short_term.append(entry)
            
            # Consolidate to long-term if needed
            if len(self.short_term) > 50:
                await self._consolidate_memories()
            
            return memory_id
    
    async def _consolidate_memories(self) -> None:
        """Move important short-term memories to long-term."""
        # Move high-importance memories to long-term
        important_memories = [m for m in self.short_term if m.importance >= 3]
        self.long_term.extend(important_memories)
        
        # Keep only recent short-term memories
        self.short_term = self.short_term[-20:]
        
        # Trim long-term if needed
        if len(self.long_term) > self.max_size:
            # Keep most important and recent
            self.long_term.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
            self.long_term = self.long_term[:self.max_size]
    
    async def search_memories(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_importance: int = 1,
        limit: int = 10
    ) -> List[MemoryEntry]:
        """Search memories.
        
        Args:
            query: Optional text to search for
            tags: Optional tags to filter by
            min_importance: Minimum importance level
            limit: Maximum number of results
            
        Returns:
            List of matching memory entries
        """
        async with self.lock:
            all_memories = self.short_term + self.long_term
            
            # Filter by importance
            results = [m for m in all_memories if m.importance >= min_importance]
            
            # Filter by tags
            if tags:
                results = [
                    m for m in results
                    if any(tag in m.tags for tag in tags)
                ]
            
            # Search content
            if query:
                query_lower = query.lower()
                results = [
                    m for m in results
                    if query_lower in m.content.lower()
                ]
            
            # Sort by relevance (importance and recency)
            results.sort(key=lambda m: (m.importance, m.timestamp), reverse=True)
            
            return results[:limit]
    
    async def get_recent_memories(self, limit: int = 10) -> List[MemoryEntry]:
        """Get recent memories.
        
        Args:
            limit: Maximum number of memories
            
        Returns:
            List of recent memory entries
        """
        async with self.lock:
            all_memories = self.short_term + self.long_term
            all_memories.sort(key=lambda m: m.timestamp, reverse=True)
            return all_memories[:limit]
    
    async def update_working_memory(self, key: str, value: Any) -> None:
        """Update working memory.
        
        Args:
            key: Memory key
            value: Memory value
        """
        async with self.lock:
            self.working_memory[key] = value
    
    async def get_working_memory(self, key: str) -> Optional[Any]:
        """Get working memory value.
        
        Args:
            key: Memory key
            
        Returns:
            Memory value or None
        """
        async with self.lock:
            return self.working_memory.get(key)
    
    async def clear_working_memory(self) -> None:
        """Clear working memory."""
        async with self.lock:
            self.working_memory.clear()
    
    async def save_to_file(self, filepath: Path) -> None:
        """Save memory to file.
        
        Args:
            filepath: Path to save file
        """
        async with self.lock:
            data = {
                "agent_name": self.agent_name,
                "short_term": [m.to_dict() for m in self.short_term],
                "long_term": [m.to_dict() for m in self.long_term],
                "working_memory": self.working_memory,
                "timestamp": datetime.now().isoformat()
            }
            
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
    
    async def load_from_file(self, filepath: Path) -> bool:
        """Load memory from file.
        
        Args:
            filepath: Path to load file
            
        Returns:
            bool: True if loaded successfully
        """
        if not filepath.exists():
            return False
        
        async with self.lock:
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                
                self.short_term = [
                    MemoryEntry.from_dict(m) for m in data.get("short_term", [])
                ]
                self.long_term = [
                    MemoryEntry.from_dict(m) for m in data.get("long_term", [])
                ]
                self.working_memory = data.get("working_memory", {})
                
                return True
            except Exception:
                return False
    
    def get_context_summary(self, max_items: int = 5) -> str:
        """Get a summary of current context.
        
        Args:
            max_items: Maximum number of items to include
            
        Returns:
            str: Context summary
        """
        recent = sorted(
            self.short_term + self.long_term,
            key=lambda m: (m.importance, m.timestamp),
            reverse=True
        )[:max_items]
        
        summary_parts = []
        for memory in recent:
            summary_parts.append(f"- {memory.content}")
        
        return "\n".join(summary_parts) if summary_parts else "No context available"
