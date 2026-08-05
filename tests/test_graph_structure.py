"""Tests that the LangGraph definition is structurally correct.

These verify the graph topology without invoking any agent —
no LLM, no database, no network.
"""

from backend import AGENT_ORDER, KNOWN_AGENTS, ROUTE_MAP, graph


class TestGraphNodes:
    """The compiled graph must contain every expected node."""

    EXPECTED_NODES = {
        "supervisor",
        "guardrail_blocked",
        "flight_agent",
        "hotel_agent",
        "weather_agent",
        "budget_agent",
        "itinerary_agent",
        "human_approval",
        "final_agent",
    }

    def test_has_all_expected_nodes(self):
        actual = set(graph.nodes.keys())
        missing = self.EXPECTED_NODES - actual
        assert not missing, f"Missing nodes: {missing}"

    def test_no_unexpected_nodes(self):
        # Allow __start__ and __end__ which LangGraph adds internally
        internal = {"__start__", "__end__"}
        actual = set(graph.nodes.keys()) - internal
        unexpected = actual - self.EXPECTED_NODES
        assert not unexpected, f"Unexpected nodes: {unexpected}"


class TestAgentConstants:
    """KNOWN_AGENTS, AGENT_ORDER, and ROUTE_MAP must stay consistent."""

    def test_known_agents_equals_agent_order_set(self):
        assert set(AGENT_ORDER) == KNOWN_AGENTS

    def test_agent_order_has_no_duplicates(self):
        assert len(AGENT_ORDER) == len(set(AGENT_ORDER))

    def test_route_map_covers_all_agents(self):
        for agent in AGENT_ORDER:
            assert agent in ROUTE_MAP, f"{agent} missing from ROUTE_MAP"

    def test_route_map_includes_guardrail_blocked(self):
        assert "guardrail_blocked" in ROUTE_MAP

    def test_itinerary_agent_is_last_in_order(self):
        assert AGENT_ORDER[-1] == "itinerary_agent"
