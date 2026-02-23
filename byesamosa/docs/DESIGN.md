# ByeSamosa — Technical Architecture Design

## Context

Oura Ring 4 subscription costs $7/month but delivers shallow insights. The Oura app tells you WHAT happened but not WHY or WHAT to do. Goal: cancel the subscription and build a personal AI-powered dashboard using free Membership Hub data exports, with reasoning chains, personalized recommendations, and rich visualizations.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| **Dashboard** | Streamlit + Plotly | Same Python stack, direct data access, fast to build for personal tool. No separate frontend build step. |
| **Storage** | Local JSON files + pandas | Start simple with flat files. Raw exports in `data/raw/`, parsed/normalized data in `data/processed/` as JSON. Pandas for analytics/baseline queries. Can migrate to DuckDB later if needed. |
| **AI** | Claude API (Anthropic Python SDK) | Structured output, strong reasoning for chains. Data context fits easily in context window. |
| **Data Import** | Manual CSV download + CLI | Oura export is async (up to 48h) with email OTP auth — full automation not feasible for MVP. User downloads CSV from Membership Hub, imports via CLI. Playwright automation deferred to post-MVP. |
| **Package mgr** | uv | Fast modern Python packaging. |

---

## System Architecture

```
+------------------------------------------------------------------+
|                        BYESAMOSA SYSTEM                          |
+------------------------------------------------------------------+
|                                                                   |
|  +------------------+    +------------------+    +--------------+ |
|  |  MANUAL IMPORT   |    |   DATA ENGINE    |    |  AI ENGINE   | |
|  |  (CLI + CSV)     |--->|  (Parser +       |--->| (Claude API) | |
|  |                  |    |   JSON + pandas) |    |              | |
|  +------------------+    +------------------+    +--------------+ |
|         |                       |                       |         |
|         v                       v                       v         |
|  +------------------+    +------------------+    +--------------+ |
|  |  data/raw/       |    |  data/processed/ |    |  data/       | |
|  |  *.csv           |    |  *.json          |    |  insights/   | |
|  +------------------+    +------------------+    +--------------+ |
|                                 |                       |         |
|                                 v                       v         |
|                          +---------------------------+            |
|                          |    DASHBOARD (Streamlit)   |            |
|                          |    Direct data access      |            |
|                          +---------------------------+            |
+------------------------------------------------------------------+

    USER WORKFLOW:
      1. Request export at membership.ouraring.com/data-export
      2. Wait for email (up to 48h)
      3. Download CSV
      4. python -m byesamosa.pipeline import --file export.csv
      5. streamlit run streamlit_app.py
```

---

## Data Flow

```
[User imports new data]
  python -m byesamosa.pipeline import --file ~/Downloads/oura_export.csv
    → Copy CSV to data/raw/
    → Data Engine: parse CSV, normalize, save to data/processed/
    → Data Engine: recompute baselines (pandas rolling windows)
    → AI Engine: generate insight for latest day
    → Store insight as JSON in data/insights/

[User runs: streamlit run streamlit_app.py]
  → Streamlit loads DataStore directly
  → Calls get_latest_day(), get_trends(), get_deltas()
  → Loads cached AI insight from data/insights/
  → Renders dashboard
```

---

## Storage Design (Local JSON Files)

Instead of a database, data is stored as structured JSON files:

```
data/
├── raw/                          # Untouched Oura exports (CSV)
│   ├── 2025-02-12_export.csv
│   └── 2025-02-13_export.csv
│
├── processed/                    # Normalized, deduplicated data
│   ├── daily_sleep.json          # Array of DailySleep records, keyed by day
│   ├── daily_readiness.json      # Array of DailyReadiness records
│   ├── daily_activity.json       # Array of DailyActivity records
│   ├── sleep_phases.json         # 5-min interval sleep phase data
│   └── baselines.json            # Pre-computed 7d/30d/90d rolling averages
│
├── insights/                     # AI-generated insights (one file per import)
│   └── 2025-02-12.json
│
└── logs/
```

**How it works:**
- Parser reads raw exports → normalizes into Pydantic models → appends/upserts into the processed JSON files (dedup by `day` field)
- Baselines computed via pandas: `df.rolling(window=30).mean()` etc.
- **Streamlit reruns the script on each interaction** (data is small — ~365 rows/year, negligible I/O cost). This means the dashboard always shows fresh data.

---

## Data Models (Pydantic)

> **Note:** These models are provisional. Final field names and types will be determined after inspecting the actual Oura CSV export.

**Schema Versioning:** All processed JSON files include `schema_version: int` field. Current version: `1`. If Oura changes export format or we refactor models, increment version and write migration scripts in `src/byesamosa/data/migrations.py`.

