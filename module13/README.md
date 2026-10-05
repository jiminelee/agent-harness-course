# Module 13: MCP — Discovering and Calling External Tools

**Files:** `tool_server.py`, `inspect_tools.py`, `module13_mcp_tools.py`
**Builds on:** Module 3's registry and loop; Module 8's `async` / `await`

## Concept

In Module 3, the harness owns a dictionary mapping tool names to Python
functions. What if a separate program provides the tools, or several
applications should use the same implementation?

**Model Context Protocol (MCP)** defines how an application discovers and
calls tools supplied by another program. This module moves two arithmetic
functions into a local MCP server, then connects our own harness to it.

MCP does **not** replace the model's tool calling or the agent loop. The
model still requests a named tool with arguments; our code executes that
request and sends the result back. MCP changes how the harness learns
which tools exist and reaches their implementations.

## Three names to learn

| Term | In this module |
|---|---|
| Host | Our application managing the model, history, and loop |
| Client | The SDK `Client` inside the host, talking to the server |
| Server | `tool_server.py`, a separate program exposing `add` and `multiply` |

A server does not necessarily mean a remote computer. Here the client
starts a child process on your machine. They exchange protocol messages
over **stdio** (standard input/output), so you need no port or second
terminal for MCP. Ollama, if used, is a separate model service.

The tool server has no LLM and does not choose actions. The host makes
model requests and routes the requested actions to the server.

## What's new since Module 3

| Module 3 | Module 13 |
|---|---|
| Local `@tool` decorator | SDK `@mcp.tool()` on the server |
| Locally assembled `TOOLS_SCHEMA` | `list_tools()` definitions, adapted for the model |
| `TOOL_REGISTRY[name](**args)` | `await client.call_tool(name, args)` |
| Python function result | MCP content, optional structured data, and error status |
| One process | Host and tool-server processes |
| Messages and bounded loop | Same responsibilities, now with async requests |

Registration still exists on the server. The host no longer imports tool
implementations or keeps a name-to-function registry. Its set of discovered
names is only an allowlist, not executable code.

## Setup

Use **Python 3.10+** and activate the project virtual environment described
in the [root README](../README.md). From the project root:

```bash
python -m pip install -r module13/requirements.txt
```

This module pins the direct dependencies to `mcp==2.2.0` and
`openai==3.19.2`, verified together. It uses the official SDK's **MCPServer**
(`from mcp.server import MCPServer`) and **Client** (`from mcp import Client`)
APIs. Older v1/FastMCP examples have different APIs; do not mix them into
this example. Transitive dependencies are resolved by pip, not locked here.

## Step 1: use MCP without a model

```bash
python module13/inspect_tools.py
```

This starts the server, prints each tool's name, description, and input
JSON Schema, then calls `multiply` with `a=6`, `b=7`. No model server or API
key is needed. Look for output like this (schemas omitted here):

```text
[DISCOVER] add: Add two numbers and return their sum.
[DISCOVER] multiply: Multiply two numbers and return their product.
[CALL] multiply(6, 7)
42.0
Structured result: {"result": 42.0}
[MCP] Connection closed; server process cleaned up.
```

The SDK derives input schemas from type hints. The numeric return is
represented as readable content and structured output; inspection shows
both. Do not separately start `tool_server.py`: the client starts it using
the active Python interpreter and an absolute path, and closes it afterward.

## Step 2: connect the agent loop

Start the course's model service as described in the root README, then run:

```bash
python module13/module13_mcp_tools.py
```

The task is “Multiply 6 by 7, then add 10 to that result.” The expected
arithmetic result is **52**. Check `[MCP CALL]` and `[MCP RESULT]` logs:
a correct final number alone does not demonstrate MCP use.

```text
Host starts server -> discovers tools -> converts schemas for model
    |
LLM requests multiply(a=6, b=7)
    |
Host calls MCP server -> result 42 -> tool message back to LLM
    |
LLM requests add(a=42, b=10)
    |
Host calls MCP server -> result 52 -> tool message back to LLM
    |
LLM returns final answer -> host closes connection
```

Exact responses and call counts vary. As in Module 3, no tool calls means
the loop stops; it is not proof of answer correctness.

