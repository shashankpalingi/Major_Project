# Agentic Abstention and Sequential Uncertainty Middleware

A research-grade multi-step LLM agent that generates **controlled, reproducible trajectories** — successes, failures, recoveries, and loops — as the foundation for an abstention middleware layer.

---

## Project Phases

| Phase | Status | Description |
|-------|--------|-------------|
| **Phase 1** | ✅ Complete | Basic LLM agent with mock tools |
| **Phase 2** | ✅ Complete | Controlled failure scenarios and structured logging |
| Phase 3+ | 🔜 Planned | Abstention middleware, Redis, PostgreSQL, Decision Transformer |

---

## Architecture

```
User Task
   ↓
LLM Agent  (Groq API — Llama model)
   ↓
Tool Call  (with optional ScenarioConfig injected)
   ↓
Controlled Mock Tool
   ↓
Observation  (SUCCESS / FAILURE / EMPTY_RESULT)
   ↓
LLM Agent
   ↓
Next Action / Final Response
```

> Phase 3 will insert an **Interceptor Proxy** between the LLM Agent and the Tool Call step to implement abstention logic.

---

## Project Structure

```
agentic-abstention/
├── app/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   └── agent.py              # Core Agent class + structured logging
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── flight_tool.py        # Mock flights  (Phase 2: failure injection)
│   │   ├── weather_tool.py       # Mock weather  (Phase 1 only)
│   │   └── search_tool.py        # Mock search   (Phase 2: empty result injection)
│   ├── scenarios/
│   │   ├── __init__.py
│   │   ├── config.py             # ScenarioConfig + ToolFailureConfig dataclasses
│   │   └── definitions.py        # All named scenarios registered in SCENARIOS dict
│   └── main.py                   # CLI entry point
├── .env                          # API key (never commit)
├── .gitignore
├── requirements.txt
└── README.md
```

---

## Setup

### 1. Python 3.11+, create virtualenv

```bash
cd agentic-abstention
python -m venv venv
source venv/bin/activate       # macOS/Linux
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Add your Groq API key to `.env`

```
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

Get a free key at <https://console.groq.com>.

---

## Running the Project

### List available scenarios

```bash
python -m app.main list
```

### Phase 1 — original three tests (no failure injection)

```bash
python -m app.main
python -m app.main phase1
```

### Phase 2 — individual scenarios

```bash
python -m app.main success
python -m app.main recovery
python -m app.main repeated_failure
python -m app.main empty_result
python -m app.main impossible
python -m app.main loop
```

### Phase 2 — all six scenarios in sequence

```bash
python -m app.main all
```

### Override the LLM model (optional)

```bash
GROQ_MODEL=qwen/qwen3.8-27b python -m app.main success
```

---

## Phase 2 Scenarios

### Scenario 1 — SUCCESS (`success`)

**Task:** "What is the weather in Hyderabad?"

No failure injection. Tool executes normally and succeeds.

**Expected trajectory:**

```
ITERATION 1 → LLM calls weather_tool → TOOL STATUS: SUCCESS
ITERATION 2 → LLM produces final answer
```

**Why it matters:** Establishes the clean baseline. The abstention middleware must learn to pass through successful calls without interference.

---

### Scenario 2 — TEMPORARY FAILURE → RECOVERY (`recovery`)

**Task:** "Find a flight from Hyderabad to Delhi."

`flight_search_tool` is configured with `fail_times=1`: the first call returns `status: failure`, the second call returns `status: success`.

**Expected trajectory:**

```
ITERATION 1 → LLM calls flight_search_tool → TOOL STATUS: FAILURE
ITERATION 2 → LLM retries flight_search_tool → TOOL STATUS: SUCCESS
ITERATION 3 → LLM produces final answer
```

**Why it matters:** Demonstrates that a single failure is recoverable. The middleware must distinguish transient failures (retry) from permanent ones (abstain).

---

### Scenario 3 — REPEATED FAILURE (`repeated_failure`)

**Task:** "Find a flight from Hyderabad to Delhi."

`flight_search_tool` is configured with `always_fail=True`. Every call returns `status: failure`. The agent retries until `max_iterations` is reached.

**Expected trajectory:**

```
ITERATION 1 → LLM calls flight_search_tool → TOOL STATUS: FAILURE
ITERATION 2 → LLM retries → TOOL STATUS: FAILURE
ITERATION 3 → LLM retries → TOOL STATUS: FAILURE
...
MAX ITERATIONS REACHED — no final answer produced
```

> ⚠️ This is **intentionally bad behaviour**. The agent loops without resolving. Phase 3 middleware will detect this pattern and force abstention instead.

**Why it matters:** Creates the "repeated failure" trajectory that the Decision Transformer must learn to flag as an abstention trigger.

---

### Scenario 4 — EMPTY RESULT (`empty_result`)

**Task:** "Search for information about xzqwerty_unknown_topic_42."

