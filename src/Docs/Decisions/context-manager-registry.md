# Why ContextManager Uses a Registry

Instead of checking every possible result type with a long chain of `if isinstance(...)`, the `ContextManager` uses a registry that maps a result type to its corresponding handler.

Example:

```python
handlers = {
    PlannerResult: self._apply_planner,
    ExecutorResult: self._apply_executor,
    ReflectorResult: self._apply_reflector,
}
```

When a node returns a result, the `ContextManager` simply looks up the appropriate handler and applies it.

## Why not use `if isinstance()`?

While an `if-elif` chain works for a small number of node types, it becomes difficult to maintain as the framework grows.

Future modules will introduce additional results such as:

* RetrieverResult
* MemoryResult
* ToolResult
* EvaluatorResult
* BrowserResult
* ResearchResult

With a registry, adding support for a new result only requires registering a new handler. Existing code remains unchanged.

## Benefits

* Easier to extend.
* Cleaner implementation.
* Follows the **Open/Closed Principle**.
* Decouples result types from the dispatching logic.
* Makes the framework scalable as new node types are introduced.

The registry makes the `ContextManager` responsible only for dispatching to the correct handler, while each handler remains responsible for a single state transition.
