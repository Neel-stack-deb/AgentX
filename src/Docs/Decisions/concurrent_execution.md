# The creation of Runtime Context

execution_id uniquely identifies one complete run of the agent.

## Example:

  User: "Build a calculator"

### Execution #1 (ID: abc123)
   Plan created
   Step 1 completed
   Step 2 failed

### Execution #2 (ID: xyz789)
   New plan
   All steps completed

#### Without an execution_id, you can't reliably:

- Separate concurrent executions.
- Group events and artifacts belonging to the same run.
- Replay or debug a specific execution.
- Trace logs in production.

### with this id we can separate the concerns each execurtion instance wise for each goal 