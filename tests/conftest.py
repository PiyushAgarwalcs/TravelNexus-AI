"""
Test configuration — mocks external services so tests run
without API keys, a database, or network access.

HOW IT WORKS
------------
backend.py and mcp_client.py execute heavy side-effects at import
time (DB connection, LLM construction, MCP client creation).

This conftest installs lightweight MagicMock modules into
sys.modules BEFORE any project code is imported, so the entire
test suite runs fast, offline, and without real packages like
psycopg needing to connect anywhere.
"""

import os
import sys
from unittest.mock import MagicMock

from langgraph.checkpoint.memory import MemorySaver

import pytest

# ═══════════════════════════════════════════════════════
# 1. Dummy environment variables
#    (must be set BEFORE any project module is imported)
# ═══════════════════════════════════════════════════════
_TEST_ENV = {
    "GROQ_API_KEY": "gsk_test000000000000000000000000000000000000000000000",
    "DATABASE_URL": "postgresql://test:test@localhost:5432/testdb?sslmode=disable",
    "TAVILY_API_KEY": "tvly-test0000000000000000000000000000",
    "AVIATION_STACK_API_KEY": "test_aviation_key_00000000",
    "OPENWEATHER_API_KEY": "test_openweather_key_00000",
}

for _key, _value in _TEST_ENV.items():
    os.environ[_key] = _value


# ═══════════════════════════════════════════════════════
# 2. Pre-mock heavy external modules via sys.modules
#
#    This approach works even when packages like psycopg
#    are not installed in the test environment.  The mocks
#    are inserted BEFORE backend.py gets imported, so all
#    import-time side effects (DB connect, LLM init) hit
#    the mocks instead of real code.
# ═══════════════════════════════════════════════════════

# ── Mock LLM (ChatGroq) ──
_mock_llm = MagicMock(name="mock_chat_groq_llm")
_mock_llm.invoke.return_value = MagicMock(
    content='{"allowed": true, "reason": "Test approved"}'
)

_mock_langchain_groq = MagicMock(name="mock_langchain_groq_module")
_mock_langchain_groq.ChatGroq.return_value = _mock_llm

# ── Mock psycopg (PostgreSQL driver) ──
_mock_pg_conn = MagicMock(name="mock_pg_connection")
_mock_psycopg = MagicMock(name="mock_psycopg_module")
_mock_psycopg.connect.return_value = _mock_pg_conn

_mock_psycopg_rows = MagicMock(name="mock_psycopg_rows")
_mock_psycopg_rows.dict_row = MagicMock()

# ── Mock PostgresSaver → use real MemorySaver ──
# LangGraph validates the checkpointer type at graph.compile(),
# so we provide a real in-memory saver instead of a MagicMock.
_memory_saver = MemorySaver()
_memory_saver.setup = MagicMock() # Add dummy setup() to match PostgresSaver
_mock_checkpoint_module = MagicMock(name="mock_checkpoint_postgres")
_mock_checkpoint_module.PostgresSaver.return_value = _memory_saver

# ── Mock MCP adapters ──
_mock_mcp_client_instance = MagicMock(name="mock_mcp_client")
_mock_mcp_adapters = MagicMock(name="mock_mcp_adapters_module")
_mock_mcp_adapters.MultiServerMCPClient.return_value = _mock_mcp_client_instance

# ── Install mocks into sys.modules ──
# These MUST run before any `import backend` or `from backend import ...`
sys.modules["langchain_groq"] = _mock_langchain_groq
sys.modules["psycopg"] = _mock_psycopg
sys.modules["psycopg.rows"] = _mock_psycopg_rows
sys.modules["langgraph.checkpoint.postgres"] = _mock_checkpoint_module
sys.modules["langchain_mcp_adapters.client"] = _mock_mcp_adapters


# ═══════════════════════════════════════════════════════
# 3. Fixtures
# ═══════════════════════════════════════════════════════


@pytest.fixture(autouse=True)
def _reset_llm_mock():
    """Reset the LLM mock between tests for isolation."""
    import backend

    backend.llm.reset_mock()
    backend.llm.invoke.return_value = MagicMock(
        content='{"allowed": true, "reason": ""}'
    )
    backend.llm.invoke.side_effect = None
    yield


@pytest.fixture()
def api_client():
    """FastAPI TestClient with all backends mocked."""
    from fastapi.testclient import TestClient
    from app import app

    return TestClient(app)
