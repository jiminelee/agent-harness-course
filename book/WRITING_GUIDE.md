# Writing Guide

This guide is for people writing or revising the companion book. Readers don't
need it; the book's [README](README.md) is the place to start reading.

---

## Chapter Template

Every chapter from 0 to 13 follows this order, so readers always know where
they are. Chapter 14 has no code and uses a looser structure. The Chapter 2
pilot is the reference example.

1. **What You'll Learn** — at most three goals, prerequisites, and the relevant code file
2. **The Problem** — a scene where the previous chapter's code *actually* falls short (a real run log when possible)
3. **The Big Idea** — an analogy and a diagram first, no code yet
4. **Walking Through the Code** — excerpts of *only what changed* since the last chapter, with file paths and line numbers
5. **Running It** — the command, the real output, and a line-by-line reading of that output
6. **Common Problems** — where beginners get stuck, and how to get unstuck
7. **Try It Yourself** — three to five exercises, easiest first
8. **Recap** — one key sentence and a bridge to the next chapter

Each chapter ends with a short "Solutions and Hints" section that links to the
chapter's entry in [Appendix D](appendices/appendix-d-solutions.md). Solutions
live only in Appendix D, so they can't drift out of sync with a second copy.

## Writing Guidelines

- **Only real run logs.** Note the run date, model, and SDK version next to each
  log, and remind readers that model output varies from run to run. If a run
  was set up to force a behavior (for example, a forced first answer), say so.
- **The repository code is the source of truth.** Label every excerpt with its
  source, e.g. `module02/module02_first_tool.py:49-67`, and say what was left
  out (comments, docstrings, prints). When the code changes, update the
  excerpts and line numbers too.
- **Voice and spelling.** American English, second person ("you"), friendly but
  precise. Define a term the first time it appears, and add it to
  [Appendix A](appendices/appendix-a-glossary.md). Code identifiers
  (`tool_calls`, `messages`) stay in code formatting.
- **Don't overclaim.** Say "you can't *trust* the model's arithmetic," not
  "the model can't do arithmetic." Match what was actually observed, and give
  counts ("2 of 2 runs") when behavior varies.
- **Teach the failures.** When a run exposes a real weakness in a module, show
  it and explain it rather than hiding it. Unless the module code is changed,
  the weakness becomes a lesson and, ideally, an exercise.
- **Format.** Markdown with Quarto-compatible syntax: `::: {.callout-...}`
  blocks and plain ` ```mermaid ` diagrams. It reads on GitHub and builds into an
  HTML book with Quarto. Avoid semicolons inside Mermaid text; they end a
  statement.

## Keeping the Book in Sync

When you add or revise a chapter:

- Add new errors to [Appendix B](appendices/appendix-b-common-errors.md) and new
  terms to [Appendix A](appendices/appendix-a-glossary.md).
- Put the exercise solutions in Appendix D under the chapter's heading.
- Check that "Section X.Y" references point to headings that exist.
- Check that every relative link resolves.
- Check that each excerpted code line still appears in the cited line range.
- Rebuild with `quarto render` from the `book/` folder, and confirm that the
  callouts and diagrams display.

When a module's code changes, re-run it, replace the affected logs (with a new
date and versions), and update the chapter's excerpts, explanations, and
Appendix D answers.
