"""Tests for agent memory system."""

import pytest
import asyncio
from pathlib import Path
import tempfile

from mcp_client_for_ollama.agents.memory import AgentMemory, MemoryEntry


class TestAgentMemory:
    """Tests for AgentMemory."""
    
    @pytest.mark.asyncio
    async def test_add_memory(self):
        """Test adding a memory."""
        memory = AgentMemory("test-agent")
        
        memory_id = await memory.add_memory(
            "Test memory content",
            importance=3,
            tags=["test"]
        )
        
        assert memory_id is not None
        assert len(memory.short_term) == 1
        assert memory.short_term[0].content == "Test memory content"
    
    @pytest.mark.asyncio
    async def test_search_memories(self):
        """Test searching memories."""
        memory = AgentMemory("test-agent")
        
        await memory.add_memory("Python code", importance=2, tags=["coding"])
        await memory.add_memory("JavaScript code", importance=3, tags=["coding"])
        await memory.add_memory("Documentation", importance=1, tags=["docs"])
        
        # Search by tag
        results = await memory.search_memories(tags=["coding"])
        assert len(results) == 2
        
        # Search by query
        results = await memory.search_memories(query="Python")
        assert len(results) == 1
        assert "Python" in results[0].content
        
        # Search by importance
        results = await memory.search_memories(min_importance=3)
        assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_get_recent_memories(self):
        """Test getting recent memories."""
        memory = AgentMemory("test-agent")
        
        await memory.add_memory("Memory 1")
        await memory.add_memory("Memory 2")
        await memory.add_memory("Memory 3")
        
        recent = await memory.get_recent_memories(limit=2)
        assert len(recent) == 2
        assert recent[0].content == "Memory 3"  # Most recent first
    
    @pytest.mark.asyncio
    async def test_working_memory(self):
        """Test working memory operations."""
        memory = AgentMemory("test-agent")
        
        await memory.update_working_memory("key1", "value1")
        value = await memory.get_working_memory("key1")
        assert value == "value1"
        
        await memory.clear_working_memory()
        value = await memory.get_working_memory("key1")
        assert value is None
    
    @pytest.mark.asyncio
    async def test_save_and_load(self):
        """Test saving and loading memory."""
        memory = AgentMemory("test-agent")
        
        await memory.add_memory("Test memory", importance=2, tags=["test"])
        await memory.update_working_memory("key", "value")
        
        # Save to temporary file
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "memory.json"
            await memory.save_to_file(filepath)
            
            # Load into new memory instance
            new_memory = AgentMemory("test-agent")
            loaded = await new_memory.load_from_file(filepath)
            
            assert loaded is True
            assert len(new_memory.short_term) == 1
            assert new_memory.short_term[0].content == "Test memory"
            assert await new_memory.get_working_memory("key") == "value"
    
    def test_context_summary(self):
        """Test getting context summary."""
        memory = AgentMemory("test-agent")
        
        asyncio.run(memory.add_memory("Important memory", importance=5))
        asyncio.run(memory.add_memory("Less important", importance=1))
        
        summary = memory.get_context_summary(max_items=2)
        assert "Important memory" in summary


class TestMemoryEntry:
    """Tests for MemoryEntry."""
    
    def test_memory_entry_creation(self):
        """Test creating a memory entry."""
        from datetime import datetime
        
        entry = MemoryEntry(
            id="test-id",
            content="Test content",
            timestamp=datetime.now(),
            importance=3,
            tags=["test"]
        )
        
        assert entry.id == "test-id"
        assert entry.content == "Test content"
        assert entry.importance == 3
        assert "test" in entry.tags
    
    def test_memory_entry_to_dict(self):
        """Test converting memory entry to dictionary."""
        from datetime import datetime
        
        entry = MemoryEntry(
            id="test-id",
            content="Test content",
            timestamp=datetime.now(),
            importance=3,
            tags=["test"]
        )
        
        entry_dict = entry.to_dict()
        
        assert entry_dict["id"] == "test-id"
        assert entry_dict["content"] == "Test content"
        assert entry_dict["importance"] == 3
        assert "test" in entry_dict["tags"]
    
    def test_memory_entry_from_dict(self):
        """Test creating memory entry from dictionary."""
        from datetime import datetime
        
        data = {
            "id": "test-id",
            "content": "Test content",
            "timestamp": datetime.now().isoformat(),
            "importance": 3,
            "tags": ["test"]
        }
        
        entry = MemoryEntry.from_dict(data)
        
        assert entry.id == "test-id"
        assert entry.content == "Test content"
        assert entry.importance == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
