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
graph TD
    User([User Prompt]) --> G{Input Guardrail}
    G -- "Blocked" --> End([End])
    G -- "Allowed" --> Sup[Supervisor Agent]
    
    Sup --> F[Flight Agent]
    Sup --> H[Hotel Agent]
    Sup --> W[Weather Agent]
    Sup --> B[Budget Agent]
    
    F --> I[Itinerary Agent]
    H --> I
    W --> I
    B --> I
    Sup -- "Direct" --> I
    
    I --> HITL{Human Approval}
    HITL -- "Feedback" --> Sup
    HITL -- "Approved" --> Final[Final Plan Generation]
    Final --> DB[(PostgreSQL State)]
    Final --> End
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
git clone https://github.com/yourusername/TravelNexus-AI.git
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
