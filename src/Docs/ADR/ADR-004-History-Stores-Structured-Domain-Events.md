# ADR-004: History Stores Structured Domain Events

## Status

Accepted

---

## Context

The framework requires a complete and queryable record of every execution.

A simple list of event names (for example, `"TaskStarted"` or `"PlanCreated"`) is sufficient for logging, but it does not preserve the contextual information needed for debugging, tracing, replaying executions, or future observability features.

As the framework evolves, each event will need to carry metadata specific to what occurred.

---

## Decision

History will store **structured domain events** represented as classes rather than plain strings.

Every event inherits from a common `Event` base class containing shared metadata such as:

* `execution_id`
* `timestamp`

Each concrete event may include additional fields relevant to that event.

Examples:

* `TaskStarted(step_id)`
* `TaskCompleted(step_id)`
* `ExecutionFinished(success)`

These events are **not** used for inter-component communication or triggering execution. They exist solely to record what has already happened during an execution.

---

## Rationale

The purpose of these events is historical recording rather than message passing.

Using structured event objects provides:

* Rich contextual information.
* Strong typing.
* Easier querying and filtering.
* Support for replay and debugging.
* Extensibility without changing the History interface.

For example, querying all completed tasks becomes a simple type-based operation rather than parsing strings.

---

## Consequences

### Advantages

* Preserves complete execution metadata.
* Enables execution replay.
* Simplifies debugging and tracing.
* Supports future observability dashboards.
* Easy to extend by introducing new event types.
* Promotes a strongly typed domain model.

### Disadvantages

* Slightly more code than storing plain event names.
* Requires defining event models as the framework grows.

---

## Alternatives Considered

### Store Event Names as Strings

Example:

```text
["GoalReceived", "PlanCreated", "TaskStarted"]
```

**Rejected because:**

* Cannot associate metadata with individual events.
* Difficult to filter or analyze execution history.
* Becomes fragile as more event types are introduced.
* Does not scale to production observability.

### Use Pub/Sub Events

Publish events through an event bus and let other components consume them.

**Rejected because:**

The framework's `History` is not an event-driven messaging system.

Its responsibility is to maintain an immutable execution record, not to coordinate asynchronous communication between components.

---

## Notes

These are **Domain Events**, not **Integration Events**.

* **Domain Events** describe facts that have already occurred and are stored in `History`.
* **Integration (Pub/Sub) Events** notify other systems that work should begin.

The framework uses Domain Events to support replayability, debugging, tracing, and evaluation while keeping execution flow under the sole control of the Orchestrator.
