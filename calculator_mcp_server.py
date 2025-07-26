from mcp.server import FastMCP

mcp = FastMCP("Calculator Server")

@mcp.tool(description="Calculator tool which performs calculations")
def calculator(x: int, y: int) -> int:
    print(f"[MCP SERVER] Calculator called with x={x}, y={y}")
    return x + y

mcp.run(transport="sse")