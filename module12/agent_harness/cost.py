"""
cost.py
=======
COST MONITORING.

Every LLM API call has a token cost. Across a long agentic run (many turns,
many tool calls, each re-sending growing conversation history) costs add
up fast and invisibly if nobody is tracking them. CostTracker accumulates
token usage from each API response's `usage` field and estimates a dollar
cost, so you can log/alert on it (e.g. "abort this run if it exceeds $0.50").
"""

from .config import PRICE_PER_1K_TOKENS


class CostTracker:
    def __init__(self):
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.call_count = 0

    def record(self, usage):
        """
        `usage` is the `.usage` object returned on a chat completion
        response (has .prompt_tokens and .completion_tokens on the
        OpenAI SDK; Ollama's OpenAI-compat mode returns the same shape).
        Some local/self-hosted providers may not return usage at all --
        we handle that gracefully rather than crashing cost tracking.
        """
        # This method is called only after a real (non-cached) LLM request,
        # so count the call even when a provider omits token-usage metadata.
        self.call_count += 1
        if usage is None:
            return
        self.total_input_tokens += getattr(usage, "prompt_tokens", 0) or 0
        self.total_output_tokens += getattr(usage, "completion_tokens", 0) or 0

    @property
    def estimated_cost_usd(self) -> float:
        input_cost = (self.total_input_tokens / 1000) * PRICE_PER_1K_TOKENS["input"]
        output_cost = (self.total_output_tokens / 1000) * PRICE_PER_1K_TOKENS["output"]
        return round(input_cost + output_cost, 6)

    def summary(self) -> str:
        return (
            f"{self.call_count} LLM call(s), "
            f"{self.total_input_tokens} input + {self.total_output_tokens} output tokens, "
            f"~${self.estimated_cost_usd:.6f} estimated cost"
        )
