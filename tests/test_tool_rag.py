"""Unit tests for ToolRAG functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest
import torch

from mcp_client_for_ollama.tools.rag import ToolRAG


@pytest.fixture
def mock_tools():
    """Create mock Tool objects for testing."""
    tools = []
    
    # GitHub-related tools
    tool1 = Mock()
    tool1.name = "github.list_issues"
    tool1.description = "List issues from a GitHub repository"
    tool1.inputSchema = {"properties": {"repo": {}, "state": {}}}
    tools.append(tool1)
    
    tool2 = Mock()
    tool2.name = "github.create_pr"
    tool2.description = "Create a pull request on GitHub"
    tool2.inputSchema = {"properties": {"title": {}, "body": {}, "base": {}}}
    tools.append(tool2)
    
    # Filesystem tools
    tool3 = Mock()
    tool3.name = "filesystem.read_file"
    tool3.description = "Read contents of a file from the filesystem"
    tool3.inputSchema = {"properties": {"path": {}}}
    tools.append(tool3)
    
    tool4 = Mock()
    tool4.name = "filesystem.write_file"
    tool4.description = "Write content to a file on the filesystem"
    tool4.inputSchema = {"properties": {"path": {}, "content": {}}}
    tools.append(tool4)
    
    # AWS tools
    tool5 = Mock()
    tool5.name = "aws.list_buckets"
    tool5.description = "List all S3 buckets in AWS account"
    tool5.inputSchema = {"properties": {}}
    tools.append(tool5)
    
    return tools


@pytest.fixture
def tool_rag():
    """Create a ToolRAG instance with temporary cache directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rag = ToolRAG(cache_dir=Path(tmpdir))
        yield rag


def test_tool_rag_initialization(tool_rag):
    """Test ToolRAG initializes correctly."""
    assert tool_rag.model is None  # Lazy loading
    assert tool_rag.embeddings is None
    assert len(tool_rag.tools) == 0
    assert tool_rag.cache_dir.exists()


def test_create_tool_text(tool_rag, mock_tools):
    """Test tool text representation creation."""
    tool = mock_tools[0]
    text = tool_rag._create_tool_text(tool)
    
    assert "github.list_issues" in text
    assert "List issues from a GitHub repository" in text
    assert "repo" in text
    assert "state" in text


def test_embed_tools(tool_rag, mock_tools):
    """Test embedding tools creates embeddings."""
    tool_rag.embed_tools(mock_tools, use_cache=False)
    
    assert tool_rag.embeddings is not None
    assert isinstance(tool_rag.embeddings, torch.Tensor)
    assert tool_rag.embeddings.shape[0] == len(mock_tools)
    assert len(tool_rag.tools) == len(mock_tools)
    assert len(tool_rag.tool_texts) == len(mock_tools)


def test_embed_tools_with_cache(tool_rag, mock_tools):
    """Test embedding caching works correctly."""
    # First embedding - creates cache
    tool_rag.embed_tools(mock_tools, use_cache=True)
    first_embeddings = tool_rag.embeddings.clone()
    
    # Create new instance with same cache dir
    rag2 = ToolRAG(cache_dir=tool_rag.cache_dir)
    rag2.embed_tools(mock_tools, use_cache=True)
    
    # Should load from cache
    assert torch.allclose(first_embeddings, rag2.embeddings)


def test_retrieve_relevant_tools_github_query(tool_rag, mock_tools):
    """Test retrieving tools for GitHub-related query."""
    tool_rag.embed_tools(mock_tools, use_cache=False)
    
    results = tool_rag.retrieve_relevant_tools("show me GitHub issues", threshold=0.3, max_tools=2)
    
    assert len(results) <= 2
    # GitHub tools should be top results
    assert any("github" in tool.name for tool in results)


def test_retrieve_relevant_tools_filesystem_query(tool_rag, mock_tools):
    """Test retrieving tools for filesystem-related query."""
    tool_rag.embed_tools(mock_tools, use_cache=False)
    
    results = tool_rag.retrieve_relevant_tools("read a file from disk", threshold=0.3, max_tools=2)
    
    assert len(results) <= 2
    # Filesystem tools should be top results
    assert any("filesystem" in tool.name for tool in results)


def test_retrieve_relevant_tools_aws_query(tool_rag, mock_tools):
    """Test retrieving tools for AWS-related query."""
    tool_rag.embed_tools(mock_tools, use_cache=False)
    
    results = tool_rag.retrieve_relevant_tools("list my S3 buckets", threshold=0.3, max_tools=2)
    
    assert len(results) <= 2
    # AWS tool should be in top results
    assert any("aws" in tool.name for tool in results)


def test_retrieve_before_embed_raises_error(tool_rag):
    """Test that retrieving before embedding raises ValueError."""
    with pytest.raises(ValueError, match="Tools must be embedded"):
        tool_rag.retrieve_relevant_tools("test query")


def test_retrieve_respects_max_tools(tool_rag, mock_tools):
    """Test that max_tools parameter is respected."""
    tool_rag.embed_tools(mock_tools, use_cache=False)
    
    results = tool_rag.retrieve_relevant_tools("test query", threshold=0.0, max_tools=3)
    assert len(results) <= 3
    
    results = tool_rag.retrieve_relevant_tools("test query", threshold=0.0, max_tools=10)
    assert len(results) <= len(mock_tools)  # Can't exceed available tools


def test_clear_cache(tool_rag, mock_tools):
    """Test cache clearing functionality."""
    tool_rag.embed_tools(mock_tools, use_cache=True)
    
    # Verify cache file exists
    cache_files = list(tool_rag.cache_dir.glob("*.pkl"))
    assert len(cache_files) > 0
    
    # Clear cache
    tool_rag.clear_cache()
    
    # Verify cache is empty
    cache_files = list(tool_rag.cache_dir.glob("*.pkl"))
    assert len(cache_files) == 0


def test_compute_cache_hash_consistency(tool_rag, mock_tools):
    """Test that cache hash is consistent for same tools."""
    hash1 = tool_rag._compute_cache_hash(mock_tools)
    hash2 = tool_rag._compute_cache_hash(mock_tools)
    
    assert hash1 == hash2


def test_compute_cache_hash_changes_with_tools(tool_rag, mock_tools):
    """Test that cache hash changes when tools change."""
    hash1 = tool_rag._compute_cache_hash(mock_tools)
    hash2 = tool_rag._compute_cache_hash(mock_tools[:3])
    
    assert hash1 != hash2
