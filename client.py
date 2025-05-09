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
    # Initialize the MCP client with a model and console
    def __init__(self, model: str = "llama3.2:3b"):              
        self.console = Console()
        self.exit_stack = AsyncExitStack()
        self.model = model
        self.ollama = ollama.AsyncClient()
        self.session: Optional[ClientSession] = None

    # Connect to the MCP server using the provided script path
    async def connect_to_server(self, server_script_path: str):        
        is_python = server_script_path.endswith('.py')
        is_js = server_script_path.endswith('.js')
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(command=command, args=[server_script_path], env=None)
        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # List tools
        meta = await self.session.list_tools()
        self.console.print("Server connected. Tools:", [t.name for t in meta.tools], style="dim green")

    # Process a query by sending it to the model and handling tool calls
    async def process_query(self, query: str) -> str:
        messages = [{"role": "user", "content": query}]
        meta = await self.session.list_tools()
        tools_meta = [{"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.inputSchema}} for t in meta.tools]

        # Initial call
        resp: ChatResponse = await self.ollama.chat(model=self.model, messages=messages, tools=tools_meta)
        final = []
        if getattr(resp.message, "content", None):
            final.append(resp.message.content)
        # Check for tool calls
        elif resp.message.tool_calls:
            for tc in resp.message.tool_calls:
                # Call the tool
                result = await self.session.call_tool(tc.function.name, tc.function.arguments)
                messages.append({"role": "tool", "name": tc.function.name, "content": result.content[0].text})                
                # Call the model again with the tool result, so we can get the final answer
                resp = await self.ollama.chat(model=self.model, messages=messages, tools=tools_meta)
                final.append(resp.message.content)
        return "".join(final)

    # Main loop for user interaction
    async def chat_loop(self):
        self.console.print("[bold green]MCP Client Started![/bold green] Model: [cyan]{}[/cyan]".format(self.model))
        self.console.print("[italic]Type your queries below or [bold]'quit'[/bold] to exit.[/italic]")
        while True:
            q = input("Query: ").strip()
            if q.lower() == 'quit':
                break
            try:
                ans = await self.process_query(q)
                self.console.print(Markdown(ans))
            except Exception as e:
                self.console.print("Error:", e, style="bold red")

    async def cleanup(self):
        await self.exit_stack.aclose()

# Main function to parse arguments and run the client
async def main():
    p = argparse.ArgumentParser()
    p.add_argument("--mcp-server", required=True)
    p.add_argument("--model", default="llama3.2:3b")
    args = p.parse_args()
    client = MCPClient(model=args.model)
    try:
        await client.connect_to_server(args.mcp_server)
        await client.chat_loop()
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
