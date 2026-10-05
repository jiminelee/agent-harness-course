"""
agent_harness
==============
A small, reusable agent harness core distilled from the course's basic
tool-calling loop. It packages the loop, tool registry, error handling,
cost tracking, caching, and prompt registry so a new project can import
them instead of copy-pasting a script. Advanced course features such as
memory compression, planning, reflection, guardrails, tracing, and multi-
agent orchestration remain separate examples to compose as needed.

Public API:
    from agent_harness import Agent, tool, get_client

    @tool(description="...", parameters={...}, required=[...])
    def my_tool(...): ...

    agent = Agent(system_prompt="...")
    answer = agent.run("do something")
"""

from .config import get_client, MODEL
from .tools import tool, TOOL_REGISTRY, TOOLS_SCHEMA
from .prompts import PromptRegistry
from .cost import CostTracker
from .cache import SimpleCache
from .loop import Agent

__all__ = [
    "get_client", "MODEL",
    "tool", "TOOL_REGISTRY", "TOOLS_SCHEMA",
    "PromptRegistry", "CostTracker", "SimpleCache",
    "Agent",
]
