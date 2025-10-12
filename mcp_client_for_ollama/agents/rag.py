"""RAG (Retrieval-Augmented Generation) agent for enhanced context and knowledge."""

from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from rich.console import Console
import ollama
from contextlib import AsyncExitStack
import json
import hashlib
from datetime import datetime

from .base import SubAgent
from .communication import MessageBroker
from .memory import AgentMemory


class RAGAgent(SubAgent):
    """Specialized agent for Retrieval-Augmented Generation.
    
    This agent provides:
    - Document ingestion and indexing
    - Semantic search and retrieval
    - Context-aware query answering
    - Knowledge base management
    - Vector-based similarity search (simple implementation)
    """
    
    DEFAULT_SYSTEM_PROMPT = """You are an expert RAG (Retrieval-Augmented Generation) agent.

Your responsibilities include:
1. Ingesting and indexing documents for retrieval
2. Performing semantic search across knowledge bases
3. Providing context-aware answers using retrieved information
4. Managing and organizing knowledge bases
5. Extracting relevant information from documents
6. Synthesizing information from multiple sources

When working with documents:
- Parse and chunk documents appropriately
- Extract key information and concepts
- Create meaningful embeddings for search
- Retrieve most relevant context for queries
- Provide accurate, well-sourced answers
- Cite sources and provide references
- Handle multiple document types

Search capabilities:
- Semantic similarity search
- Keyword-based search
- Hybrid search combining methods
- Filtering by metadata (date, source, type)
- Ranking by relevance

Always provide clear, well-referenced answers with source citations.
"""
    
    def __init__(
        self,
        name: str = "rag",
        model: str = "qwen2.5:7b",
        console: Optional[Console] = None,
        ollama_client: Optional[ollama.AsyncClient] = None,
        parent_exit_stack: Optional[AsyncExitStack] = None,
        message_broker: Optional[MessageBroker] = None,
        custom_prompt: Optional[str] = None
    ):
        """Initialize RAG agent."""
        description = "Specialized agent for Retrieval-Augmented Generation and knowledge management"
        system_prompt = custom_prompt or self.DEFAULT_SYSTEM_PROMPT
        
        super().__init__(
            name=name,
            description=description,
            model=model,
            system_prompt=system_prompt,
            console=console,
            ollama_client=ollama_client,
            parent_exit_stack=parent_exit_stack,
            message_broker=message_broker,
            enable_memory=True
        )
        
        # Document storage
        self.documents: List[Dict[str, Any]] = []
        self.chunks: List[Dict[str, Any]] = []
        
        # Knowledge base metadata
        self.knowledge_bases: Dict[str, List[str]] = {}  # kb_name -> doc_ids
    
    async def ingest_document(
        self,
        content: str,
        doc_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500,
        overlap: int = 50
    ) -> str:
        """Ingest a document into the knowledge base.
        
        Args:
            content: Document content
            doc_id: Optional document ID (auto-generated if None)
            metadata: Optional metadata (title, source, date, etc.)
            chunk_size: Size of text chunks for indexing
            overlap: Overlap between chunks
            
        Returns:
            str: Document ID
        """
        try:
            # Generate document ID if not provided
            if not doc_id:
                doc_id = hashlib.md5(content.encode()).hexdigest()
            
            # Store document
            document = {
                "id": doc_id,
                "content": content,
                "metadata": metadata or {},
                "ingested_at": datetime.now().isoformat(),
                "chunk_count": 0
            }
            
            self.documents.append(document)
            
            # Chunk the document
            chunks = self._chunk_text(content, chunk_size, overlap)
            
            # Store chunks with references to document
            for i, chunk_text in enumerate(chunks):
                chunk = {
                    "id": f"{doc_id}_{i}",
                    "doc_id": doc_id,
                    "text": chunk_text,
                    "position": i,
                    "metadata": metadata or {}
                }
                self.chunks.append(chunk)
            
            document["chunk_count"] = len(chunks)
            
            # Remember this ingestion
            await self.remember(
                f"Ingested document: {doc_id} ({len(chunks)} chunks)",
                importance=3,
                tags=["rag", "ingest", doc_id]
            )
            
            return f"Successfully ingested document {doc_id} ({len(chunks)} chunks)"
            
        except Exception as e:
            return f"Error ingesting document: {str(e)}"
    
    async def ingest_file(
        self,
        file_path: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: int = 500
    ) -> str:
        """Ingest a file into the knowledge base.
        
        Args:
            file_path: Path to file to ingest
            metadata: Optional metadata
            chunk_size: Size of text chunks
            
        Returns:
            str: Success message with document ID
        """
        try:
            path = Path(file_path)
            
            if not path.exists():
                return f"Error: File not found: {file_path}"
            
            # Read file content
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Add file metadata
            file_metadata = metadata or {}
            file_metadata.update({
                "source_file": str(path),
                "filename": path.name,
                "file_type": path.suffix
            })
            
            # Use filename as doc_id base
            doc_id = path.stem
            
            return await self.ingest_document(
                content=content,
                doc_id=doc_id,
                metadata=file_metadata,
                chunk_size=chunk_size
            )
            
        except Exception as e:
            return f"Error ingesting file: {str(e)}"
    
    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for relevant chunks using the query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            List of relevant chunks with scores
        """
        try:
            # Simple keyword-based search with scoring
            results = []
            query_lower = query.lower()
            query_words = set(query_lower.split())
            
            for chunk in self.chunks:
                # Apply metadata filters if specified
                if filter_metadata:
                    skip = False
                    for key, value in filter_metadata.items():
                        if chunk["metadata"].get(key) != value:
                            skip = True
                            break
                    if skip:
                        continue
                
                chunk_text_lower = chunk["text"].lower()
                chunk_words = set(chunk_text_lower.split())
                
                # Calculate relevance score
                # 1. Exact match bonus
                score = 10.0 if query_lower in chunk_text_lower else 0.0
                
                # 2. Word overlap score
                word_overlap = len(query_words & chunk_words)
                score += word_overlap * 2.0
                
                # 3. Word frequency
                for word in query_words:
                    score += chunk_text_lower.count(word) * 0.5
                
                if score > 0:
                    results.append({
                        "chunk": chunk,
                        "score": score,
                        "doc_id": chunk["doc_id"]
                    })
            
            # Sort by score and return top_k
            results.sort(key=lambda x: x["score"], reverse=True)
            
            return results[:top_k]
            
        except Exception as e:
            self.console.print(f"[red]Error searching: {str(e)}[/red]")
            return []
    
    async def query_with_context(
        self,
        query: str,
        top_k: int = 3,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Answer a query using retrieved context.
        
        Args:
            query: Question or query
            top_k: Number of context chunks to retrieve
            filter_metadata: Optional metadata filters
            
        Returns:
            str: Answer with context
        """
        # Retrieve relevant chunks
        results = await self.search(query, top_k, filter_metadata)
        
        if not results:
            return "No relevant context found for this query."
        
        # Build context from retrieved chunks
        context_parts = []
        sources = []
        
        for i, result in enumerate(results, 1):
            chunk = result["chunk"]
            context_parts.append(f"[Source {i}]\n{chunk['text']}")
            
            # Track sources
            metadata = chunk["metadata"]
            source_info = metadata.get("source_file", metadata.get("title", f"Document {chunk['doc_id']}"))
            sources.append(f"[{i}] {source_info}")
        
        context = "\n\n".join(context_parts)
        
        # Create prompt with context
        task = f"""Based on the following context, answer the query:

Query: {query}

Context:
{context}

Please provide a comprehensive answer based on the context above. Cite sources using [1], [2], etc.
"""
        
        # Get answer from the model
        answer = await self.execute_task(task)
        
        # Append sources
        sources_text = "\n\nSources:\n" + "\n".join(sources)
        
        # Remember this query
        await self.remember(
            f"RAG Query: {query[:100]}... ({len(results)} sources)",
            importance=3,
            tags=["rag", "query"]
        )
        
        return answer + sources_text
    
    async def create_knowledge_base(self, kb_name: str, description: str = "") -> str:
        """Create a new knowledge base.
        
        Args:
            kb_name: Name of the knowledge base
            description: Optional description
            
        Returns:
            str: Success message
        """
        if kb_name in self.knowledge_bases:
            return f"Knowledge base '{kb_name}' already exists"
        
        self.knowledge_bases[kb_name] = []
        
        await self.remember(
            f"Created knowledge base: {kb_name}",
            importance=2,
            tags=["rag", "kb", kb_name]
        )
        
        return f"Successfully created knowledge base: {kb_name}"
    
    async def add_to_knowledge_base(
        self,
        kb_name: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add content to a knowledge base.
        
        Args:
            kb_name: Name of the knowledge base
            content: Content to add
            metadata: Optional metadata
            
        Returns:
            str: Success message with document ID
        """
        if kb_name not in self.knowledge_bases:
            await self.create_knowledge_base(kb_name)
        
        # Add KB name to metadata
        kb_metadata = metadata or {}
        kb_metadata["knowledge_base"] = kb_name
        
        # Ingest document
        result = await self.ingest_document(content=content, metadata=kb_metadata)
        
        # Extract doc_id from result
        if "Successfully ingested document" in result:
            doc_id = result.split("document ")[1].split(" ")[0]
            self.knowledge_bases[kb_name].append(doc_id)
        
        return result
    
    async def query_knowledge_base(
        self,
        kb_name: str,
        query: str,
        top_k: int = 3
    ) -> str:
        """Query a specific knowledge base.
        
        Args:
            kb_name: Name of the knowledge base
            query: Query string
            top_k: Number of results
            
        Returns:
            str: Answer with context from KB
        """
        if kb_name not in self.knowledge_bases:
            return f"Knowledge base '{kb_name}' not found"
        
        # Filter by knowledge base
        return await self.query_with_context(
            query=query,
            top_k=top_k,
            filter_metadata={"knowledge_base": kb_name}
        )
    
    def _chunk_text(self, text: str, chunk_size: int, overlap: int) -> List[str]:
        """Split text into overlapping chunks.
        
        Args:
            text: Text to chunk
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            
        Returns:
            List of text chunks
        """
        chunks = []
        start = 0
        text_length = len(text)
        
        while start < text_length:
            # Get chunk
            end = start + chunk_size
            chunk = text[start:end]
            
            # Try to break at sentence or word boundary
            if end < text_length:
                # Look for sentence boundary
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                last_boundary = max(last_period, last_newline)
                
                if last_boundary > chunk_size * 0.5:  # At least 50% of chunk
                    chunk = chunk[:last_boundary + 1]
                    end = start + last_boundary + 1
            
            chunks.append(chunk.strip())
            start = end - overlap
        
        return [c for c in chunks if c]  # Remove empty chunks
    
    async def list_documents(self) -> str:
        """List all ingested documents.
        
        Returns:
            str: Formatted list of documents
        """
        if not self.documents:
            return "No documents ingested yet"
        
        result = ["Ingested Documents:"]
        result.append(f"{'ID':<20} {'Chunks':<10} {'Source'}")
        result.append("-" * 70)
        
        for doc in self.documents:
            doc_id = doc["id"][:20]
            chunks = doc["chunk_count"]
            source = doc["metadata"].get("source_file", doc["metadata"].get("title", "N/A"))
            result.append(f"{doc_id:<20} {chunks:<10} {source}")
        
        result.append(f"\nTotal: {len(self.documents)} documents, {len(self.chunks)} chunks")
        
        return "\n".join(result)
    
    async def get_document_info(self, doc_id: str) -> str:
        """Get information about a specific document.
        
        Args:
            doc_id: Document ID
            
        Returns:
            str: Document information
        """
        doc = next((d for d in self.documents if d["id"] == doc_id), None)
        
        if not doc:
            return f"Document not found: {doc_id}"
        
        info = [f"Document: {doc_id}"]
        info.append(f"Ingested: {doc['ingested_at']}")
        info.append(f"Chunks: {doc['chunk_count']}")
        info.append(f"Content Length: {len(doc['content'])} characters")
        
        if doc["metadata"]:
            info.append("\nMetadata:")
            for key, value in doc["metadata"].items():
                info.append(f"  {key}: {value}")
        
        return "\n".join(info)
    
    async def clear_knowledge_base(self, kb_name: Optional[str] = None) -> str:
        """Clear a knowledge base or all documents.
        
        Args:
            kb_name: Optional KB name (clears all if None)
            
        Returns:
            str: Success message
        """
        if kb_name:
            if kb_name not in self.knowledge_bases:
                return f"Knowledge base '{kb_name}' not found"
            
            # Remove documents in this KB
            doc_ids = self.knowledge_bases[kb_name]
            self.documents = [d for d in self.documents if d["id"] not in doc_ids]
            self.chunks = [c for c in self.chunks if c["doc_id"] not in doc_ids]
            
            del self.knowledge_bases[kb_name]
            
            return f"Cleared knowledge base: {kb_name}"
        else:
            # Clear everything
            count_docs = len(self.documents)
            count_chunks = len(self.chunks)
            
            self.documents.clear()
            self.chunks.clear()
            self.knowledge_bases.clear()
            
            return f"Cleared all documents ({count_docs} documents, {count_chunks} chunks)"
    
    def get_rag_stats(self) -> Dict[str, Any]:
        """Get RAG system statistics.
        
        Returns:
            Dict with statistics
        """
        return {
            "total_documents": len(self.documents),
            "total_chunks": len(self.chunks),
            "knowledge_bases": len(self.knowledge_bases),
            "kb_details": {
                kb: len(docs) for kb, docs in self.knowledge_bases.items()
            }
        }
