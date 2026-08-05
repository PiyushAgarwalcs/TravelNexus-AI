"""Tests for state helpers and result serialization.

All functions under test are pure — they only inspect or
transform data structures.  No LLM or database access.
"""

import pytest
from unittest.mock import MagicMock

from backend import (
    _empty_constraints,
    _interrupt_payload,
    _json_from_llm,
    _serialize_result,
)


# ── _empty_constraints ────────────────────────────────


class TestEmptyConstraints:

    def test_returns_all_expected_keys(self):
        constraints = _empty_constraints()
        expected = {
            "destination",
            "origin",
            "duration",
            "budget",
            "travel_style",
            "special_preferences",
        }
        assert set(constraints.keys()) == expected

    def test_returns_fresh_dict_each_call(self):
        a = _empty_constraints()
        b = _empty_constraints()
        assert a is not b
        a["destination"] = "Tokyo"
        assert b["destination"] == ""

    def test_special_preferences_is_list(self):
        assert isinstance(_empty_constraints()["special_preferences"], list)


# ── _json_from_llm ────────────────────────────────────


class TestJsonFromLlm:

    def test_clean_json(self):
        result = _json_from_llm('{"allowed": true, "reason": "ok"}')
        assert result == {"allowed": True, "reason": "ok"}

    def test_json_with_surrounding_text(self):
        text = 'Here is the result:\n{"key": "value"}\nDone.'
        assert _json_from_llm(text) == {"key": "value"}

    def test_nested_json(self):
        text = '{"a": {"b": 1}, "c": [2, 3]}'
        result = _json_from_llm(text)
        assert result["a"]["b"] == 1
        assert result["c"] == [2, 3]

    def test_raises_on_no_json(self):
        with pytest.raises(ValueError, match="JSON"):
            _json_from_llm("No JSON here at all")

    def test_raises_on_empty_string(self):
        with pytest.raises(ValueError):
            _json_from_llm("")

    def test_raises_on_malformed_json(self):
        with pytest.raises(Exception):
            _json_from_llm("{not: valid, json}")


# ── _interrupt_payload ────────────────────────────────


class TestInterruptPayload:

    def test_none_when_no_interrupts_key(self):
        assert _interrupt_payload({}) is None

    def test_none_when_empty_list(self):
        assert _interrupt_payload({"__interrupt__": []}) is None

    def test_extracts_dict_value(self):
        interrupt = MagicMock()
        interrupt.value = {"draft_itinerary": "Day 1: Arrive in Tokyo"}
        result = _interrupt_payload({"__interrupt__": [interrupt]})
        assert result == {"draft_itinerary": "Day 1: Arrive in Tokyo"}

    def test_wraps_non_dict_value(self):
        interrupt = MagicMock()
        interrupt.value = "some string"
        result = _interrupt_payload({"__interrupt__": [interrupt]})
        assert result == {"value": "some string"}

    def test_uses_first_interrupt_only(self):
        i1 = MagicMock()
        i1.value = {"first": True}
        i2 = MagicMock()
        i2.value = {"second": True}
        result = _interrupt_payload({"__interrupt__": [i1, i2]})
        assert result == {"first": True}


# ── _serialize_result ─────────────────────────────────


class TestSerializeResult:

    def _make_result(self, **overrides):
        from langchain_core.messages import AIMessage

        base = {
            "messages": [AIMessage(content="test")],
            "final_response": "Final plan here",
            "flight_results": "",
            "hotel_results": "",
            "weather_results": "",
            "budget_results": "",
            "itinerary": "",
            "selected_agents": [],
            "trip_constraints": {},
            "supervisor_reasoning": "",
            "guardrail_allowed": True,
            "guardrail_reason": "",
            "approved": None,
            "human_feedback": "",
            "llm_calls": 0,
        }
        base.update(overrides)
        return base

    def test_includes_all_required_keys(self):
        serialized = _serialize_result(self._make_result(), "thread-123")
        required = {
            "thread_id",
            "answer",
            "requires_approval",
            "approval_request",
            "flight_results",
            "hotel_results",
            "weather_results",
            "budget_results",
            "itinerary",
            "selected_agents",
            "trip_constraints",
            "supervisor_reasoning",
            "guardrail_allowed",
            "guardrail_reason",
            "approved",
            "human_feedback",
            "llm_calls",
        }
        assert required.issubset(set(serialized.keys()))

    def test_no_approval_required_without_interrupt(self):
        serialized = _serialize_result(self._make_result(), "t-1")
        assert serialized["requires_approval"] is False

    def test_uses_final_response_as_answer(self):
        serialized = _serialize_result(
            self._make_result(final_response="My plan"),
            "t-1",
        )
        assert serialized["answer"] == "My plan"

    def test_thread_id_passed_through(self):
        serialized = _serialize_result(self._make_result(), "abc-123")
        assert serialized["thread_id"] == "abc-123"

    def test_preserves_selected_agents(self):
        result = self._make_result(selected_agents=["flight_agent", "hotel_agent"])
        serialized = _serialize_result(result, "t-1")
        assert serialized["selected_agents"] == ["flight_agent", "hotel_agent"]
