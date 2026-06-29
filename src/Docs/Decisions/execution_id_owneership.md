# Execution ID Ownership

## Principle

Only objects that can exist **independently of the current execution state** should store an `execution_id`.

Objects that are part of the current execution already belong to an `ExecutionContext` and therefore do not need to duplicate this information.

---

## Models That Own `execution_id`

### RuntimeContext

Represents the currently running execution.

```text
RuntimeContext
├── execution_id
├── current_node
├── retry_count
└── status
```

---

### Event

Events are stored in `History` and may be queried long after execution finishes.

```text
Event
├── execution_id
└── timestamp
```

---

### Artifact

Artifacts are also stored independently in `History`.

```text
Artifact
├── artifact_id
├── execution_id
└── created_at
```

---

## Models That Do NOT Need `execution_id`

These models are owned by `ExecutionContext` and therefore already belong to a specific execution.

* Goal
* Plan
* PlanStep
* TaskExecution
* Reflection
* ExecutionResponse
* Scratchpad
* ExecutionContext

Adding `execution_id` to these models would duplicate information without providing additional value.

---

## Ownership Hierarchy

```text
RuntimeContext (execution_id)
        │
        ├── ExecutionContext
        │     ├── Goal
        │     ├── Plan
        │     ├── TaskExecution
        │     └── Scratchpad
        │
        └── History
              ├── Events (execution_id)
              └── Artifacts (execution_id)
```

---

## Guideline

Ask the following question before adding an `execution_id` to a model:

> **Can this object be stored, queried, or exist independently of the current `ExecutionContext`?**

* **Yes** → Store `execution_id`.
* **No** → Let ownership determine the execution and avoid duplicating the identifier.