```python
class DailySleep(BaseModel):
    schema_version: int = 1             # For future migrations
    day: date
    score: int                          # 0-100
    # Contributors (0-100 each)
    deep_sleep_contrib: Optional[int]
    efficiency_contrib: Optional[int]
    latency_contrib: Optional[int]
    rem_sleep_contrib: Optional[int]
    restfulness_contrib: Optional[int]
    timing_contrib: Optional[int]
    total_sleep_contrib: Optional[int]
    # Raw values
    total_sleep_seconds: int
    rem_sleep_seconds: int
    deep_sleep_seconds: int
    light_sleep_seconds: int
    awake_seconds: int
    efficiency: float
    latency_seconds: int
    bedtime_start: datetime
    bedtime_end: datetime
    average_heart_rate: float
    average_hrv: float
    lowest_heart_rate: int
    average_breath: float

class DailyReadiness(BaseModel):
    schema_version: int = 1
    day: date
    score: int
    temperature_deviation: Optional[float]
    temperature_trend_deviation: Optional[float]
    # Contributors (0-100 each)
    activity_balance_contrib: Optional[int]
    body_temperature_contrib: Optional[int]
    hrv_balance_contrib: Optional[int]
    previous_day_activity_contrib: Optional[int]
    previous_night_contrib: Optional[int]
    recovery_index_contrib: Optional[int]
    resting_heart_rate_contrib: Optional[int]
    sleep_balance_contrib: Optional[int]

class DailyActivity(BaseModel):
    schema_version: int = 1
    day: date
    score: int
    active_calories: Optional[int]
    total_calories: Optional[int]
    steps: Optional[int]
    inactive_seconds: Optional[int]
    low_seconds: Optional[int]
    medium_seconds: Optional[int]
    high_seconds: Optional[int]
    rest_seconds: Optional[int]
    average_met: Optional[float]

class Baseline(BaseModel):
    schema_version: int = 1
    day: date
    metric: str
    avg_7d: Optional[float]
    avg_30d: Optional[float]
    avg_90d: Optional[float]
    stddev_30d: Optional[float]
```

**Baseline computation** via pandas (run after each import):
```python
df = pd.read_json("data/processed/daily_sleep.json")
df["avg_7d"] = df["score"].rolling(7, min_periods=1).mean()
df["avg_30d"] = df["score"].rolling(30, min_periods=1).mean()
df["avg_90d"] = df["score"].rolling(90, min_periods=1).mean()
df["stddev_30d"] = df["score"].rolling(30, min_periods=1).std()
```

Metrics tracked: `sleep_score`, `readiness_score`, `activity_score`, `average_hrv`, `lowest_heart_rate`, `deep_sleep_seconds`, `rem_sleep_seconds`, `total_sleep_seconds`, `efficiency`, `temperature_deviation`, `steps`, `active_calories`.

---

## Directory Structure

```
byesamosa/
├── pyproject.toml
├── .env                        # ANTHROPIC_API_KEY
├── .env.example
├── .gitignore
├── streamlit_app.py            # Streamlit dashboard entry point
│
├── src/byesamosa/
│   ├── __init__.py
│   ├── config.py               # pydantic-settings
│   ├── pipeline.py             # Orchestrator: import CSV → parse → AI
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── parser.py           # CSV → Pydantic models
│   │   ├── store.py            # JSON file read/write, dedup, upsert
│   │   ├── queries.py          # Baselines (pandas rolling), trends, lookups
│   │   └── models.py           # Pydantic data models
│   │
│   └── ai/
│       ├── __init__.py
│       ├── engine.py           # Claude API integration
│       ├── prompts.py          # Prompt templates
│       └── schemas.py          # AI output Pydantic models
│
├── tests/
│   ├── test_parser.py
│   ├── test_queries.py
│   └── test_ai_prompts.py
│
├── data/                       # .gitignored
│   ├── raw/
│   ├── processed/
│   ├── insights/
│   └── logs/
│
└── scripts/
    └── setup.sh
```

---

---

## AI Engine Design

**Approach:** Assemble a rich data context in Python, inject it into a structured prompt, let Claude reason over it.

**System prompt** establishes Claude as a personal sleep/recovery analyst:
- Provide reasoning chains (observation → physiological cause → actionable implication)
- Give specific recommendations ("Skip HIIT, do 30min yoga" not "prioritize recovery")
- Decompose scores into contributor impacts vs personal baselines
- Label each contributor as `boost` (≥85), `ok` (75-84), or `drag` (<75)
- Return structured JSON matching the AIInsight Pydantic schema

**Data context** includes: latest day's metrics, baselines (7d/30d/90d), last 7 days trend, contributor scores. Fits easily in <10K tokens.

