# TravelNexus-AI 🌍✈️

<p align="center">
  <img src="docs/ui-1.png" width="48%" alt="TravelNexus-AI UI 1">
  &nbsp;
  <img src="docs/ui-2.png" width="48%" alt="TravelNexus-AI UI 2">
</p>

> **An enterprise-grade, multi-agent AI system for autonomous travel planning.**

TravelNexus-AI demonstrates advanced agentic workflows using **LangGraph** and the **Model Context Protocol (MCP)**. It features a Supervisor agent for routing, strict Input Guardrails for safety, and a Human-In-The-Loop (HITL) architecture for approval before finalizing complex itineraries.

---

## 🚀 Key Features

*   **Multi-Agent Orchestration:** A `Supervisor` agent intelligently routes user requests to specialized agents (`Flight`, `Hotel`, `Weather`, `Budget`, `Itinerary`).
*   **Input Guardrails:** Validates user prompts before processing, blocking off-topic, harmful, or non-travel requests (achieved **100% accuracy** on evals).
*   **Human-In-The-Loop (HITL):** Pauses execution to present a draft itinerary to the user for approval or revision before finalizing.
*   **Stateful Persistence:** Uses PostgreSQL (`PostgresSaver`) to checkpoint thread state, allowing users to resume conversations seamlessly.
*   **Model Context Protocol (MCP):** Connects the LLM to real-world APIs (Tavily, AviationStack, OpenWeather) using standard, secure MCP servers.
*   **Production-Ready Testing:** Includes a 60+ unit test suite with mocked backends, and an LLM evaluation suite measuring agent routing accuracy and guardrail reliability.

---

## 🏗️ Architecture

The system utilizes a directed graph architecture built with LangGraph:

```mermaid
%%{init: {'flowchart': {'nodeSpacing': 80, 'rankSpacing': 80}}}%%
flowchart TD
    %% Define Styles (Round boxes, Transparent fill, Colorful borders, Jojoba font)
    classDef user fill:transparent,stroke:#6366f1,stroke-width:2px,color:#312e81,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef guardrail fill:transparent,stroke:#22c55e,stroke-width:2px,color:#14532d,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef blocked fill:transparent,stroke:#ef4444,stroke-width:2px,color:#881337,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef supervisor fill:transparent,stroke:#a855f7,stroke-width:2px,color:#4c1d95,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef agent_flight fill:transparent,stroke:#3b82f6,stroke-width:2px,color:#1e3a8a,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef agent_hotel fill:transparent,stroke:#22c55e,stroke-width:2px,color:#14532d,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef agent_weather fill:transparent,stroke:#f59e0b,stroke-width:2px,color:#78350f,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef agent_budget fill:transparent,stroke:#8b5cf6,stroke-width:2px,color:#4c1d95,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef agent_itinerary fill:transparent,stroke:#14b8a6,stroke-width:2px,color:#134e4a,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef state fill:transparent,stroke:#64748b,stroke-width:2px,color:#0f172a,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef hitl fill:transparent,stroke:#d946ef,stroke-width:2px,color:#701a75,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef final fill:transparent,stroke:#a855f7,stroke-width:2px,color:#4c1d95,rx:15,ry:15,font-family:Jojoba,sans-serif
    classDef db fill:transparent,stroke:#0ea5e9,stroke-width:2px,color:#0c4a6e,rx:15,ry:15,font-family:Jojoba,sans-serif

    %% 1. User Input
    User("👤 1. USER INPUT<br/><i>'Plan a 4 day trip to Dubai...'</i>"):::user

    %% 2. Guardrail
    Guardrail("🛡️ 2. INPUT GUARDRAIL<br/>Validate Request<br/>(Relevance, Safety)"):::guardrail
    User --> Guardrail

    Blocked("🚫 BLOCKED REQUEST<br/>Provide reason & stop"):::blocked
    Guardrail -- "BLOCK ❌" --> Blocked

    %% 3. Supervisor
    Supervisor("🤖 3. SUPERVISOR AGENT<br/>Understands request & dynamically<br/>decides which agents are needed<br/><i>(No manual workflow!)</i>"):::supervisor
    Guardrail -- "PASS ✅" --> Supervisor

    %% 4. Specialists
    subgraph Specialists ["4. SPECIALIST AI AGENTS (Selected Dynamically)"]
        Flight("✈️ Flight Agent<br/>Searches flights & routes<br/><i>(AviationStack MCP)</i>"):::agent_flight
        Hotel("🏨 Hotel Agent<br/>Searches hotels & reviews<br/><i>(Tavily MCP)</i>"):::agent_hotel
        Weather("☀️ Weather Agent<br/>Climate & packing info<br/><i>(Custom MCP)</i>"):::agent_weather
        Budget("💰 Budget Agent<br/>Analyzes budget & costs<br/><i>(LLM)</i>"):::agent_budget
        Itinerary("🗺️ Itinerary Agent<br/>Creates day-wise plan<br/><i>(LLM)</i>"):::agent_itinerary
    end

    Supervisor --> Flight & Hotel & Weather & Budget
    Flight & Hotel & Weather & Budget --> Itinerary
    Supervisor -- "Direct Route" ----> Itinerary

    %% 5. State
    State("🗄️ 5. SHARED STATE (TravelState)<br/>user_query | trip_constraints | flight_results<br/>hotel_results | weather_info | budget_analysis<br/>itinerary_plan | messages | llm_calls"):::state
    Specialists -.- State

    %% 6. HITL
    HITL("👤 6. HUMAN-IN-THE-LOOP<br/>Review generated itinerary"):::hitl
    Itinerary --> HITL

    HITL -- "Request Changes ✏️" --> Supervisor

    %% 7. Final Response
    Final("💬 7. FINAL RESPONSE AGENT<br/>Generates well-structured travel plan"):::final
    HITL -- "Approve ✅" --> Final

    %% 8. Persistence
    DB("🐘 8. PERSISTENCE<br/>PostgreSQL Checkpointer<br/><i>Long-Term Memory</i>"):::db
    Final --> DB
```

