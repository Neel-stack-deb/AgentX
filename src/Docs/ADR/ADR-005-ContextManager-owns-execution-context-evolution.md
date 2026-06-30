# ADR-005: ContextManager Owns ExecutionContext Evolution

## Status

Accepted

---

## Context

`ExecutionContext` is immutable. After every node execution, a new version of the context must be created.

Allowing each node or the Orchestrator to update the context directly would mix execution flow with state management and lead to duplicated update logic.

---

## Decision

A dedicated `ContextManager` is responsible for creating new versions of `ExecutionContext`.

Nodes return domain results only.

The Orchestrator controls execution flow.

The `ContextManager` applies node results and produces the next immutable `ExecutionContext`.

---

## Consequences

### Advantages

* Single source of truth for state evolution.
* Keeps the Orchestrator focused on execution flow.
* Nodes remain pure reasoning components.
* Makes adding new node types straightforward.

### Disadvantages

* Introduces one additional abstraction.
* All state transitions must be implemented in the `ContextManager`.

---

## Notes

Responsibilities are clearly separated:

* **Nodes** → Produce results.
* **ContextManager** → Evolves execution state.
* **Orchestrator** → Controls execution flow.
