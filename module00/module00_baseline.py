"""
Module 0: Why a Harness? (Baseline -- No Loop, No Tools)
===========================================================
Goal: Before we build any "agent" machinery, let's see what a plain LLM
call looks like on its own -- a single request, a single response, done.
This is the BASELINE that every later module builds on top of.

Notice everything this script CANNOT do:
  - It cannot have a multi-turn conversation (Module 1 adds a loop).
  - It cannot use any tools -- if you ask it to do real-time math or
    look something up, it can only guess from its training data
    (Module 2 adds real tool calling).
  - It has no memory of anything beyond this one exchange.

This is exactly the gap a "harness" exists to fill: the LLM call itself
never changes much across the rest of the course -- what changes is the CODE
we wrap around it (the harness).

This script uses the OpenAI-compatible client, so -- like every other
module in this course -- it works unmodified against OpenAI's real API
or a local Ollama server, just by changing the three config values below.
"""

from openai import OpenAI

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
# Example 1: OpenAI's real API
#   BASE_URL = "https://api.openai.com/v1"
#   API_KEY  = "sk-..."
#   MODEL    = "gpt-4o-mini"
#
# Example 2: Local Ollama (OpenAI-compatible endpoint at /v1)
#   BASE_URL = "http://localhost:11434/v1"
#   API_KEY  = "ollama"       # dummy value, Ollama ignores it
#   MODEL    = "gemma4:e4b"   # any model you've pulled with `ollama pull`

BASE_URL = "http://localhost:11434/v1"
API_KEY = "ollama"
MODEL = "gemma4:e4b"

# `reasoning_effort` is not supported by every OpenAI-compatible model.
# The default Ollama setup accepts it; real OpenAI/non-Ollama providers omit it.
LLM_OPTIONS = {"reasoning_effort": "none"} if API_KEY == "ollama" else {}

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)


def ask_llm_once(user_message: str) -> str:
    """
    The simplest possible LLM interaction: one message in, one message out.
    No history is kept, no follow-up happens, no tools are offered.
    """
    print(f"\n{'=' * 60}")
    print("[SINGLE CALL] Sending one message to the LLM (no loop, no tools)...")
    print(f"{'=' * 60}")
    print(f"REQUEST: {user_message}")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": user_message},
        ],
        **LLM_OPTIONS,
    )

    reply = response.choices[0].message.content
    print(f"RESPONSE: {reply}")
    return reply


if __name__ == "__main__":
    # Try a factual/reasoning question first -- this works fine with a
    # single call, no harness needed.
    ask_llm_once("In one sentence, what is an 'agent harness'?")

    # Now try something that exposes the limits of a single call: real-time
    # arithmetic. Without a tool, the model can only guess/compute mentally
    # (unreliable for anything non-trivial) -- there is no way for it to
    # actually run code. Watch this in Module 2, where a real calculator
    # tool fixes this.
    ask_llm_once("What is 384712 * 9931? Just compute it directly.")

    # And this exposes the "no memory" limitation: the model has no idea
    # what was asked a moment ago, because we never kept a message history.
    ask_llm_once("What did I just ask you in my previous message?")
