# Module 13: Roadmap to a Commercial-Grade Agent Harness

This document is for those who have completed Modules 0-12 of the course. It lays out
**what to study further** and **what to change in the code** to take this project from
an educational implementation to something ready for real production use. The course
was designed to teach you the core mechanics by building them yourself; everything
below is what's needed to actually put this in front of real users.

---

## 1. Tool Execution Security (Sandboxing)

**Problem (current code):** The `calculate` tool uses Python's `eval()`, even with a
restricted namespace. `read_file` accesses the filesystem directly. Neither is safe
enough for a real service.

**Study:**
- Code execution isolation like Docker containers
- The principle of least privilege — explicitly scoping each tool's filesystem/network access
- Safe expression parsing libraries (e.g. `asteval`, `simpleeval`) as a replacement for `eval()`

**Change in code:**
- Replace `calculate` with a safe math expression parser
- Run any code-execution tools inside an isolated container/process with strict timeouts and resource limits
- File-access tools should normalize paths (resolve symlinks, realpath) and enforce an allowlisted root directory they can never escape
- Module 12's MCP server is a separate process, not a sandbox. Restrict its
  operating-system permissions and review which discovered tools the host exposes.

---

## 2. Prompt Injection & Content Defense

**Problem:** Module 8 built a human-approval gate, but never addressed **indirect prompt
injection** — malicious instructions hidden inside tool output (search results, file
contents, etc.) that the model might follow as if they were legitimate instructions.

**Study:**
- Prompt injection / indirect injection attack patterns and defenses
- Tool output sanitization (treating external text as untrusted data, not instructions)
- Constitutional AI / system-prompt isolation techniques used by Anthropic/OpenAI
- Content moderation APIs for filtering harmful content

**Change in code:**
- When wrapping tool results in a `role="tool"` message, clearly mark that content as
  *data*, not instructions (e.g. explicit delimiters/warnings)
- Treat external-content tools (web search, file reads) as a lower trust tier, and
  factor that trust level into any dangerous-action approval logic

---

## 3. Robust Error Handling & Retry Strategy

**Problem:** Module 6's retry logic is a simple counter. Real production traffic mixes
network errors, rate limits, timeouts, and more, each needing different handling.

