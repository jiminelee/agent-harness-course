"""
config.py
=========
Single source of truth for provider configuration. Every module in this
course repeated these three lines at the top of the file -- packaging them
here means changing providers (OpenAI <-> Ollama <-> anything else
OpenAI-compatible) now happens in exactly ONE place for your whole project.
"""

from openai import OpenAI

# Change these three values to switch providers. Everything else in this
# library is written against the OpenAI-compatible protocol, so no other
# code needs to change.
BASE_URL = "http://localhost:11434/v1"   # e.g. "https://api.openai.com/v1" for real OpenAI
API_KEY = "ollama"                        # e.g. your real OpenAI key
MODEL = "gemma4:e4b"                       # e.g. "gpt-4o-mini"

# `reasoning_effort` is not universal across OpenAI-compatible providers.
# The course's default Ollama configuration accepts it; OpenAI requests omit it.
LLM_OPTIONS = {"reasoning_effort": "none"} if API_KEY == "ollama" else {}

# A rough per-1K-token price table, used by cost.py for estimated cost
# tracking. These are illustrative placeholder numbers -- always check your
# actual provider's current pricing page for real values.
PRICE_PER_1K_TOKENS = {
    "input": 0.00015,
    "output": 0.0006,
}

_client = None


def get_client() -> OpenAI:
    """
    Returns a single shared client instance (simple singleton pattern) so
    the whole application reuses one HTTP connection pool instead of
    creating a new client every time an agent is instantiated.
    """
    global _client
    if _client is None:
        _client = OpenAI(base_url=BASE_URL, api_key=API_KEY)
    return _client
