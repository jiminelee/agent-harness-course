"""
prompts.py
==========
PROMPT VERSIONING.

Throughout this course, system prompts were just string constants at the
top of a file. That's fine for a demo, but in production, prompts change
over time (you tweak wording to fix a bug or improve behavior), and you
NEED to know exactly which prompt version produced which agent run --
especially when debugging a regression ("this broke after we changed the
prompt on Tuesday").

PromptRegistry stores multiple named, versioned prompts and always
returns both the text AND its version tag together, so callers can log
"this run used prompt researcher_v3" alongside the rest of the trace
(see Module 10's Tracer -- pairing prompt version with trace events is
exactly how you'd correlate a regression with a specific prompt change).
"""


class PromptRegistry:
    def __init__(self):
        # name -> {version -> text}
        self._prompts = {}
        # name -> currently active version (what get() returns by default)
        self._active_version = {}

    def register(self, name: str, version: str, text: str, activate: bool = True):
        self._prompts.setdefault(name, {})[version] = text
        if activate or name not in self._active_version:
            self._active_version[name] = version

    def get(self, name: str, version: str = None) -> tuple:
        """
        Returns (text, version). If version is omitted, returns the
        currently active version for that prompt name.
        """
        version = version or self._active_version[name]
        return self._prompts[name][version], version

    def set_active(self, name: str, version: str):
        if version not in self._prompts.get(name, {}):
            raise ValueError(f"Unknown version '{version}' for prompt '{name}'")
        self._active_version[name] = version


# A default, ready-to-use registry with one example prompt versioned twice,
# to demonstrate the pattern. Real projects would register their own.
default_registry = PromptRegistry()

default_registry.register(
    name="general_assistant",
    version="v1",
    text="You are a helpful assistant with access to tools.",
    activate=False,
)
default_registry.register(
    name="general_assistant",
    version="v2",
    text="You are a helpful assistant with access to tools. Use tools "
         "whenever a task requires up-to-date information or precise "
         "calculation -- do not guess numbers.",
    activate=True,  # v2 is the current default
)
