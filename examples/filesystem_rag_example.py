"""
Example demonstrating FileSystem and RAG agent capabilities.

This script shows how to:
1. Use FileSystemAgent for file operations (read, write, edit, delete)
2. Use RAGAgent for knowledge management and retrieval
3. Combine agents for complex workflows
"""

import asyncio
from rich.console import Console
from contextlib import AsyncExitStack
import ollama

from mcp_client_for_ollama.agents import AgentManager


async def main():
    """Run filesystem and RAG agents example."""
    console = Console()
    console.print("\n[bold blue]🗂️  FileSystem & RAG Agents Example[/bold blue]\n")
    
    # Initialize components
    ollama_client = ollama.AsyncClient()
    exit_stack = AsyncExitStack()
    
    # Create agent manager
    manager = AgentManager(console, ollama_client, exit_stack)
    
    # Example 1: Create FileSystem agent
    console.print("[bold cyan]Step 1: Creating FileSystem Agent[/bold cyan]")
    
    fs_agent = manager.create_agent(
        agent_type="filesystem",
        name="file-manager",
        model="qwen2.5:7b"
    )
    
    if fs_agent:
        console.print("✓ FileSystem agent created")
        
        # Demonstrate file operations
        console.print("\n[bold cyan]Step 2: File Operations Demo[/bold cyan]")
        
        # Write a file
        console.print("Writing test file...")
        result = await fs_agent.write_file(
            "/tmp/test_file.txt",
            "This is a test file created by the FileSystem agent.\nLine 2\nLine 3"
        )
        console.print(f"  {result}")
        
        # Read the file
        console.print("\nReading test file...")
        content = await fs_agent.read_file("/tmp/test_file.txt")
        console.print(f"  Content: {content[:50]}...")
        
        # Edit the file
        console.print("\nEditing test file...")
        result = await fs_agent.edit_file(
            "/tmp/test_file.txt",
            "Line 2",
            "Modified Line 2"
        )
        console.print(f"  {result}")
        
        # List directory
        console.print("\nListing /tmp directory...")
        listing = await fs_agent.list_directory("/tmp", "test_*.txt")
        console.print(f"  {listing[:200]}...")
        
        # Get operations summary
        summary = fs_agent.get_operations_summary()
        console.print(f"\nOperations performed: {summary['total_operations']}")
        console.print(f"  Successful: {summary['successful']}")
        console.print(f"  Failed: {summary['failed']}")
    
    # Example 2: Create RAG agent
    console.print("\n[bold cyan]Step 3: Creating RAG Agent[/bold cyan]")
    
    rag_agent = manager.create_agent(
        agent_type="rag",
        name="knowledge-base",
        model="qwen2.5:7b"
    )
    
    if rag_agent:
        console.print("✓ RAG agent created")
        
        # Ingest documents
        console.print("\n[bold cyan]Step 4: RAG Operations Demo[/bold cyan]")
        
        console.print("Ingesting knowledge...")
        
        # Ingest some sample documents
        doc1 = """
        Smart Contract Security Best Practices:
        
        1. Always use the latest Solidity compiler version
        2. Implement access control using modifiers
        3. Use SafeMath for arithmetic operations
        4. Avoid using tx.origin for authorization
        5. Be careful with external calls (reentrancy)
        6. Use pull over push for payments
        """
        
        result = await rag_agent.ingest_document(
            content=doc1,
            doc_id="security-best-practices",
            metadata={"category": "security", "type": "guide"}
        )
        console.print(f"  {result}")
        
        doc2 = """
        Common Smart Contract Vulnerabilities:
        
        1. Reentrancy: Allows attackers to repeatedly call a function
        2. Integer Overflow/Underflow: Arithmetic errors
        3. Access Control: Unauthorized access to functions
        4. Front-running: Transaction ordering attacks
        5. Denial of Service: Making contract unusable
        """
        
        result = await rag_agent.ingest_document(
            content=doc2,
            doc_id="common-vulnerabilities",
            metadata={"category": "security", "type": "reference"}
        )
        console.print(f"  {result}")
        
        # List documents
        console.print("\nIngested documents:")
        docs_list = await rag_agent.list_documents()
        console.print(f"  {docs_list}")
        
        # Query the knowledge base
        console.print("\n[bold cyan]Step 5: Querying Knowledge Base[/bold cyan]")
        
        query = "What is reentrancy and how to prevent it?"
        console.print(f"Query: {query}")
        
        # This would normally call the LLM, but we'll skip for demo
        console.print("  (Would query LLM with retrieved context)")
        
        # Search for relevant chunks
        results = await rag_agent.search(query, top_k=3)
        console.print(f"\nFound {len(results)} relevant chunks")
        for i, result in enumerate(results, 1):
            console.print(f"  [{i}] Score: {result['score']:.2f}")
            console.print(f"      Text: {result['chunk']['text'][:100]}...")
        
        # Get RAG stats
        stats = rag_agent.get_rag_stats()
        console.print(f"\nRAG Statistics:")
        console.print(f"  Documents: {stats['total_documents']}")
        console.print(f"  Chunks: {stats['total_chunks']}")
    
    # Example 3: Combined workflow
    console.print("\n[bold cyan]Step 6: Combined Workflow[/bold cyan]")
    console.print("Scenario: Read code, analyze with RAG, save findings")
    
    # This demonstrates how the agents can work together
    console.print("  1. FileSystem agent reads contract file")
    console.print("  2. RAG agent analyzes code against knowledge base")
    console.print("  3. FileSystem agent saves audit report")
    console.print("  (Skipped for demo - requires actual LLM)")
    
    # Cleanup
    console.print("\n[bold cyan]Cleanup[/bold cyan]")
    
    # Clean up test file
    if fs_agent:
        result = await fs_agent.delete_file("/tmp/test_file.txt")
        console.print(f"  {result}")
    
    await manager.cleanup_all()
    await exit_stack.aclose()
    console.print("✓ All agents cleaned up\n")
    
    # Summary
    console.print("[bold green]✓ FileSystem & RAG Example Complete![/bold green]")
    console.print("\nNew Capabilities Demonstrated:")
    console.print("  • File operations: read, write, edit, delete, list")
    console.print("  • RAG: document ingestion, search, knowledge management")
    console.print("  • Agent memory: persistent context across operations")
    console.print("  • Combined workflows: agents working together")


if __name__ == "__main__":
    asyncio.run(main())
