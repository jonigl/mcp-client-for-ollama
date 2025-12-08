"""Tool RAG (Retrieval-Augmented Generation) for intelligent tool filtering.

This module implements semantic search over tool schemas to efficiently select
relevant tools for a given query, enabling scalable tool management with large
tool sets.
"""

import json
import pickle
from pathlib import Path
from typing import List, Optional, Tuple

import torch
from mcp import Tool
from sentence_transformers import SentenceTransformer, util


class ToolRAG:
    """Manages semantic search over tool schemas for intelligent tool filtering.
    
    Uses sentence transformers to embed tool descriptions and perform vector
    search to find the most relevant tools for a given query.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Optional[Path] = None,
    ):
        """Initialize the ToolRAG system.

        Args:
            model_name: Name of the sentence-transformers model to use.
                Default is 'all-MiniLM-L6-v2' (80MB, fast, good quality).
            cache_dir: Directory to cache embeddings. If None, uses
                ~/.cache/ollmcp/tool_embeddings/
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        self.cache_dir = cache_dir or Path.home() / ".cache" / "ollmcp" / "tool_embeddings"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Storage for tools and their embeddings
        self.tools: List[Tool] = []
        self.tool_texts: List[str] = []
        self.embeddings: Optional[torch.Tensor] = None
        self._cache_hash: Optional[str] = None

    def _load_model(self) -> None:
        """Lazy load the sentence transformer model."""
        if self.model is None:
            self.model = SentenceTransformer(self.model_name)

    def _create_tool_text(self, tool: Tool) -> str:
        """Create searchable text representation of a tool.

        Args:
            tool: Tool object to convert to text

        Returns:
            String representation combining name, description, and key parameters
        """
        parts = [
            f"Tool: {tool.name}",
            f"Description: {tool.description or 'No description'}",
        ]
        
        # Add parameter information if available
        if hasattr(tool, 'inputSchema') and tool.inputSchema:
            schema = tool.inputSchema
            if isinstance(schema, dict) and 'properties' in schema:
                param_names = list(schema['properties'].keys())
                if param_names:
                    parts.append(f"Parameters: {', '.join(param_names)}")
        
        return " | ".join(parts)

    def _compute_cache_hash(self, tools: List[Tool]) -> str:
        """Compute a hash of the tool set for cache validation.

        Args:
            tools: List of tools to hash

        Returns:
            Hash string representing the tool set
        """
        # Create a stable representation of tools
        tool_repr = json.dumps(
            [(t.name, t.description) for t in tools],
            sort_keys=True
        )
        return str(hash(tool_repr))

    def _get_cache_path(self, cache_hash: str) -> Path:
        """Get the cache file path for a given hash.

        Args:
            cache_hash: Hash of the tool set

        Returns:
            Path to the cache file
        """
        return self.cache_dir / f"{cache_hash}_{self.model_name.replace('/', '_')}.pkl"

    def embed_tools(self, tools: List[Tool], use_cache: bool = True) -> None:
        """Embed all tools for semantic search.

        Args:
            tools: List of Tool objects to embed
            use_cache: Whether to use cached embeddings if available
        """
        self.tools = tools
        self.tool_texts = [self._create_tool_text(tool) for tool in tools]
        self._cache_hash = self._compute_cache_hash(tools)
        
        cache_path = self._get_cache_path(self._cache_hash)
        
        # Try to load from cache
        if use_cache and cache_path.exists():
            try:
                with open(cache_path, 'rb') as f:
                    cached_data = pickle.load(f)
                    self.embeddings = cached_data['embeddings']
                    return
            except Exception:
                # Cache load failed, will recompute
                pass
        
        # Compute embeddings
        self._load_model()
        self.embeddings = self.model.encode(
            self.tool_texts,
            convert_to_tensor=True,
            show_progress_bar=False
        )
        
        # Save to cache
        if use_cache:
            try:
                with open(cache_path, 'wb') as f:
                    pickle.dump({
                        'embeddings': self.embeddings,
                        'model_name': self.model_name,
                    }, f)
            except Exception:
                # Cache save failed, not critical
                pass

    def retrieve_relevant_tools(
        self,
        query: str,
        top_k: int = 15
    ) -> List[Tool]:
        """Retrieve the most relevant tools for a given query.

        Args:
            query: User query to find relevant tools for
            top_k: Number of tools to retrieve

        Returns:
            List of the top_k most relevant Tool objects

        Raises:
            ValueError: If tools haven't been embedded yet
        """
        if self.embeddings is None or not self.tools:
            raise ValueError("Tools must be embedded before retrieval. Call embed_tools() first.")
        
        self._load_model()
        
        # Encode the query
        query_embedding = self.model.encode(
            query,
            convert_to_tensor=True,
            show_progress_bar=False
        )
        
        # Compute similarity scores
        similarity_scores = util.cos_sim(query_embedding, self.embeddings)[0]
        
        # Get top-k indices
        top_k = min(top_k, len(self.tools))
        scores, indices = torch.topk(similarity_scores, k=top_k)
        
        # Return the corresponding tools
        return [self.tools[idx] for idx in indices]

    def clear_cache(self) -> None:
        """Clear all cached embeddings."""
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_file.unlink()
