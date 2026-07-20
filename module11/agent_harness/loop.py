"""
loop.py
=======
The core `Agent` class -- this is the packaged, reusable version of the
tool-calling loop and registry from Modules 1-3, now wired together with
Module 11's cost tracking and caching concerns.

This intentionally keeps a SUBSET of the full course's features. Memory
compression, planning, reflection/retries, confirmation gates, tracing,
and multi-agent orchestration remain examples in their respective modules;
they are advanced compositions you can layer on top of this core Agent.
"""

from .config import get_client, MODEL, LLM_OPTIONS
from .tools import TOOL_REGISTRY, TOOLS_SCHEMA, execute_tool_call
from .cost import CostTracker
from .cache import SimpleCache


class Agent:
    """
    A reusable agent with its own system prompt, tool subset, cost tracker,
    and cache. Multiple Agent instances can coexist in the same process
    (e.g. a "researcher" Agent and a "writer" Agent, echoing Module 10),
    each with independent cost/cache accounting.
    """

    def __init__(self, system_prompt: str, tools_schema: list = None,
                 tool_registry: dict = None, max_turns: int = 8,
                 use_cache: bool = True):
        self.system_prompt = system_prompt
        # Default to the full globally-registered toolset if none specified,
        # so a quick `Agent(system_prompt="...")` just works out of the box.
        self.tools_schema = tools_schema if tools_schema is not None else TOOLS_SCHEMA
        self.tool_registry = tool_registry if tool_registry is not None else TOOL_REGISTRY
        self.max_turns = max_turns
        self.client = get_client()
        self.cost = CostTracker()
        self.cache = SimpleCache() if use_cache else None

    def _call_llm(self, messages: list):
        """Wraps the raw API call with caching and cost tracking."""
        if self.cache is not None:
            cached = self.cache.get(MODEL, messages, self.tools_schema)
            if cached is not None:
                print("    [CACHE] hit -- reusing previous response, no API call made.")
                return cached

        response = self.client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=self.tools_schema if self.tools_schema else None,
            **LLM_OPTIONS,
        )
        self.cost.record(response.usage)

        if self.cache is not None:
            self.cache.set(MODEL, messages, self.tools_schema, response)

        return response

    def run(self, user_task: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_task},
        ]

        for turn in range(1, self.max_turns + 1):
            print(f"[Agent] turn {turn}: sending {len(messages)} messages...")
            response = self._call_llm(messages)
            message = response.choices[0].message

            if message.tool_calls:
                messages.append(message)
                for tool_call in message.tool_calls:
                    print(f"[Agent] turn {turn}: calling tool "
                          f"'{tool_call.function.name}'")
                    tool_result = execute_tool_call(
                        tool_call.function.name,
                        tool_call.function.arguments,
                        registry=self.tool_registry,
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": tool_result,
                    })
                continue

            print(f"[Agent] turn {turn}: final answer produced.")
            return message.content

        return "(Agent did not finish within the turn limit.)"

    def stats(self) -> str:
        """Convenience summary combining cost and cache stats for logging."""
        cache_summary = self.cache.summary() if self.cache else "caching disabled"
        return f"{self.cost.summary()} | {cache_summary}"