**Study:**
- Exponential backoff with jitter
- The circuit breaker pattern (preventing cascading failures)
- Idempotency (ensuring retries don't duplicate side effects)
- Each provider's (OpenAI, Anthropic, etc.) rate-limit and error-code conventions

**Change in code:**
- Wrap API calls with a library like `tenacity` for backoff+jitter retries
- Distinguish error types (transient network issue vs. permanent auth failure vs. rate
  limit) and apply different strategies to each
- State-changing tools (file writes, payments, etc.) should use idempotency keys to
  prevent duplicate execution on retry
- For MCP, distinguish a tool error result from a failed protocol request or
  disconnected server. Build on Module 12's deadlines with recovery policies;
  do not blindly repeat a call whose side effects may already have happened.

---

## 4. Production-Grade Observability

**Problem:** Module 9's `Tracer` writes to a local JSON file — an educational
implementation, not a production one.

**Study:**
- OpenTelemetry (the standard for distributed tracing)
- Structured logging platforms (Datadog, Honeycomb, Grafana Loki, etc.)
- Metrics/alerting systems (Prometheus + Grafana, or a managed cloud equivalent)
- LLM-specific observability tools (LangSmith, Arize Phoenix, Braintrust, etc.)

**Change in code:**
- Replace `Tracer` with OpenTelemetry spans sent to a central collector
- Set alerting thresholds on error rate, latency, and cost
- Make traces searchable by user/task (currently everything lives in one file)
- Correlate model tool-call IDs with MCP server identity, tool name, latency,
  and outcome so a cross-process failure can be followed end to end.

---

## 5. Evaluation & Regression Testing

**Problem:** This course has no systematic way to measure "is this agent actually
working well." Module 6's critic is real-time self-checking, not a pre-deployment
quality gate.

**Study:**
- LLM evaluation frameworks (OpenAI Evals, promptfoo, DeepEval)
- Golden dataset construction methodology (representative tasks + expected outcomes)
- Automated regression testing (detecting quality drops after prompt/model changes)
- Human-in-the-loop evaluation (using human-graded samples to calibrate automated graders)

**Change in code:**
- Add a deployment gate requiring the agent to hit a minimum score on a golden dataset
  before shipping
- Wire this into Module 11's `PromptRegistry` so every new prompt version automatically
  runs against the eval set

---

## 6. Durable State & Resilience for Long-Running Tasks

**Problem:** All agent state currently lives only in memory (the `messages` list). If
the process dies, any in-progress task is simply gone.

**Study:**
- Workflow orchestration tools with built-in checkpoint/resume support
- Patterns for persisting state to a database (Postgres, Redis)
- Designing for resumable, idempotent execution

**Change in code:**
- Persist the `messages` history and execution state to a database every turn
- On process restart, resume from the last checkpoint instead of starting over
- Especially important for Module 10's long-running multi-agent tasks

---

## 7. Advanced Cost & Performance Management

**Problem:** Module 11's `CostTracker`/`SimpleCache` are single-process, in-memory
implementations.

**Study:**
- Per-user/per-organization budgets and quotas
- Model routing strategies (route simple requests to a cheap model, complex ones to a
  stronger model, automatically)
- Distributed caching (Redis) shared across multiple server instances
- Native prompt caching features offered by providers (Anthropic/OpenAI)

**Change in code:**
- Replace `SimpleCache` with a Redis-backed cache shared across worker processes
- Add a routing layer that assesses request complexity and picks a model accordingly
- Block or alert on requests once a user/org exceeds their cost budget

---

## 8. Scaling Parallel/Distributed Execution

**Problem:** Module 7's async pattern gives you concurrency within a single process.
Serving thousands of concurrent users requires a different architecture entirely.

**Study:**
- Message-queue-based work distribution (Celery, RQ, AWS SQS)
- Horizontally scalable worker architectures
- Backpressure handling — how the system behaves under overload

**Change in code:**
- Move agent execution into a queue consumed by multiple worker processes
- Add priority queuing (e.g. paying users processed first)

---

## 9. Security & Compliance

**Problem:** Legal/security requirements around user data, PII, and audit logs are
entirely untouched in this course.

**Study:**
- PII detection/masking techniques
- Data retention policies and deletion-request handling (e.g. GDPR)
- Secrets management (never hardcoding API keys — use Vault, AWS Secrets Manager, etc.)
- Multi-tenant isolation (ensuring one user's data/execution is never exposed to another)
- Authentication and authorization for remote MCP servers, plus explicit trust
  decisions for server-provided tool descriptions and results

**Change in code:**
- Load `BASE_URL`/`API_KEY` from environment variables or a secrets manager instead of
  hardcoding them (fine for a teaching script, never acceptable in production)
- Add a filtering layer so PII never ends up persisted in logs/traces

---

## 10. UX-Level Considerations

**Problem:** Every module in this course waits for the whole run to finish before
printing a final answer.

**Study:**
- Streaming responses (token-by-token output in real time)
- Partial-result display and progress UI
- Mechanisms for letting a user cancel an in-flight task

**Change in code:**
- Switch to `client.chat.completions.create(..., stream=True)` and forward tokens to
  the frontend as they arrive
- Stream "what the agent is currently doing" to the user even mid-tool-execution
- Implement a cancellation signal that safely interrupts an in-progress loop

---

## 11. Learning to Compare Frameworks

**Problem:** This course deliberately built everything from scratch, without a
framework. In practice, you'll need to decide whether to keep building it yourself or
adopt an existing framework.

**Study:**
- LangGraph (graph-based state management — structurally very close to the concepts in
  this course)
- AutoGen, CrewAI (multi-agent orchestration frameworks)
- Map each framework's features back onto the modules in this course to understand what
  they're actually doing under the hood

**Change in code:**
- Consider a hybrid approach: keep the core logic in `agent_harness/loop.py`, but swap
  out specific pieces (e.g. state-graph management) for a framework like LangGraph
  where it adds real value

---

## Suggested Priority Order

When moving toward production, this order is recommended:

1. **Security first** — Sections 1, 2, 9 (sandboxing, injection defense, secrets
   management) must be solved before anything is exposed to real users
2. **Reliability** — Sections 3, 6 (error handling, state resilience)
3. **Quality assurance** — Section 5 (evaluation/regression testing) — without this,
   you can't know whether any later change is safe
4. **Observability** — Section 4 — you need visibility into what's actually happening
   in production before you can improve the rest
5. **Scale & cost** — Sections 7, 8
6. **UX polish** — Section 10
7. **Architecture reconsideration** — Section 11 (only if needed)

The concepts you learned in Modules 0-12 are the **foundation** for every item above —
whether you end up using a framework or continuing to build it yourself, you won't be
able to understand what that framework is doing internally without having built these
concepts firsthand.
