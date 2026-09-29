"""Run from the root: python -m unittest discover -s module12 -v

Uses real stdio MCP servers and a scripted model; no model downloads/API
credentials are needed. Temporary fixtures are removed after each test.
"""

import copy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock

from mcp.types import CallToolResult, ImageContent, ListToolsResult, TextContent, Tool
from openai.types.chat import ChatCompletionMessage

from inspect_tools import connect_server, discover_tools, format_tool_result
from module12_mcp_tools import (
    MCPConnectionError, execute_mcp_tool_call, run_agent_loop, to_model_tool_schema,
)


def tool_call(name, arguments, call_id="call_1"):
    return SimpleNamespace(id=call_id, function=SimpleNamespace(
        name=name, arguments=arguments,
    ))


class AdapterTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_preserves_pages_and_schema(self):
        schema = {"type": "object", "properties": {"a": {"type": "number"}},
                  "required": ["a"], "additionalProperties": False}
        first = Tool(name="first", description="A tool", input_schema=schema)
        second = Tool(name="second", input_schema={"type": "object"})
        client = SimpleNamespace(list_tools=AsyncMock(side_effect=[
            ListToolsResult(tools=[first], next_cursor="page2"),
            ListToolsResult(tools=[second]),
        ]))
        tools = await discover_tools(client)
        self.assertEqual([t.name for t in tools], ["first", "second"])
        self.assertEqual(client.list_tools.await_args_list[1].kwargs, {"cursor": "page2"})
        self.assertEqual(to_model_tool_schema(first)["function"], {
            "name": "first", "description": "A tool", "parameters": schema,
        })

    async def test_bad_model_arguments_do_not_reach_server(self):
        client = SimpleNamespace(call_tool=AsyncMock())
        for name, arguments in [("missing", "{}"), ("add", "{"), ("add", "[]")]:
            result = await execute_mcp_tool_call(client, tool_call(name, arguments), {"add"})
            self.assertTrue(result.startswith("ERROR:"))
        client.call_tool.assert_not_awaited()

    async def test_transport_exception_aborts_instead_of_becoming_tool_error(self):
        client = SimpleNamespace(call_tool=AsyncMock(side_effect=ConnectionError("closed")))
        with self.assertRaises(MCPConnectionError):
            await execute_mcp_tool_call(client, tool_call("add", "{}"), {"add"})

    def test_result_preserves_blocks_structured_data_and_error(self):
        result = CallToolResult(
            content=[TextContent(type="text", text="first"),
                     TextContent(type="text", text="second"),
                     ImageContent(type="image", data="AA==", mime_type="image/png")],
            structured_content={"answer": 42}, is_error=True,
        )
        text = format_tool_result(result)
        self.assertTrue(text.startswith("ERROR:"))
        self.assertIn("first\nsecond", text)
        self.assertIn('"answer": 42', text)
        self.assertIn("Unsupported MCP content type: image", text)
        self.assertIn("no content", format_tool_result(CallToolResult(content=[])))


class StdioTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_discovery_execution_and_validation_errors(self):
        async with connect_server() as client:
            self.assertEqual({t.name for t in await discover_tools(client)}, {"add", "multiply"})
            result = await client.call_tool("multiply", {"a": 6, "b": 7})
            self.assertFalse(result.is_error)
            self.assertEqual(result.structured_content, {"result": 42.0})
            for name, arguments in [("add", {"a": 1}), ("add", {"a": "bad", "b": 1}),
                                    ("missing", {})]:
                failure = await client.call_tool(name, arguments)
                self.assertTrue(failure.is_error)
                self.assertTrue(format_tool_result(failure).startswith("ERROR:"))

    async def test_agent_loop_with_scripted_model_and_real_mcp(self):
        calls = []

        async def complete(**kwargs):
            calls.append(copy.deepcopy(kwargs))
            index = len(calls)
            if index < 3:
                name, args = (("multiply", {"a": 6, "b": 7}) if index == 1
                              else ("add", {"a": 42, "b": 10}))
                message = ChatCompletionMessage(role="assistant", tool_calls=[{
                    "id": f"call_{index}", "type": "function",
                    "function": {"name": name, "arguments": json.dumps(args)},
                }])
            else:
                message = ChatCompletionMessage(role="assistant", content="52")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)])

        llm = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=complete)))
        async with connect_server() as client:
            self.assertEqual(await run_agent_loop("Multiply, then add", client, llm), "52")
        messages = calls[-1]["messages"]
        self.assertEqual([m["role"] for m in messages],
                         ["system", "user", "assistant", "tool", "assistant", "tool"])
        self.assertEqual(messages[3]["tool_call_id"], "call_1")
        self.assertEqual(messages[5]["tool_call_id"], "call_2")
        self.assertIn("42.0", messages[3]["content"])
        self.assertIn("52.0", messages[5]["content"])

    async def test_server_extension_and_cleanup_after_timeout(self):
        # A temporary server extends the actual course server. The client has
        # no knowledge of these new tools or their Python implementations.
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "server.py"
            pid_file = Path(directory) / "pid"
            fixture.write_text(
                "import asyncio, os, sys\n"
                f"sys.path.insert(0, {str(Path(__file__).resolve().parent)!r})\n"
                "from tool_server import mcp\n"
                f"open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n"
                "@mcp.tool()\n"
                "def subtract(a: float, b: float) -> float:\n"
                "    return a - b\n"
                "@mcp.tool()\n"
                "async def slow() -> str:\n"
                "    await asyncio.sleep(30)\n"
                "    return 'done'\n"
                "@mcp.tool()\n"
                "def fail() -> str:\n"
                "    raise ValueError('deliberate tool failure')\n"
                "mcp.run(transport='stdio')\n", encoding="utf-8",
            )
            async with connect_server(fixture) as client:
                names = {t.name for t in await discover_tools(client)}
                self.assertIn("subtract", names)
                result = await client.call_tool("subtract", {"a": 9, "b": 4})
                self.assertEqual(result.structured_content, {"result": 5.0})
                self.assertTrue((await client.call_tool("fail", {})).is_error)
                with self.assertRaises(MCPConnectionError):
                    # Use the SDK's per-request deadline, leaving ample startup time.
                    async def timed_call(name, arguments):
                        return await client.call_tool(name, arguments, read_timeout_seconds=0.1)
                    proxy = SimpleNamespace(call_tool=timed_call)
                    await execute_mcp_tool_call(proxy, tool_call("slow", "{}"), names)
            if os.name == "posix":
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(pid_file.read_text()), 0)

    async def test_missing_server_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            entered = False
            with self.assertRaises(Exception):
                async with connect_server(Path(directory) / "missing.py", session_timeout=5):
                    entered = True
            self.assertFalse(entered, "A missing server must not connect")

    async def test_startup_deadline_cleans_up_unresponsive_child(self):
        with tempfile.TemporaryDirectory() as directory:
            fixture = Path(directory) / "unresponsive.py"
            pid_file = Path(directory) / "pid"
            fixture.write_text(
                "import os, time\n"
                f"open({str(pid_file)!r}, 'w').write(str(os.getpid()))\n"
                "time.sleep(30)\n", encoding="utf-8",
            )
            entered = False
            with self.assertRaises(TimeoutError):
                async with connect_server(fixture, session_timeout=1):
                    entered = True
            self.assertFalse(entered)
            self.assertTrue(pid_file.exists(), "Fixture must start to test child cleanup")
            if os.name == "posix":
                with self.assertRaises(ProcessLookupError):
                    os.kill(int(pid_file.read_text()), 0)


if __name__ == "__main__":
    unittest.main()
