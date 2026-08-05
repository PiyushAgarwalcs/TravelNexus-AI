"""Tests for the supervisor routing logic.

These exercise pure routing functions and constants —
no LLM calls, no database, no network.
"""

from backend import (
    AGENT_ORDER,
    KNOWN_AGENTS,
    ROUTE_MAP,
    _selected_agents,
    route_after_agent,
    route_from_supervisor,
)


# ── _selected_agents ──────────────────────────────────


class TestSelectedAgents:
    """_selected_agents must preserve AGENT_ORDER and filter unknowns."""

    def test_preserves_agent_order(self):
        state = {"selected_agents": ["budget_agent", "flight_agent", "itinerary_agent"]}
        result = _selected_agents(state)
        assert result == ["flight_agent", "budget_agent", "itinerary_agent"]

    def test_empty_selection(self):
        state = {"selected_agents": []}
        assert _selected_agents(state) == []

    def test_missing_key_defaults_to_empty(self):
        assert _selected_agents({}) == []

    def test_ignores_unknown_agents(self):
        state = {"selected_agents": ["flight_agent", "unknown_agent"]}
        assert _selected_agents(state) == ["flight_agent"]

    def test_all_agents_selected(self):
        state = {"selected_agents": list(KNOWN_AGENTS)}
        result = _selected_agents(state)
        assert len(result) == len(AGENT_ORDER)


# ── route_from_supervisor ─────────────────────────────


class TestRouteFromSupervisor:
    """Supervisor → first agent routing decisions."""

    def test_guardrail_blocked(self):
        state = {"guardrail_allowed": False, "selected_agents": ["flight_agent"]}
        assert route_from_supervisor(state) == "guardrail_blocked"

    def test_routes_to_first_selected_agent(self):
        state = {
            "guardrail_allowed": True,
            "selected_agents": ["hotel_agent", "itinerary_agent"],
        }
        assert route_from_supervisor(state) == "hotel_agent"

    def test_falls_back_to_itinerary_when_no_agents(self):
        state = {"guardrail_allowed": True, "selected_agents": []}
        assert route_from_supervisor(state) == "itinerary_agent"

    def test_defaults_to_allowed_when_key_missing(self):
        state = {"selected_agents": ["weather_agent"]}
        assert route_from_supervisor(state) == "weather_agent"

    def test_respects_agent_order_not_selection_order(self):
        state = {
            "guardrail_allowed": True,
            "selected_agents": ["weather_agent", "flight_agent"],
        }
        # flight_agent comes before weather_agent in AGENT_ORDER
        assert route_from_supervisor(state) == "flight_agent"


# ── route_after_agent ─────────────────────────────────


class TestRouteAfterAgent:
    """Agent → next agent chaining."""

    def test_routes_to_next_selected_agent(self):
        state = {"selected_agents": ["flight_agent", "hotel_agent", "itinerary_agent"]}
        router = route_after_agent("flight_agent")
        assert router(state) == "hotel_agent"

    def test_skips_unselected_agents(self):
        state = {"selected_agents": ["flight_agent", "budget_agent", "itinerary_agent"]}
        router = route_after_agent("flight_agent")
        # hotel_agent and weather_agent are not selected → skipped
        assert router(state) == "budget_agent"

    def test_falls_back_to_itinerary(self):
        state = {"selected_agents": ["flight_agent", "itinerary_agent"]}
        router = route_after_agent("flight_agent")
        assert router(state) == "itinerary_agent"

    def test_last_specialist_routes_to_itinerary(self):
        state = {"selected_agents": ["budget_agent", "itinerary_agent"]}
        router = route_after_agent("budget_agent")
        assert router(state) == "itinerary_agent"

    def test_only_itinerary_selected(self):
        state = {"selected_agents": ["itinerary_agent"]}
        router = route_after_agent("flight_agent")
        assert router(state) == "itinerary_agent"


# ── Constants consistency ─────────────────────────────


class TestConstants:
    """Verify that the routing constants are internally consistent."""

    def test_known_agents_match_order(self):
        assert set(AGENT_ORDER) == KNOWN_AGENTS

    def test_agent_order_has_no_duplicates(self):
        assert len(AGENT_ORDER) == len(set(AGENT_ORDER))

    def test_route_map_covers_all_agents(self):
        for agent in AGENT_ORDER:
            assert agent in ROUTE_MAP, f"{agent} missing from ROUTE_MAP"

    def test_route_map_includes_guardrail_blocked(self):
        assert "guardrail_blocked" in ROUTE_MAP
