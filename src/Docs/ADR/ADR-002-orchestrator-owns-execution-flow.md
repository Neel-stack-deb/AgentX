# Orchestrator Owns Execution Flow

## Context

Multiple components need to coordinate execution.

If nodes call each other directly,
the execution graph becomes difficult to understand.

## Decision

Only the Orchestrator schedules nodes.

Nodes never invoke other nodes.

## Consequences

Pros

- Single source of truth
- Easy retries
- Easy replanning
- Easy graph execution

Cons

- Slightly more orchestration code