# ADR-001

## Title

ExecutionContext is Immutable

---

## Status

Accepted

---

## Context

The framework needs predictable execution, replayability,
and easier debugging.

Nodes should never mutate shared state.

---

## Decision

ExecutionContext will be immutable.

Nodes receive a copy.

Nodes return outputs.

The Orchestrator creates a new ExecutionContext.

---

## Consequences

### Pros

- Easy replay
- Time travel debugging
- Deterministic execution
- Easier testing

### Cons

- More object creation
- Slight memory overhead

---