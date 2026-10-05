"""
Module 11: Multi-Agent & Orchestration
=========================================
Goal: Module 6 decomposed a task into subtasks, but ONE agent (with one
fixed toolset and persona) executed all of them. Sometimes you want
genuinely DIFFERENT specialists -- e.g. a researcher agent (good at using
search/calculation tools) and a writer agent (good at producing polished
prose, with no tools at all) -- each with their own system prompt, tools,
and even model if you wanted.

New pattern: SUB-AGENTS AS TOOLS.
  The cleanest way to build this with the exact same tool-calling
  mechanics we've used all along: wrap each sub-agent in a function that
  LOOKS like a tool to the top-level "orchestrator" LLM. When the
  orchestrator "calls" delegate_to_researcher(...), what actually happens
  under the hood is a WHOLE separate agent loop runs (with its own system
  prompt, tools, and turn limit), and its final answer is returned as the
  "tool result" to the orchestrator.

This means the orchestrator doesn't need any special multi-agent-specific
code -- from its point of view, it's just calling tools, exactly like
Module 3. The complexity is hidden inside each delegate function.
"""

import json
from openai import OpenAI

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
MODEL = "gemma4:e4b"

# Keep provider-specific options out of requests to models that may reject them.
LLM_OPTIONS = {"reasoning_effort": "none"} if API_KEY == "ollama" else {}

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

MAX_TURNS_PER_AGENT = 6


# ---------------------------------------------------------------------------
# GENERIC REUSABLE TOOL-CALLING LOOP (same shape as Module 3, factored out
# so BOTH sub-agents and the orchestrator can reuse it with different
# system prompts and toolsets)
# ---------------------------------------------------------------------------
def run_tool_calling_loop(system_prompt: str, user_message: str, tools_schema: list,
                            tool_registry: dict, agent_label: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]

    for turn in range(1, MAX_TURNS_PER_AGENT + 1):
        print(f"    [{agent_label} | turn {turn}] calling LLM with {len(messages)} messages...")
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tools_schema if tools_schema else None,
            **LLM_OPTIONS,
        )
        message = response.choices[0].message

        if message.tool_calls:
            messages.append(message)
            for tool_call in message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)
                tool_fn = tool_registry.get(tool_name)

                print(f"    [{agent_label} | turn {turn}] -> {tool_name}({tool_args})")
                if tool_fn is None:
                    tool_result = f"ERROR: unknown tool '{tool_name}'"
                else:
                    try:
                        tool_result = str(tool_fn(**tool_args))
                    except Exception as e:
                        tool_result = f"ERROR: {e}"
                print(f"    [{agent_label} | turn {turn}] <- {tool_result[:100]}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result,
                })
            continue

        print(f"    [{agent_label}] finished after {turn} turn(s).")
        return message.content

    return f"({agent_label} did not finish within its turn limit.)"


# ---------------------------------------------------------------------------
# SUB-AGENT 1: RESEARCHER
# Has real tools (calculate, search_web), no writing responsibility at all.
# ---------------------------------------------------------------------------
RESEARCHER_SYSTEM_PROMPT = """You are a research specialist. Use your tools
to gather facts and figures relevant to the question. Respond with concise,
factual notes -- NOT polished prose. Just the raw findings.
"""

RESEARCHER_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Evaluate a basic arithmetic expression.",
            "parameters": {
                "type": "object",
                "properties": {"expression": {"type": "string"}},
                "required": ["expression"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the web for a query and return a short summary.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
]


def _calculate(expression: str) -> str:
    return str(eval(expression, {"__builtins__": {}}, {}))


def _search_web(query: str) -> str:
    return f"[STUB RESULT] Pretend web search results for: '{query}'."


RESEARCHER_TOOL_REGISTRY = {"calculate": _calculate, "search_web": _search_web}


def delegate_to_researcher(question: str) -> str:
    """
    This is the function exposed to the ORCHESTRATOR as a "tool". Calling
    it runs a COMPLETE, independent researcher agent loop (with its own
    tools and system prompt) and returns that agent's final notes as the
    tool result.
    """
    return run_tool_calling_loop(
        system_prompt=RESEARCHER_SYSTEM_PROMPT,
        user_message=question,
        tools_schema=RESEARCHER_TOOLS_SCHEMA,
        tool_registry=RESEARCHER_TOOL_REGISTRY,
        agent_label="RESEARCHER",
    )


# ---------------------------------------------------------------------------
# SUB-AGENT 2: WRITER
# No tools at all -- purely a text specialist that turns raw notes into
# polished prose. Deliberately given a DIFFERENT persona/system prompt than
# the researcher, to show sub-agents can be shaped very differently.
# ---------------------------------------------------------------------------
WRITER_SYSTEM_PROMPT = """You are a writing specialist. You will be given
raw research notes and instructions. Turn them into clear, polished,
well-organized prose suitable for a non-technical reader. Do not invent
facts not present in the notes.
"""


def delegate_to_writer(notes_and_instructions: str) -> str:
    """
    No tools_schema/tool_registry needed here -- the writer agent is a pure
    text-in/text-out loop (it will simply never request a tool call, since
    none are offered). Still reuses the exact same run_tool_calling_loop
    function as the researcher -- demonstrating the loop shape is generic.
    """
    return run_tool_calling_loop(
        system_prompt=WRITER_SYSTEM_PROMPT,
        user_message=notes_and_instructions,
        tools_schema=[],
        tool_registry={},
        agent_label="WRITER",
    )


# ---------------------------------------------------------------------------
# ORCHESTRATOR
# Its "tools" are actually whole sub-agents. From the orchestrator LLM's
# point of view, this looks exactly like Module 3's tool calling -- it has
# no idea delegate_to_researcher secretly runs a multi-turn agent internally.
# ---------------------------------------------------------------------------
ORCHESTRATOR_SYSTEM_PROMPT = """You are an orchestrator managing two
specialists: a researcher (for gathering facts/figures) and a writer (for
producing polished prose from notes). Delegate appropriately -- typically
research first, then pass its notes to the writer. Give the final polished
text as your own last message once the writer has produced it.
"""

ORCHESTRATOR_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "delegate_to_researcher",
            "description": "Delegate a research question to the researcher specialist agent.",
            "parameters": {
                "type": "object",
                "properties": {"question": {"type": "string"}},
                "required": ["question"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_to_writer",
            "description": "Delegate writing to the writer specialist, given research notes and instructions.",
            "parameters": {
                "type": "object",
                "properties": {"notes_and_instructions": {"type": "string"}},
                "required": ["notes_and_instructions"],
            },
        },
    },
]

ORCHESTRATOR_TOOL_REGISTRY = {
    "delegate_to_researcher": delegate_to_researcher,
    "delegate_to_writer": delegate_to_writer,
}


def run_orchestrator(user_task: str) -> str:
    print(f"\n{'=' * 60}")
    print("[ORCHESTRATOR] Starting top-level orchestration loop...")
    print(f"{'=' * 60}")
    return run_tool_calling_loop(
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        user_message=user_task,
        tools_schema=ORCHESTRATOR_TOOLS_SCHEMA,
        tool_registry=ORCHESTRATOR_TOOL_REGISTRY,
        agent_label="ORCHESTRATOR",
    )


if __name__ == "__main__":
    task = (
        "I need a short paragraph, for a general audience, explaining what "
        "an 'agent harness' is and why tool calling matters -- please "
        "research the topic first, then have it written up nicely."
    )
    print(f"USER TASK: {task}")

    result = run_orchestrator(task)

    print(f"\n{'#' * 60}")
    print("FINAL ANSWER:")
    print(result)
    print(f"{'#' * 60}")
