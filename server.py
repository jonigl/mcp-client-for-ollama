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
