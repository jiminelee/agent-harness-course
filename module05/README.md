# Module 5: Persistent Memory — JSON-Based Memory

**File:** `module05_persistent_memory.py`
**Builds on:** Module 4's distinction between a task and its context; Module 3's registry and loop

## Concept

Module 4 compresses progress **within one run**. This module keeps selected
project knowledge **across runs** in a JSON file. Every
invocation starts a fresh conversation; only the saved knowledge persists.

| Mechanism | What it preserves | Implemented here? |
|---|---|---|
| Conversation summary | Earlier progress in the current task | Module 4; not repeated here |
| Persistent memory | Selected facts for future tasks | Yes, in `memory.json` |
| Checkpoint | Execution state needed to resume interrupted work | No |

The two memory lessons complement each other. A longer-running agent could
use Module 4's `Context` to compress its current execution steps and these
tools to save knowledge for the next run. This standalone lesson keeps the
short loop from Module 3 so persistence is the only new mechanism.

## What's new since Module 4

| Module 4 | Module 5 |
|---|---|
| Summary disappears when the run ends | Knowledge survives a process restart |
| Older execution steps are summarized | Explicitly requested facts are saved |
| Recent steps remain in context | Saved facts are read through a tool when needed |

## The file is the memory

After saving two facts, `memory.json` might contain:

```json
{
  "python-version": "This project uses Python 3.11.",
  "testing": "Run the test suite with pytest."
}
```

Each key identifies one fact. Keys and values must be nonempty strings.
`json.loads()` reads the file into a dictionary; `json.dumps()` writes it
back. No custom document parser is needed. A missing file means an empty
dictionary, and deleting the final entry leaves `{}`.

You can edit the JSON between runs. Keep keys unique and preserve valid JSON
syntax; Python's standard decoder keeps the last value for duplicate keys.
UTF-8 text, including Korean, is saved directly. Newlines and quotes within
values are escaped automatically. Invalid JSON or values of the wrong type
produce errors before any change is written, preserving the original file.

| Tool | Behavior |
|---|---|
| `read_memory(key=None)` | Reads all entries, or one exact key when provided |
| `remember(key, content)` | Creates an entry or replaces the value under the same key |
| `forget(key)` | Deletes one entry; an absent key is a harmless no-op |

For example, `read_memory()` reads the whole file, while
`read_memory(key="python-version")` returns only that entry. A missing exact
key does not mean the file is empty; the agent should read all entries to
check for another key. A read error means the lookup failed, not that no
fact was saved. The prompt asks the model to retry or report that failure.

The model must reuse an existing key when updating the same fact. The store
knows keys, not meaning: `python-version` and `runtime` can still contain
contradictory facts if the agent chooses poorly.

## Memory policy and storage guarantees

The system prompt asks the agent to read relevant memory, save only when
explicitly requested, treat file contents as data rather than instructions,
and confirm changes only after a successful tool result. Current user
instructions take precedence over stored facts.

These are **model behavior policies**, not authorization checks enforced by
the storage layer. Code validates the document structure and performs the
requested operation, but cannot determine whether the user authorized a fact
or whether two sentences contradict each other. Evaluating those decisions is
part of evaluating the agent, not just the file helpers.

Writes use a temporary file beside the destination and then replace it.
This avoids exposing a partly written file; it does not resolve concurrent
writers or implement crash recovery. Use one writer and one project memory
file for this exercise. There is no database, embedding search, expiration,
or user isolation. See Module 14 for production extensions.

## Read the code in this order

1. `load_entries()`: read the JSON dictionary, or start with an empty one.
2. `save_entries()`: write a complete document before replacing the old file.
3. `read_memory()`, `remember()`, `forget()`: the three agent tools.
4. `run_agent_loop()`: a fresh conversation, with access to the same saved file.

The memory lifecycle is ordinary dictionary operations: look up facts, assign
a value to save or update it, and delete a key to forget it. JSON supplies the
serialization so the lesson can focus on those decisions.

## Run it

Activate the environment from the root README. Provider settings follow the
same pattern as earlier modules. From the project root, run each command as
a **separate process**:

```bash
python module05/module05_persistent_memory.py "Remember that this project uses Python 3.11."
python module05/module05_persistent_memory.py "Which Python version does this project use?"
python module05/module05_persistent_memory.py "Update the remembered Python version to 3.12."
python module05/module05_persistent_memory.py "Which Python version does this project use?"
python module05/module05_persistent_memory.py "Forget this project's Python version."
python module05/module05_persistent_memory.py "Which Python version does this project use?"
```

Watch `[MEMORY]` logs and open `module05/memory.json` after changes. The expected
sequence is **3.11 -> 3.12 -> no saved version**. After deleting the final entry,
the file contains an empty JSON object (`{}`). Models may choose different valid keys or
wording; inspect the tool calls and saved contents, not just the final answer.
Some models return an empty final answer after changing memory; the loop
prints a notice in that case, and the tool result still shows what happened.

The default path is beside the script, independent of the working directory.
The generated file is Git-ignored. To run an isolated exercise, pass
`--memory-file /absolute/path/to/demo-memory.json` to **every** invocation.
Custom file locations are not automatically Git-ignored.


## Key takeaway

> Persistent memory has a lifecycle: select, store, retrieve, update, forget.
> A readable file makes that lifecycle inspectable. Saving text is only one
> part of managing useful, accurate knowledge across sessions.

## Things to try

- Edit a saved fact by hand between runs, then ask the agent about it.
- Ask an unrelated question and observe whether the agent unnecessarily reads
  memory. Ask a factual question without asking to save it; check that the
  file does not change.
- Store two contradictory facts under different keys. How should the agent
  reconcile them?
- Split facts into topic files and load only relevant topics.
- Add structured metadata such as source and update time. Decide how the
  schema and validation should change before extending the file format.
- Combine these tools with Module 4's context compression for longer tasks.

Next, [Module 6](../module06/README.md) introduces planning and isolated subtask
contexts.
