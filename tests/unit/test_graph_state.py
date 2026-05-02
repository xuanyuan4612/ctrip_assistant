"""Graph State 测试"""
import pytest
from app.graph.state import update_dialog_stack, State


class TestDialogStack:
    def test_push(self):
        result = update_dialog_stack(["assistant"], "update_flight")
        assert result == ["assistant", "update_flight"]

    def test_pop(self):
        result = update_dialog_stack(["assistant", "update_flight"], "pop")
        assert result == ["assistant"]

    def test_noop_none(self):
        result = update_dialog_stack(["assistant"], None)
        assert result == ["assistant"]

    def test_push_to_empty(self):
        result = update_dialog_stack([], "book_hotel")
        assert result == ["book_hotel"]

    def test_pop_empty_returns_empty(self):
        result = update_dialog_stack([], "pop")
        assert result == []


class TestState:
    def test_state_fields(self):
        state = State(
            messages=[],
            summary="",
            user_id=1,
            username="test",
            passenger_id="P123",
            user_info={},
            dialog_state=["assistant"],
            decision_path=[],
            confidence_scores={},
            guardrail_flags=[],
            clarification_needed=False,
            collected_slots={},
        )
        assert state["user_id"] == 1
        assert state["passenger_id"] == "P123"
        assert state["dialog_state"] == ["assistant"]
