# Result Objects Should Carry Their Own Context

## Problem

Initially, `ExecutorResult` only returned the execution response.

```python
ExecutorResult
├── response
```

The `ExecutionContextManager` then attempted to determine which `PlanStep` had been executed by calling:

```python
context.plan.next_pending_step()
```

This required the `ExecutionContextManager` to infer information that the `Executor` already knew.

---

## Decision

Each `NodeResult` should carry all of the information produced by that node.

For the `Executor`, this means returning the executed step along with the response.

Example:

```python
ExecutorResult
├── step
└── response
```

or at minimum

```python
ExecutorResult
├── step_id
└── response
```

---

## Rationale

The component that performs an action has the most accurate knowledge of what happened.

Another component should never have to rediscover or infer that information from the current state.

This avoids incorrect assumptions and makes the framework more robust as execution becomes more complex.

---

## Guiding Principle

> **The component that knows a fact should communicate that fact. Never make another component rediscover it.**

This keeps responsibilities clear:

* **Executor** → Knows what it executed.
* **ExecutionContextManager** → Applies the result to create the next immutable `ExecutionContext`.
* **Orchestrator** → Controls execution flow.
