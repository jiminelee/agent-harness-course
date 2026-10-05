"""Module 13's tool provider. No model or agent loop lives in this process.

The client starts this file automatically. stdout belongs to MCP; send any
debug prints to stderr (print(..., file=sys.stderr)).
"""

from mcp.server import MCPServer

mcp = MCPServer("Course arithmetic")


@mcp.tool()
def add(a: float, b: float) -> float:
    """Add two numbers and return their sum."""
    return a + b


@mcp.tool()
def multiply(a: float, b: float) -> float:
    """Multiply two numbers and return their product."""
    return a * b


if __name__ == "__main__":
    mcp.run(transport="stdio")
