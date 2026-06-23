import pytest

from app.tool_router import ToolResult, ToolRouter, create_default_tool_router


def test_router_calls_registered_tool():
    router = ToolRouter()
    router.register("echo_tool", lambda args: ToolResult("echo_tool", "ok", args))

    result = router.call("echo_tool", {"value": 1})

    assert result.summary == "ok"
    assert result.payload == {"value": 1}


def test_router_rejects_unknown_tool():
    router = ToolRouter()

    with pytest.raises(KeyError):
        router.call("missing", {})


def test_default_router_has_profile_and_question_tools():
    router = create_default_tool_router()

    assert router.names() == ["plan_next_question", "retrieve_profile_context"]
