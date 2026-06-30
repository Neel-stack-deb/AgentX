from pydantic import ValidationError
from Core import ExecutionContext
from Types import (
    ExecuterResult,
    NodeResult,
    PlannerResult,
    ReflectorResult,
    TaskExecution,
)


class ExecutionContextManager:

    def __init__(self) -> None:
        self.handlers: {
            PlannerResult: self._apply_planner,
            ExecuterResult: self._apply_executer,
            ReflectorResult: self._apply_reflector,
        }

    def apply(self, context: ExecutionContext, result: NodeResult) -> ExecutionContext:
        handler = self.handlers.get(type(result))
        if handler is None:
            raise ValueError(f"No handler registered for {type(result).__name__}")
        return handler(context, result)

    def _apply_planner(
        self, context: ExecutionContext, result: PlannerResult
    ) -> ExecutionContext:
        try:
            return context.model_copy(
                update={"plan": result.plan}, force_validation=True
            )

        except ValidationError as validationError:
            print(
                f"[VALIDATION FAILED] validation failed at creating the new instance of ExecutionContext at the planner handler, No new instance created:\n{validationError}"
            )

    def _apply_executer(
        self, context: ExecutionContext, result: ExecuterResult
    ) -> ExecutionContext:
        task_execution = TaskExecution(
            step_id=result.step.step_id,
            current_response=result.executionResponse,
            current_reflection=None,
        )
        try:
            return context.model_copy(
                update={"current_task_execution": task_execution}, force_validation=True
            )
        except ValidationError as validationError:
            print(
                f"[VALIDATION FAILED] validation failed at creating the new instance of ExecutionContext at the executer handler, No new instance created:\n{validationError}"
            )

    def _apply_reflector(
        self,
        context: ExecutionContext,
        result: ReflectorResult,
    ) -> ExecutionContext:

        old_execution = context.current_task_execution

        updated_execution = TaskExecution(
            step_id=old_execution.step_id,
            current_response=old_execution.current_response,
            current_reflection=result.reflection,
        )

        try:
            return context.model_copy(
                update={"current_task_execution": updated_execution},
                force_validation=True,
            )
        except ValidationError as validationError:
            print(
                f"[VALIDATION FAILED] validation failed at creating the new instance of ExecutionContext at the reflector handler, No new instance created:\n{validationError}"
            )
