"""
tools.py
========
The tool registry pattern from Module 3, packaged as a standalone module.
Any file in your project can `from agent_harness import tool` and register
new tools without touching this file or the core loop at all.

Includes two example tools (calculate, search_web) purely so the package
is runnable out of the box -- in a real project you'd likely remove these
and define your own domain-specific tools instead.
"""

import json

TOOL_REGISTRY = {}   # name -> python function
TOOLS_SCHEMA = []    # name -> JSON schema sent to the LLM
DANGEROUS_TOOLS = set()  # names marked as dangerous; policy is layered separately


def tool(description: str, parameters: dict, required: list, dangerous: bool = False):
    """
    Decorator that registers a function as an agent tool, exactly like
    Module 3/8. `dangerous=True` preserves the safety metadata introduced
    in Module 8, but this minimal Module 11 Agent does not enforce a human-
    confirmation gate. A real application can use DANGEROUS_TOOLS when it
    layers that policy on top of the core loop.
    """
    def decorator(fn):
        TOOL_REGISTRY[fn.__name__] = fn
        TOOLS_SCHEMA.append({
            "type": "function",
            "function": {
                "name": fn.__name__,
                "description": description,
                "parameters": {"type": "object", "properties": parameters, "required": required},
            },
        })
        if dangerous:
            DANGEROUS_TOOLS.add(fn.__name__)
        return fn
    return decorator


@tool(
    description="Evaluate a basic arithmetic expression and return the numeric result.",
    parameters={"expression": {"type": "string", "description": "e.g. '2 + 2'"}},
    required=["expression"],
)
def calculate(expression: str) -> str:
    """Example tool included so the package works out of the box."""
    return str(eval(expression, {"__builtins__": {}}, {}))


@tool(
    description="Search the web for a query and return a short summary of results.",
    parameters={"query": {"type": "string", "description": "The search query string."}},
    required=["query"],
)
def search_web(query: str) -> str:
    """STUB -- replace with a real search API call in a real project."""
    return f"[STUB RESULT] Pretend web search results for: '{query}'."


def execute_tool_call(tool_name: str, arguments_json: str,
                      registry: dict = None) -> str:
    """
    Shared execution helper with the error handling established in
    Module 3/6: unknown tools, bad JSON, and tool exceptions all become
    an "ERROR: ..." string instead of raising, so the agent loop never
    crashes because of a tool.
    """
    # Agent instances may expose different tool subsets, so execution must
    # use the same registry that belongs to that Agent. Falling back to the
    # global registry keeps direct calls and the default Agent convenient.
    active_registry = registry if registry is not None else TOOL_REGISTRY
    tool_fn = active_registry.get(tool_name)
    if tool_fn is None:
        return f"ERROR: unknown tool '{tool_name}'. Available: {list(active_registry.keys())}"
    try:
        tool_args = json.loads(arguments_json)
    except json.JSONDecodeError as e:
        return f"ERROR: could not parse arguments as JSON: {e}"
    try:
        return str(tool_fn(**tool_args))
    except Exception as e:
        return f"ERROR: tool '{tool_name}' raised an exception: {e}"
