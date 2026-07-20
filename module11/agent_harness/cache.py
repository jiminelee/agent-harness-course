"""
cache.py
========
CACHING STRATEGY.

If the exact same (model, messages, tools) combination is sent twice --
which happens more than you'd expect, e.g. during development when you
re-run the same test task repeatedly -- there's no reason to pay for and
wait on a second identical LLM call. SimpleCache stores responses keyed by
a hash of the request, so repeat requests are served instantly for free.

This is an IN-MEMORY cache for teaching purposes (cleared when the process
exits). A real production system would likely use Redis or a similar
persistent store so the cache survives restarts and is shared across
multiple worker processes.
"""

import hashlib
import json


class SimpleCache:
    def __init__(self):
        self._store = {}
        self.hits = 0
        self.misses = 0

    def _make_key(self, model: str, messages: list, tools: list) -> str:
        """
        Builds a stable hash key from the request contents. We serialize
        messages/tools to JSON first (sorting keys for determinism) so
        logically-identical requests always hash to the same key.
        """
        # Note: `messages` may contain SDK message objects (not just plain
        # dicts) once tool calls have happened in a conversation -- we
        # convert defensively so json.dumps doesn't choke.
        def to_plain(m):
            if isinstance(m, dict):
                return m
            return {"role": m.role, "content": m.content,
                     "tool_calls": str(getattr(m, "tool_calls", None))}

        payload = json.dumps(
            {"model": model, "messages": [to_plain(m) for m in messages], "tools": tools},
            sort_keys=True,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, model: str, messages: list, tools: list):
        key = self._make_key(model, messages, tools)
        if key in self._store:
            self.hits += 1
            return self._store[key]
        self.misses += 1
        return None

    def set(self, model: str, messages: list, tools: list, response):
        key = self._make_key(model, messages, tools)
        self._store[key] = response

    def summary(self) -> str:
        total = self.hits + self.misses
        rate = (self.hits / total * 100) if total else 0
        return f"{self.hits} hit(s), {self.misses} miss(es) ({rate:.0f}% hit rate)"
