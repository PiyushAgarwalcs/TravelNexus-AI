"""Tests for agent functions with a mocked LLM.

The conftest patches ChatGroq so backend.llm is a MagicMock.
Each test configures the mock's return value to simulate
specific LLM responses.
"""

from unittest.mock import MagicMock

from backend import guardrail_blocked_agent, supervisor_agent


# ── guardrail_blocked_agent ───────────────────────────


class TestGuardrailBlockedAgent:
    """guardrail_blocked_agent just echoes the blocked reason."""

    def test_returns_reason_from_final_response(self):
        state = {"final_response": "Off-topic request", "guardrail_reason": ""}
        result = guardrail_blocked_agent(state)
        assert result["final_response"] == "Off-topic request"

    def test_falls_back_to_guardrail_reason(self):
        state = {"final_response": "", "guardrail_reason": "Not travel related"}
        result = guardrail_blocked_agent(state)
        assert result["final_response"] == "Not travel related"

    def test_uses_default_when_no_reason(self):
        result = guardrail_blocked_agent({})
        assert "blocked" in result["final_response"].lower()

    def test_returns_ai_message(self):
        state = {"guardrail_reason": "Blocked for testing"}
        result = guardrail_blocked_agent(state)
        assert len(result["messages"]) == 1
        assert result["messages"][0].content == "Blocked for testing"


# ── supervisor_agent ──────────────────────────────────


class TestSupervisorAgent:
    """Tests for the supervisor/guardrail pipeline."""

    def test_blocks_when_guardrail_says_no(self):
        import backend

        backend.llm.invoke.return_value = MagicMock(
            content='{"allowed": false, "reason": "Not a travel request."}'
        )
        state = {"user_query": "Write Python code", "llm_calls": 0}

        result = supervisor_agent(state)

        assert result["guardrail_allowed"] is False
        assert result["selected_agents"] == []
        assert "llm_calls" in result

    def test_allows_and_routes_travel_request(self):
        import backend

        backend.llm.invoke.side_effect = [
            # 1st call → guardrail
            MagicMock(content='{"allowed": true, "reason": ""}'),
            # 2nd call → supervisor routing
            MagicMock(
                content=(
                    '{"selected_agents": ["flight_agent", "itinerary_agent"],'
                    ' "trip_constraints": {"destination": "Tokyo"},'
                    ' "reasoning": "Flight search needed"}'
                )
            ),
        ]
        state = {"user_query": "Find flights to Tokyo", "llm_calls": 0}

        result = supervisor_agent(state)

        assert result["guardrail_allowed"] is True
        assert "flight_agent" in result["selected_agents"]
        assert "itinerary_agent" in result["selected_agents"]

    def test_ensures_itinerary_agent_always_included(self):
        import backend

        backend.llm.invoke.side_effect = [
            MagicMock(content='{"allowed": true, "reason": ""}'),
            MagicMock(
                content=(
                    '{"selected_agents": ["flight_agent"],'
                    ' "trip_constraints": {},'
                    ' "reasoning": "test"}'
                )
            ),
        ]
        state = {"user_query": "Flights to Paris", "llm_calls": 0}

        result = supervisor_agent(state)

        assert "itinerary_agent" in result["selected_agents"]

    def test_falls_back_on_guardrail_llm_error(self):
        import backend

        backend.llm.invoke.side_effect = Exception("LLM timeout")
        state = {"user_query": "Plan a trip to Japan", "llm_calls": 0}

        result = supervisor_agent(state)

        # Fails open — request is allowed
        assert result["guardrail_allowed"] is True

    def test_falls_back_on_supervisor_parse_error(self):
        import backend

        backend.llm.invoke.side_effect = [
            # Guardrail passes
            MagicMock(content='{"allowed": true, "reason": ""}'),
            # Supervisor returns unparseable response
            MagicMock(content="I cannot return JSON right now"),
        ]
        state = {"user_query": "Hotels in Bali", "llm_calls": 0}

        result = supervisor_agent(state)

        # Falls back to all agents
        assert result["guardrail_allowed"] is True
        assert len(result["selected_agents"]) == len(backend.AGENT_ORDER)

    def test_increments_llm_calls(self):
        import backend

        backend.llm.invoke.side_effect = [
            MagicMock(content='{"allowed": true, "reason": ""}'),
            MagicMock(
                content=(
                    '{"selected_agents": ["itinerary_agent"],'
                    ' "trip_constraints": {},'
                    ' "reasoning": "ok"}'
                )
            ),
        ]
        state = {"user_query": "Plan trip", "llm_calls": 0}

        result = supervisor_agent(state)

        assert result["llm_calls"] == 2  # guardrail + supervisor
