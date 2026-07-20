"""
example_usage.py
================
This is what USING the packaged core looks like from a brand new project's
point of view -- contrast this with Module 1's standalone loop. The basic
loop, tools, error handling, cost tracking, caching, and prompt registry
are available behind a small interface. Advanced features from Modules
4-10 remain separate examples that can be composed on top of this core.

Run this file from the project root with `python module11/example_usage.py`.
The `agent_harness/` package lives next to this script.
"""

from agent_harness import Agent, tool, PromptRegistry
from agent_harness.prompts import default_registry

# ---------------------------------------------------------------------------
# Registering a brand-new custom tool is just a decorator -- no need to
# touch loop.py, cache.py, or anything else in the library.
# ---------------------------------------------------------------------------
@tool(
    description="Convert a temperature from Celsius to Fahrenheit.",
    parameters={"celsius": {"type": "number", "description": "Temperature in Celsius."}},
    required=["celsius"],
)
def celsius_to_fahrenheit(celsius: float) -> str:
    return str(celsius * 9 / 5 + 32)


if __name__ == "__main__":
    # Pull a VERSIONED system prompt from the registry (Module 11's prompt
    # versioning) instead of hardcoding a string -- this line alone tells
    # you exactly which prompt text produced this run, for later debugging.
    system_prompt, prompt_version = default_registry.get("general_assistant")
    print(f"Using prompt 'general_assistant' version={prompt_version}")

    # Note: celsius_to_fahrenheit registered itself into the GLOBAL
    # TOOLS_SCHEMA/TOOL_REGISTRY the moment the decorator ran above, so the
    # default Agent() picks it up automatically alongside calculate/search_web.
    agent = Agent(system_prompt=system_prompt)

    task = "Convert 100 Celsius to Fahrenheit, then calculate half of that result."
    print(f"USER TASK: {task}\n")

    answer = agent.run(task)

    print(f"\n{'#' * 60}")
    print("FINAL ANSWER:")
    print(answer)
    print(f"{'#' * 60}")

    # This is the payoff of Module 11: one line gives you full visibility
    # into cost and cache efficiency for this run.
    print(f"\n[STATS] {agent.stats()}")