**AI Output Schema** (what the frontend consumes):
```python
class ScoreInsight(BaseModel):
    """AI one-liner for a single score card."""
    one_liner: str              # e.g. "Deep sleep was your best in 2 weeks..."
    contributors: list[ContributorLabel]  # sorted best→worst

class ContributorLabel(BaseModel):
    name: str                   # e.g. "Latency", "REM Sleep"
    value: int                  # 0-100
    tag: Literal["boost", "ok", "drag"]

class ReasoningStep(BaseModel):
    label: str                  # "Observation" | "Cause" | "So what"
    text: str

class ActionItem(BaseModel):
    title: str                  # e.g. "Go hard if you have a workout planned"
    detail: str                 # e.g. "Readiness 90 + HRV rebound = full capacity..."
    priority: Literal["high", "medium", "low"]
    tag: str                    # e.g. "Fix REM", "Break trend", "Optional"

class ChartAnnotation(BaseModel):
    """AI callout for a chart or vital."""
    text: str                   # e.g. "Best in 10 days. Strong parasympathetic rebound..."

class TrendAnnotation(BaseModel):
    """AI annotation for a trend chart."""
    icon: str                   # e.g. "up", "down", "heart"
    text: str                   # e.g. "Upward trend for 10 days..."

class AIInsight(BaseModel):
    """Full AI output for a single briefing."""
    date: date
    score_insights: dict[str, ScoreInsight]  # keys: "sleep", "readiness", "activity"
    reasoning_chain: list[ReasoningStep]     # 3 steps
    actions: list[ActionItem]                # 3-4 items
    hypnogram_annotation: Optional[ChartAnnotation]  # Only if sleep phase data available
    vital_annotations: dict[str, ChartAnnotation]  # keys: "hrv", "rhr", "temp", "breath"
    trend_annotations: dict[str, TrendAnnotation]  # keys: "sleep_score", "hrv_rhr"
    good_looks_like: dict[str, str]          # keys: "sleep", "readiness", "activity"
```

**Caching:** Insights stored as JSON files in `data/insights/YYYY-MM-DD.json` (one per import). Dashboard reads cached insights; refresh button re-runs on demand with rate limiting (session-state timestamp check) and cost protection (max_tokens=4096, ~$0.05 per call).

**Cost Protection:**
- Set `max_tokens=4096` in Claude API calls (caps cost at ~$0.05/insight)
- Rate limit: Refresh button allows 1 request per 60 seconds (Streamlit session-state timestamp check)
- UI shows confirmation before regenerating
- Track monthly API spend in `data/logs/api_costs.json` (append timestamp + estimated cost per call)

---

## Implementation Phases

**Phase 1: Data Foundation**
- Project scaffolding (pyproject.toml, .env, directory structure)
- **Generate mock data** for development (30 days of realistic sleep/readiness/activity scores). Save to `data/processed/` as JSON. This allows dashboard development before real Oura export arrives.
- Pydantic data models (`data/models.py`) with schema versioning
- Manually download one Oura export to discover actual format (once available)
- Build parser (`data/parser.py`) — CSV/JSON → Pydantic models
- Build JSON store (`data/store.py`) — read/write/dedup processed files
- Build baseline queries (`data/queries.py`) — pandas rolling windows

**Phase 2: AI Engine**
- Data context assembly from processed JSON files
- Prompt templates with reasoning chain instructions
- Claude API call with structured JSON output
- Insight caching as JSON files

**Phase 3: ~~API Server~~ (Superseded)**
- ~~FastAPI routes wired to data store + insight files~~
- Replaced by Streamlit dashboard with direct data access. No API layer needed.

**Phase 4: Streamlit Dashboard**
- `streamlit_app.py` at project root with direct DataStore/queries access
- Score cards with `st.metric()` + Plotly radar charts (Scatterpolar)
- AI briefing with reasoning chain + action items (two-column layout)
- Vitals via `st.metric()` with deltas and AI annotations
- Trend charts via Plotly line charts (dual-axis HRV+RHR)
- Refresh insights button with session-state rate limiting
- Week/Month tabs for aggregated data views

**Phase 5: Pipeline & CLI**
- Wire orchestrator (`pipeline.py`) — CLI-driven import + AI insight generation
- `python -m byesamosa.pipeline import --file export.csv` runs full pipeline
- `python -m byesamosa.pipeline serve` launches Streamlit

**Phase 6 (Post-MVP): Playwright Automation**
- Gmail API integration for email OTP retrieval
- Playwright login flow with OTP
- Export request + readiness polling
- Automated download and import

---

## Key Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    "pandas>=2.2.0",
    "anthropic>=0.40.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
    "streamlit",
    "plotly",
]
# Post-MVP (Playwright automation):
# "playwright>=1.41.0",
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Export format differs from API docs | Use **mock data** to start development. Models are provisional with schema versioning. Raw CSVs are source of truth — can reparse if models change. |
| Export takes too long / is unreliable | Manual process — user controls when to request and import. Can request weekly. |
| Oura changes export flow or format | Schema versioning + migration scripts. Raw CSVs retained for reprocessing. |
| AI briefing quality is poor | Iterative prompt engineering; all prompts/responses stored for review |
| Runaway API costs | Rate limiting (1 req/min via session state), max_tokens cap (4096), confirmation dialog, cost tracking log |
| JSON files get large over years | Data is tiny (~365 rows/year). If it grows, migrate to DuckDB. |

---

## Verification

1. **Data pipeline:** Import a manual Oura export → verify data in processed JSON files → verify baselines compute correctly
2. **AI engine:** Run against real data → verify briefing contains reasoning chains and specific recommendations
3. **Dashboard:** `streamlit run streamlit_app.py` → verify all charts render with real data, header shows "Data as of <date>"
4. **End-to-end:** Import new CSV → verify fresh data + new AI insight appear in dashboard