1.  **Input:** User provides a prompt.
2.  **Guardrail:** Blocks non-travel requests immediately.
3.  **Supervisor:** Extracts constraints (budget, dates, destination) and decides which specialist agents are needed.
4.  **Specialist Agents:** Execute in parallel or sequence (Flights, Hotels, Weather, Budget).
5.  **Drafting:** The `Itinerary` agent compiles the data into a draft plan.
6.  **HITL Checkpoint:** Execution suspends. The UI prompts the user to approve or request changes.
7.  **Finalization:** Once approved, the graph completes and saves state to PostgreSQL.

---

## 🛠️ Tech Stack

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Core AI Framework** | `LangGraph` & `LangChain` | Graph-based agent orchestration |
| **LLM Provider** | `Groq` (Llama 3.3 70B) | Ultra-fast inference |
| **Tool Calling** | `Model Context Protocol (MCP)` | Standardized API integration |
| **Backend API** | `FastAPI` | High-performance async web framework |
| **Persistence** | `PostgreSQL` & `psycopg` | Thread checkpointing & state saving |
| **Search & Data** | `Tavily`, `AviationStack` | Live web search and flight data |
| **CI / CD & Testing** | `pytest`, `GitHub Actions` | Automated linting, coverage, and evals |

---

## 💻 Quick Start (Local Development)

### 1. Prerequisites
*   Python 3.10+
*   PostgreSQL running locally (or via Docker)
*   API Keys: Groq, Tavily, AviationStack, OpenWeather

### 2. Installation
```powershell
# Clone the repository
git clone https://github.com/PiyushAgarwalcs/TravelNexus-AI.git
cd TravelNexus-AI

# Create and activate virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# Install production dependencies
pip install -r requirements.txt
```

### 3. Environment Variables
Create a `.env` file in the root directory:
```env
GROQ_API_KEY=your_key
TAVILY_API_KEY=your_key
AVIATION_STACK_API_KEY=your_key
OPENWEATHER_API_KEY=your_key
DATABASE_URL=postgresql://user:password@localhost:5432/travelnexus
```

### 4. Run the Application
```powershell
uvicorn app:app --reload --host 127.0.0.1 --port 8000
```
Visit `http://127.0.0.1:8000` to interact with the UI.

---

## 🧪 Testing & Evaluation

This project maintains a high standard of reliability.

**Unit Tests (CI/CD):**
Run the mocked test suite without requiring API keys:
```powershell
pip install -r requirements-dev.txt
pytest tests/ -v --cov
```

**LLM Evaluation Suite:**
Run deterministic tests against the actual LLM to evaluate guardrail precision and supervisor routing accuracy:
```powershell
python evals/eval_suite.py
```

---

## 📝 License

This project is licensed under the MIT License. See the `LICENSE` file for details.
