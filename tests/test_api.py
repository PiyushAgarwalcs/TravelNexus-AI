"""Tests for FastAPI API endpoints.

The backend functions (run_travel_agent, resume_travel_agent)
are patched at the `app` module level so no LLM, DB, or MCP
calls are made.
"""

from unittest.mock import patch


# ── GET /health ───────────────────────────────────────


class TestHealthEndpoint:

    def test_returns_ok_status(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_includes_app_name(self, api_client):
        data = api_client.get("/health").json()
        assert "TravelNexus-AI" in data["message"]

    def test_lists_features(self, api_client):
        features = api_client.get("/health").json()["features"]
        assert "supervisor_agent" in features
        assert "input_guardrail" in features
        assert "human_in_the_loop" in features


# ── GET / ─────────────────────────────────────────────


class TestHomeEndpoint:

    def test_returns_html(self, api_client):
        resp = api_client.get("/")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]

    def test_contains_app_title(self, api_client):
        assert "TravelNexus-AI" in api_client.get("/").text


# ── POST /api/travel ──────────────────────────────────


class TestTravelEndpoint:

    def test_rejects_empty_message(self, api_client):
        resp = api_client.post("/api/travel", json={"message": "   "})
        assert resp.status_code == 400
        assert resp.json()["success"] is False

    def test_rejects_missing_message(self, api_client):
        resp = api_client.post("/api/travel", json={"message": ""})
        assert resp.status_code == 400

    @patch("app.run_travel_agent")
    def test_success_response(self, mock_run, api_client):
        mock_run.return_value = {
            "thread_id": "t-123",
            "answer": "Your trip plan",
            "requires_approval": False,
            "selected_agents": ["flight_agent"],
            "guardrail_allowed": True,
        }
        resp = api_client.post(
            "/api/travel",
            json={"message": "Plan a trip to Japan"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["thread_id"] == "t-123"

    @patch("app.run_travel_agent")
    def test_passes_thread_id(self, mock_run, api_client):
        mock_run.return_value = {"thread_id": "existing-thread", "answer": "ok"}
        api_client.post(
            "/api/travel",
            json={"message": "Hotels in Dubai", "thread_id": "existing-thread"},
        )
        mock_run.assert_called_once_with(
            user_input="Hotels in Dubai",
            thread_id="existing-thread",
        )

    @patch("app.run_travel_agent")
    def test_handles_backend_error(self, mock_run, api_client):
        mock_run.side_effect = RuntimeError("LLM unavailable")
        resp = api_client.post(
            "/api/travel",
            json={"message": "Plan a trip"},
        )
        assert resp.status_code == 500
        assert resp.json()["success"] is False


# ── POST /api/travel/approve ──────────────────────────


class TestApprovalEndpoint:

    def test_rejects_rejection_without_feedback(self, api_client):
        resp = api_client.post(
            "/api/travel/approve",
            json={"thread_id": "t-1", "approved": False, "feedback": ""},
        )
        assert resp.status_code == 400

    def test_rejects_empty_thread_id(self, api_client):
        resp = api_client.post(
            "/api/travel/approve",
            json={"thread_id": "", "approved": True, "feedback": ""},
        )
        assert resp.status_code == 422  # Pydantic validation

    @patch("app.resume_travel_agent")
    def test_approval_success(self, mock_resume, api_client):
        mock_resume.return_value = {
            "thread_id": "t-1",
            "answer": "Final plan",
            "requires_approval": False,
        }
        resp = api_client.post(
            "/api/travel/approve",
            json={"thread_id": "t-1", "approved": True, "feedback": ""},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @patch("app.resume_travel_agent")
    def test_revision_with_feedback(self, mock_resume, api_client):
        mock_resume.return_value = {"thread_id": "t-1", "answer": "Revised"}
        resp = api_client.post(
            "/api/travel/approve",
            json={
                "thread_id": "t-1",
                "approved": False,
                "feedback": "Reduce hotel cost",
            },
        )
        assert resp.status_code == 200
        mock_resume.assert_called_once_with(
            thread_id="t-1",
            approved=False,
            feedback="Reduce hotel cost",
        )