Provider settings are at the top of `module13_mcp_tools.py`: `BASE_URL`,
`API_KEY`, and `MODEL`. Defaults match the earlier Ollama examples. The
`reasoning_effort` option is sent only with the dummy `ollama` key.
Configuration is not loaded from `.env`.

## Read the code in this order

1. **`tool_server.py`:** two ordinary functions registered on `MCPServer`.
2. **`inspect_tools.py`:** connection lifecycle, paginated discovery, and
   conversion from MCP results to text.
3. **`to_model_tool_schema()` in the agent:** copy the name, description,
   and input schema into the model API format.
4. **`execute_mcp_tool_call()`:** parse arguments, call the server, format
   the result. Compare it with Module 3's local dispatch.
5. **`run_agent_loop()`:** append the assistant request before its results,
   preserve each `tool_call_id`, and repeat within a turn limit.

`await` suspends a function while a request completes. `async with` owns a
connection's lifetime, including cleanup on exceptions. Tool calls are
sequential here; this module does not repeat Module 8's parallelism lesson.

## Results, errors, and lifecycle

- **Model argument errors:** unknown names, malformed JSON, and non-object
  arguments become `ERROR:` messages without contacting the server. The
  server validates the actual function inputs.
- **Tool errors:** MCP's `is_error` flag becomes an `ERROR:` message that
  the model can use to correct its next attempt.
- **Request failures:** timeouts, protocol exceptions, and broken connections
  abort the run rather than repeatedly asking the model to retry a dead
  server. These differ from successful requests returning tool errors.
- **Results:** all text blocks and structured data are preserved. Other
  content types are explicitly marked unsupported by this text-only adapter.
- **Limits:** MCP requests have a 10-second read timeout. An outer
  300-second deadline includes startup and the whole session. Model calls
  have a 60-second timeout with automatic retries disabled. `MAX_TURNS=8`
  also bounds the loop.
- **Cleanup:** context managers close clients and let the SDK clean up the
  child process, including during failure or keyboard interruption.

Server stdout belongs to MCP protocol traffic. Send server debug prints to
stderr with `print(..., file=sys.stderr)`. Host-side prints are fine.


## Troubleshooting

| Symptom | Check |
|---|---|
| Cannot import `MCPServer` or `Client` | Install this module's pinned requirements in the active environment |
| Manually launched server looks idle | Run `inspect_tools.py`; stdio servers wait for protocol input |
| Protocol parsing errors | Remove server-side stdout debug prints |
| Inspection works, agent fails | Check model service, model name, and tool-calling support |
| Answer is 52, but no MCP logs | Model answered directly; inspect prompt and model behavior |
| Request/session timeout | Check startup, tool duration, and constants in `inspect_tools.py` |

## Things to try

- Add `subtract(a: float, b: float) -> float` with `@mcp.tool()` **above**
  the server's `if __name__ == "__main__"` block. Restart inspection and
  confirm it appears without changing any client registry.
- Change the task to use subtraction and observe the new tool call.
- Call `add` with a missing argument in inspection and examine the error.
  Restore the valid call afterward.
- Compare with Module 3: which code moved, and which loop logic stayed?

## Boundaries and next steps

This uses one trusted local server, reads its tool list once per run, and
exposes that list to the model. Dynamic updates, multiple-server routing,
remote authentication, and multimodal results are outside the exercise.
A production host must decide which discovered tools it permits. MCP alone
does not provide sandboxing or human approval; apply Module 9's policy ideas
before exposing side-effecting tools.

MCP also supports **Resources** (data the host can retrieve) and **Prompts**
(reusable prompt templates). These are separate capabilities, not tools
automatically added to the model. Explore them and remote Streamable HTTP
after understanding local tool discovery and execution.

> The harness still controls the agent. MCP standardizes how it discovers
> and reaches independently provided tools.

Continue to [Module 14: Production Roadmap](../module14/README.md).

## Official references

- [Architecture](https://modelcontextprotocol.io/docs/learn/architecture)
- [SDK installation](https://py.sdk.modelcontextprotocol.io/get-started/installation/)
- [MCPServer first steps](https://py.sdk.modelcontextprotocol.io/get-started/first-steps/)
- [Client, discovery, and results](https://py.sdk.modelcontextprotocol.io/client/)
- [Client transports](https://py.sdk.modelcontextprotocol.io/client/transports/)
