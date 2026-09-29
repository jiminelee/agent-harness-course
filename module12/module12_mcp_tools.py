"""Module 12: keep the agent loop; replace local dispatch with MCP.

Run: python module12/module12_mcp_tools.py
Read inspect_tools.py first: it demonstrates the same connection without
requiring a model. SDK 2.x uses MCPServer/Client, not the old v1 examples.
"""

import asyncio
import json
import sys

from openai import AsyncOpenAI

from inspect_tools import connect_server, discover_tools, format_tool_result

BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
MODEL = "gemma4:e4b"
LLM_OPTIONS = {"reasoning_effort": "none"} if API_KEY == "ollama" else {}
MAX_TURNS = 8
SYSTEM_PROMPT = (
    "You are a helpful assistant. Use the provided tools for every arithmetic "
    "operation. For dependent operations, use the actual previous tool result. "
    "Only give the final answer once the tools have returned the needed results."
)


class MCPConnectionError(RuntimeError):
    """An MCP request failed, as opposed to a tool returning an error result."""


def to_model_tool_schema(tool):
    """MCP describes tools; this adapter exposes them to Chat Completions."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


async def execute_mcp_tool_call(client, tool_call, available_names):
    name = tool_call.function.name
    # This is a discovered-name allowlist, not a name -> Python function registry.
    if name not in available_names:
        return f"ERROR: unknown tool '{name}'. Available: {sorted(available_names)}"
    try:
        arguments = json.loads(tool_call.function.arguments)
    except json.JSONDecodeError as exc:
        return f"ERROR: invalid JSON arguments: {exc}"
    if not isinstance(arguments, dict):
        return "ERROR: tool arguments must be a JSON object."

    print(f"[MCP CALL] {name}({arguments})")
    try:
        result = await client.call_tool(name, arguments)
    except Exception as exc:
        # Do not feed a disconnected server into a model retry loop. Tool-level
        # failures arrive as result.is_error and remain recoverable below.
        raise MCPConnectionError(f"MCP request for '{name}' failed: {exc}") from exc
    text = format_tool_result(result)
    print(f"[MCP RESULT] {text}")
    return text


async def run_agent_loop(user_task, mcp_client, llm_client, *, max_turns=MAX_TURNS):
    tools = await discover_tools(mcp_client)
    if not tools:
        raise RuntimeError("MCP server exposed no tools.")
    schemas = [to_model_tool_schema(tool) for tool in tools]
    names = {tool.name for tool in tools}
    print(f"[DISCOVER] {', '.join(sorted(names))}")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]

    for turn in range(1, max_turns + 1):
        print(f"[STEP {turn}] Sending {len(messages)} messages to the model...")
        response = await llm_client.chat.completions.create(
            model=MODEL, messages=messages, tools=schemas, **LLM_OPTIONS,
        )
        message = response.choices[0].message
        if not message.tool_calls:
            return message.content or "(Model returned no text.)"

        # The model still uses tool calling. Only the execution boundary changes.
        messages.append(message.model_dump(exclude_none=True))
        for tool_call in message.tool_calls:
            result = await execute_mcp_tool_call(mcp_client, tool_call, names)
            messages.append({
                "role": "tool", "tool_call_id": tool_call.id, "content": result,
            })

    return "(Agent did not finish within the turn limit.)"


async def main():
    task = "Multiply 6 by 7, then add 10 to that result."
    print(f"USER TASK: {task}")
    async with connect_server() as mcp_client:
        async with AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY,
                               timeout=60.0, max_retries=0) as llm_client:
            answer = await run_agent_loop(task, mcp_client, llm_client)
    print(f"\nFINAL ANSWER:\n{answer}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrupted; closing clients and server.", file=sys.stderr)
        sys.exit(130)
    except Exception as exc:
        print(f"Run failed ({type(exc).__name__}): {exc}\n"
              "Run inspect_tools.py to check MCP separately from the model.", file=sys.stderr)
        sys.exit(1)
