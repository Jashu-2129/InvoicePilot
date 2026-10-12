from unittest.mock import Mock

from agent.agent import InvoiceAgent
from agent.recovery import Recovery
from agent.state import AgentState


def test_recovery_records_error_and_allows_retry():
    recovery = Recovery()
    state = AgentState(user_goal="Find invoice INV-001")

    should_retry = recovery.handle_error(
        state,
        "Temporary connection error",
    )

    assert should_retry is True
    assert state.errors == ["Temporary connection error"]
    assert state.data["retry_count"] == 1
    assert state.finished is False


def test_recovery_stops_at_max_retries():
    recovery = Recovery()
    state = AgentState(user_goal="Find invoice INV-001")

    for attempt in range(recovery.max_retries):
        should_retry = recovery.handle_error(
            state,
            f"Error {attempt + 1}",
        )

    assert should_retry is False
    assert state.data["retry_count"] == recovery.max_retries
    assert state.finished is True
    assert len(state.errors) == recovery.max_retries


def test_agent_retries_temporary_tool_failure():
    agent = InvoiceAgent(Mock())
    state = AgentState(user_goal="Find invoice INV-001")

    agent.executor.execute_tool = Mock(
        side_effect=[
            RuntimeError("Temporary connection error"),
            RuntimeError("Temporary connection error"),
            {
                "http_status": 200,
                "page_content": "{}",
            },
        ]
    )

    result = agent.execute_with_retry(
        state,
        "inspect_invoice",
        invoice_id="INV-001",
    )

    assert result["http_status"] == 200
    assert agent.executor.execute_tool.call_count == 3
    assert state.data["retry_count"] == 2
    assert len(state.errors) == 2