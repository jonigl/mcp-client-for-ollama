import asyncio
from typing import Optional
from contextlib import AsyncExitStack
import argparse
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from dotenv import load_dotenv
import ollama
from ollama import ChatResponse
from rich.console import Console
from rich.markdown import Markdown
class MCPClient:
    def __init__(self, model: str = "qwen2.5:latest"):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.ollama = ollama.AsyncClient()
        self.model = model

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

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
        messages = [
            {
                "role": "user",
                "content": query
            }
        ]

        response = await self.session.list_tools()
        available_tools = [{
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.inputSchema
            }
        } for tool in response.tools]        

        # Initial Ollama API call
        response: ChatResponse = await self.ollama.chat(
            model=self.model,
            messages=messages,
            tools=available_tools,
            options={"num_predict": 1000}
        )

        # Process response and handle tool calls
        final_text = []
        
        if hasattr(response.message, 'content') and response.message.content:
            final_text.append(response.message.content)            

        elif response.message.tool_calls:
            for tool in response.message.tool_calls:
                tool_name = tool.function.name
                tool_args = tool.function.arguments

                # Execute tool call
                result = await self.session.call_tool(tool_name, tool_args)
                print(f"\n[Calling tool {tool_name} with args {tool_args}]\n")
                
                messages.append({
                    "role": "tool",
                    "content": result.content[0].text,
                    "name": tool_name
                })            

                # Get next response from Ollama with the tool results
                response = await self.ollama.chat(
                    model=self.model,
                    messages=messages,
                    tools=available_tools,
                    # options={"num_predict": 500}
                )

                final_text.append(response.message.content)

        return "\n".join(final_text)

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print(f"Using Ollama model: {self.model}")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == 'quit':
                    break

                response = await self.process_query(query)
                if response:
                    console = Console()
                    console.print(Markdown(response))
                else:
                    print("No response received.")

            except Exception as e:
                print(f"\nError: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    parser = argparse.ArgumentParser(description="MCP Client")
    parser.add_argument("--mcp-server", required=True, help="Path to the server script (.py or .js)")
    parser.add_argument("--model", default="qwen2.5:latest", help="Ollama model to use for API calls")
    args = parser.parse_args()

    client = MCPClient(model=args.model)
    try:
        await client.connect_to_server(args.mcp_server)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