`search_tool` is configured with `empty_result=True`. It returns `status: success` but `results: []`. The LLM must decide what to do with a vacuous observation.

**Expected trajectory:**

```
ITERATION 1 → LLM calls search_tool → TOOL STATUS: EMPTY_RESULT
ITERATION 2 → LLM either retries or produces a "no results" final answer
```

**Why it matters:** Tests whether the LLM correctly interprets an empty-but-successful response, and whether it hallucinates results or admits it found nothing.

---

### Scenario 5 — IMPOSSIBLE TASK (`impossible`)

**Task:** "Book a flight from Hyderabad to Mars."

`flight_search_tool` is configured with `always_fail=True` and a specific error message: *"Destination 'Mars' is not a supported location."*

**Expected trajectory:**

```
ITERATION 1 → LLM calls flight_search_tool → TOOL STATUS: FAILURE
ITERATION 2 → LLM retries (or gives up) → TOOL STATUS: FAILURE
...
LLM eventually produces a final answer explaining the task is impossible
```

**Why it matters:** The LLM should eventually conclude the task is impossible and say so. The middleware will later enforce an earlier abstention rather than letting the agent burn iterations.

---

### Scenario 6 — LOOP (`loop`)

**Task:** "Search for information about xzqwerty_unknown_topic_42."

`search_tool` always returns `empty_result=True`. `max_iterations` is raised to **6** to make the looping behaviour clearly visible.

**Expected trajectory:**

```
ITERATION 1 → search_tool → EMPTY_RESULT
ITERATION 2 → search_tool → EMPTY_RESULT  (LLM retries same query)
ITERATION 3 → search_tool → EMPTY_RESULT
...
MAX ITERATIONS REACHED
```

**Why it matters:** Exposes a fundamental weakness — the agent can call the same tool with identical inputs repeatedly with no progress. The trajectory distiller (Phase 3+) will tag this as a degenerate loop.

---

## How Failure Injection Works

Failure is **not** random. It is deterministic and reproducible.

```
ScenarioConfig
  └── tool_configs: [ToolFailureConfig]
        ├── tool_name      → which tool to intercept
        ├── fail_times     → fail exactly N times, then succeed
        ├── always_fail    → fail on every call
        └── empty_result   → succeed but return results=[]
```

The `Agent._execute_tool()` method looks up the config for each tool by name and injects it as a hidden `_scenario` keyword argument — **never part of the LLM-visible schema**. The LLM sees only the tool result; it has no knowledge of the injection.

---

## Log Format

Every run produces structured per-iteration logs:

```
══════════════════════════════════════════════════════════
  ITERATION 2 / 5
══════════════════════════════════════════════════════════
  LLM TOOL DECISION : ['flight_search_tool']
  TOOL NAME  : flight_search_tool
  TOOL INPUT : {"source": "Hyderabad", "destination": "Delhi"}
  TOOL OUTPUT:
  {
      "status": "failure",
      "error": "Flight search service is temporarily unavailable."
  }
  TOOL STATUS: FAILURE
  LLM NEXT DECISION: looping back to LLM …
──────────────────────────────────────────────────────────
```

Status labels:

| Label | Meaning |
|-------|---------|
| `SUCCESS` | Tool returned data |
| `FAILURE` | Tool returned an error or no-result status |
| `EMPTY_RESULT` | Tool returned `status: success` with `results: []` |
| `ERROR` | Agent-level dispatch error (bad args, unknown tool) |

---

## Why These Scenarios Matter for Phase 3

The six trajectories cover the decision space an abstention middleware must handle:

| Scenario | Agent behaviour | Middleware response (Phase 3) |
|----------|----------------|-------------------------------|
| success | Works correctly | Pass through |
| recovery | One failure, then success | Allow retry |
| repeated_failure | Loops forever | Force abstention after N failures |
| empty_result | Ambiguous observation | Flag for clarification |
| impossible | Unsupported task | Early abstention |
| loop | Identical calls, no progress | Detect degenerate loop, abstain |

Without these controlled trajectories, there is nothing to train the Decision Transformer on.

---

## Phase 3 Preview (Not Yet Implemented)

```
User Task
   ↓
LLM Agent
   ↓
┌─────────────────────────────┐
│   Interceptor Proxy         │  ← Phase 3
│   - Uncertainty estimation  │
│   - Trajectory distillation │
│   - Playbook lookup         │
│   - Redis state cache       │
│   - PostgreSQL logging      │
└─────────────────────────────┘
   ↓
Tool Execution
```

---

## Models with Tool Use Support (Groq)

| Model ID | Notes |
|----------|-------|
| `llama-3.1-8b-instant` | Default. Fast, free tier |
| `qwen/qwen3.8-27b` | Larger, parallel tool calls |
| `openai/gpt-oss-20b` | Fast, built-in tools |
| `openai/gpt-oss-120b` | Best quality |

Override via `.env`: `GROQ_MODEL=qwen/qwen3.8-27b`

---

## License

MIT
