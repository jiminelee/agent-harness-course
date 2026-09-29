"""Discover and call MCP tools without an LLM.

Run: python module12/inspect_tools.py
The agent example reuses these small connection/discovery helpers.
"""

import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import anyio  # installed by the MCP SDK; used for a lifecycle timeout
from mcp import Client, StdioServerParameters
from mcp.types import CallToolResult, TextContent

SERVER_PATH = Path(__file__).resolve().with_name("tool_server.py")
REQUEST_TIMEOUT = 10.0
SESSION_TIMEOUT = 300.0


@asynccontextmanager
async def connect_server(server_path=SERVER_PATH, *, request_timeout=REQUEST_TIMEOUT,
                         session_timeout=SESSION_TIMEOUT):
    """Start one child, keep it alive for the run, then let the SDK reap it.

The outer deadline includes startup and the entire session. Keeping its
cancel scope outside Client's context also lets cleanup unwind in order.
"""
    params = StdioServerParameters(
        command=sys.executable, args=[str(Path(server_path).resolve())],
    )
    with anyio.fail_after(session_timeout):
        async with Client(params, read_timeout_seconds=request_timeout) as client:
            yield client


async def discover_tools(client):
    """Collect every page; no local function registry is needed."""
    tools = []
    cursor = None
    while True:
        page = await client.list_tools(cursor=cursor)
        tools.extend(page.tools)
        if page.next_cursor is None:
            return tools
        cursor = page.next_cursor


def format_tool_result(result: CallToolResult) -> str:
    """Adapt MCP's richer result to this course's text-only model messages.

Preserve all text blocks and structured output. Never silently discard an
image/resource/audio block: explain that this adapter cannot render it.
"""
    parts = []
    for block in result.content:
        if isinstance(block, TextContent):
            parts.append(block.text)
        else:
            parts.append(f"[Unsupported MCP content type: {block.type}; text-only adapter]")
    if result.structured_content is not None:
        parts.append("Structured result: " + json.dumps(
            result.structured_content, ensure_ascii=False, allow_nan=False,
        ))
    text = "\n".join(parts) or "(Tool returned no content.)"
    return f"ERROR: {text}" if result.is_error else text


async def main():
    print("[MCP] Starting local server (no model needed)...")
    async with connect_server() as client:
        tools = await discover_tools(client)
        for tool in tools:
            print(f"[DISCOVER] {tool.name}: {tool.description}")
            print(json.dumps(tool.input_schema, indent=2))
        result = await client.call_tool("multiply", {"a": 6, "b": 7})
        print("[CALL] multiply(6, 7)")
        print(format_tool_result(result))
        if result.is_error:
            raise RuntimeError("The inspection tool call failed.")
    print("[MCP] Connection closed; server process cleaned up.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[MCP] Interrupted.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"[MCP] Inspection failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        sys.exit(1)
