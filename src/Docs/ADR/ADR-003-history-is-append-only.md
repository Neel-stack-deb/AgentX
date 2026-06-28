# ADR-003: History is Append-Only

## Status

Accepted

---

## Context

The framework needs to preserve a complete record of every execution for debugging, tracing, replayability, evaluation, and observability.

During execution, plans may change, tasks may be retried, reflections may request replanning, and artifacts may be regenerated. Overwriting previous records would destroy valuable information about how and why the agent reached a particular outcome.

---

## Decision

`History` will be **append-only**.

No existing event or artifact may be modified or deleted after it has been recorded.

Every significant action performed by the framework will create a new history entry.

Examples include:

* Goal received
* Plan created
* Task started
* Task completed
* Reflection completed
* Replan requested
* Execution finished

Heavy outputs such as generated code, tool results, reports, or summaries will be stored as **Artifacts**. Lightweight metadata describing execution will be stored as **Events**.

The current execution state is represented by `ExecutionContext` and `RuntimeContext`, while `History` serves as the immutable record of everything that has occurred.

---

## Rationale

Making History append-only provides several architectural benefits:

* Enables deterministic replay of an execution.
* Supports time-travel debugging by reconstructing any previous state.
* Preserves every intermediate decision instead of only the final outcome.
* Simplifies observability and tracing.
* Allows future evaluation metrics to analyze complete execution histories.
* Enables comparison between multiple replanning attempts.

History becomes the "black box flight recorder" of the framework.

---

## Consequences

### Advantages

* Complete audit trail.
* Easier debugging.
* Supports replay and simulation.
* Enables production-grade observability.
* Makes evaluation and benchmarking possible.
* Prevents accidental loss of execution information.

### Disadvantages

* Storage usage increases over time.
* Long-running executions may require history compression or archival.
* Additional mechanisms may be needed to efficiently query historical records.

---

## Alternatives Considered

### Mutable History

Update existing records whenever execution changes.

**Rejected because:**

* Previous execution states are lost.
* Replay becomes impossible.
* Difficult to understand why decisions changed.
* Debugging becomes significantly harder.

---

## Notes

History is **not** the source of truth for the current execution.

* **ExecutionContext** stores the current reasoning state.
* **RuntimeContext** stores the current execution state.
* **History** stores everything that has happened.

This separation keeps the framework deterministic, debuggable, and extensible as features such as memory, RAG, graph execution, and multi-agent collaboration are introduced.
