The **Model Context Protocol (MCP)** is a powerful framework for enabling communication between clients and servers, particularly when working with AI models. In this article, I’ll walk you through how to build an MCP server and client in Python using a simple and didactic approach. By the end, you’ll have a working example of an MCP client-server setup that uses the **Ollama** AI model for processing queries.

Let’s dive in!

---

## What is MCP?

MCP (Model Context Protocol) is a protocol designed to facilitate communication between AI models and tools. It allows clients to send queries to servers, which can process those queries using AI models and optionally invoke tools to perform specific tasks.

---

## Setting Up the Environment

Before we start coding, let’s set up the environment. Here’s what you’ll need:

### Requirements

- **Python 3.10+**
- **Ollama** running locally
- **UV package manager** for managing dependencies

### Installation

1. Create a virtual environment and activate it:
   ```bash
   uv venv
   source .venv/bin/activate
   ```

2. Install the required dependencies:
   ```bash
   uv pip install .
   ```

---

## Building the MCP Server

The server is responsible for handling client queries and invoking tools when needed. Let’s create a simple MCP server that provides weather information for a given city.

### Server Code

Here’s the Python code for the server:

```python
from mcp.server.fastmcp import FastMCP
import urllib

# Initialize FastMCP server
mcp = FastMCP("weather")

# Register a tool
@mcp.tool()
def get_weather(city: str) -> str:
    """
    Get the current weather for a given city

    Args:
      city (str): The name of the city

    Returns:
      str: The current weather in the city, for example, "Sunny +20°C"
    """
    contents = urllib.request.urlopen(f'https://wttr.in/{urllib.parse.quote_plus(city)}?format=%C+%t').read()
    return contents.decode('utf-8')

if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport='stdio')
```

### How It Works

1. **FastMCP Initialization**: The `FastMCP` server is initialized with a name (`"weather"`).
2. **Tool Registration**: The `@mcp.tool()` decorator registers a function (`get_weather`) as a tool that the server can invoke.
3. **Weather API**: The `get_weather` function fetches weather data from the [wttr.in](https://wttr.in) API.
4. **Server Execution**: The server runs using the `stdio` transport.

---

## Building the MCP Client

The client connects to the server, sends queries, and processes responses. It also uses the **Ollama** AI model to handle queries and invoke tools when needed.

### Client Code

Here’s the Python code for the client:

```python
import argparse
import asyncio
from contextlib import AsyncExitStack
import ollama
from ollama import ChatResponse
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rich.console import Console
from rich.markdown import Markdown
from typing import Optional

class MCPClient:
    def __init__(self, model: str = "llama3.2:3b"):
        """Initialize the MCP client"""
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.ollama = ollama.AsyncClient()
        self.model = model

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server"""
        is_python = server_script_path.endswith('.py')
        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])

    async def process_query(self, query: str) -> str:
        """Process a query using Ollama and available tools"""
        messages = [{"role": "user", "content": query}]
        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]

        response: ChatResponse = await self.ollama.chat(
            model=self.model,
            messages=messages,
            tools=available_tools,
            options={"num_predict": 1000}
        )

        final_text = []
        if hasattr(response.message, 'content') and response.message.content:
            final_text.append(response.message.content)

        elif response.message.tool_calls:
            for tool in response.message.tool_calls:
                tool_name = tool.function.name
                tool_args = tool.function.arguments
                result = await self.session.call_tool(tool_name, tool_args)
                messages.append({
                    "role": "tool",
                    "content": result.content[0].text,
                    "name": tool_name
                })
                response = await self.ollama.chat(
                    model=self.model,
                    messages=messages,
                    tools=available_tools,
                    options={"num_predict": 500}
                )
                final_text.append(response.message.content)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print(f"Using Ollama model: {self.model}")
        print("Type your queries or 'quit' to exit.")

        while True:
            query = input("\nQuery: ").strip()
            if query.lower() == 'quit':
                break
            response = await self.process_query(query)
            if response:
                console = Console()
                console.print(Markdown(response))
            else:
                print("No response received.")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    parser = argparse.ArgumentParser(description="MCP Client")
    parser.add_argument("--mcp-server", required=True, help="Path to the server script (.py or .js)")
    parser.add_argument("--model", default="llama3.2:3b", help="Ollama model to use for API calls")
    args = parser.parse_args()

    client = MCPClient(model=args.model)
    try:
        await client.connect_to_server(args.mcp_server)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Running the MCP Client and Server

1. Start the server:
   ```bash
   python server.py
   ```

2. Run the client:
   ```bash
   uv run client.py --mcp-server server.py --model llama3.2:3b
   ```

3. Interact with the client by typing queries like:
   ```
   Query: What is the weather in New York?
   ```
