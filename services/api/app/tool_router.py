from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolResult:
    name: str
    summary: str
    payload: dict[str, Any]


ToolFunction = Callable[[dict[str, Any]], ToolResult]


class ToolRouter:
    def __init__(self) -> None:
        self._tools: dict[str, ToolFunction] = {}

    def register(self, name: str, func: ToolFunction) -> None:
        if not name.replace("_", "").isalnum():
            raise ValueError(f"invalid tool name: {name}")
        self._tools[name] = func

    def names(self) -> list[str]:
        return sorted(self._tools)

    def call(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        if name not in self._tools:
            raise KeyError(f"tool not registered: {name}")
        return self._tools[name](arguments)


def create_default_tool_router() -> ToolRouter:
    router = ToolRouter()

    def retrieve_profile_context(arguments: dict[str, Any]) -> ToolResult:
        query = str(arguments.get("query", ""))
        return ToolResult(
            name="retrieve_profile_context",
            summary=f"Retrieved local profile context for query: {query[:60]}",
            payload={"query": query, "source": "local_profile"},
        )

    def plan_next_question(arguments: dict[str, Any]) -> ToolResult:
        stage = str(arguments.get("stage", "warmup"))
        return ToolResult(
            name="plan_next_question",
            summary=f"Planned next question for stage: {stage}",
            payload={"stage": stage, "question_type": "mechanism_followup"},
        )

    router.register("retrieve_profile_context", retrieve_profile_context)
    router.register("plan_next_question", plan_next_question)
    return router
