# ByeSamosa — Technical Architecture Design

## Context

Oura Ring 4 subscription costs $7/month but delivers shallow insights. The Oura app tells you WHAT happened but not WHY or WHAT to do. Goal: cancel the subscription and build a personal AI-powered dashboard using free Membership Hub data exports, with reasoning chains, personalized recommendations, and rich visualizations.

---

## Tech Stack

| Layer | Choice | Why |
|-------|--------|-----|
| **Backend** | Python + FastAPI | Data processing (pandas) + Anthropic SDK are best-in-class in Python. FastAPI gives async, auto-docs, Pydantic validation. |
| **Frontend** | React + Vite + Recharts | Component reuse for charts/gauges/sparklines. Vite = zero-config. No SSR needed (local tool). |
| **Storage** | Local JSON files + pandas | Start simple with flat files. Raw exports in `data/raw/`, parsed/normalized data in `data/processed/` as JSON. Pandas for analytics/baseline queries. Can migrate to DuckDB later if needed. |
| **AI** | Claude API (Anthropic Python SDK) | Structured output, strong reasoning for chains. Data context fits easily in context window. |
| **Data Import** | Manual CSV download + CLI | Oura export is async (up to 48h) with email OTP auth — full automation not feasible for MVP. User downloads CSV from Membership Hub, imports via CLI. Playwright automation deferred to post-MVP. |
| **Scheduling** | macOS launchd (or cron) | For AI insight regeneration on imported data. Data import itself is manual/on-demand. |
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
|                          |      API SERVER           |            |
|                          |      (FastAPI)            |            |
|                          +---------------------------+            |
|                                     |                             |
|                                     v                             |
|                          +---------------------------+            |
|                          |    FRONTEND DASHBOARD     |            |
|                          |    (React + Vite)         |            |
|                          +---------------------------+            |
+------------------------------------------------------------------+

    USER WORKFLOW:
      1. Request export at membership.ouraring.com/data-export
      2. Wait for email (up to 48h)
      3. Download CSV
      4. python -m byesamosa.pipeline import --file export.csv
      5. Open localhost:8000
```

---

## Data Flow

```
[User imports new data]
  python -m byesamosa.pipeline import --file ~/Downloads/oura_export.csv
    → Copy CSV to data/raw/
    → Data Engine: parse CSV, normalize, save to data/processed/
    → Data Engine: recompute baselines (pandas rolling windows)
    → AI Engine: generate briefing + recommendations for latest day
    → Store insight as JSON in data/insights/

[User opens browser → http://localhost:8000]
  → React app loads
  → Fetches /api/today → scores + raw metrics
  → Fetches /api/insights/today → AI briefing
  → Fetches /api/trends?days=30 → sparkline data
  → Fetches /api/sleep/hypnogram → sleep stages
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
├── insights/                     # AI-generated insights (one file per day)
│   ├── 2025-02-12-morning.json
│   └── 2025-02-12-evening.json
│
└── logs/
```

**How it works:**
- Parser reads raw exports → normalizes into Pydantic models → appends/upserts into the processed JSON files (dedup by `day` field)
- Baselines computed via pandas: `df.rolling(window=30).mean()` etc.
- API server loads processed JSON files into pandas DataFrames on startup (data is small — a year of daily data is ~365 rows)
- On new import, DataFrames are refreshed

---

## Data Models (Pydantic)

```python
class DailySleep(BaseModel):
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
│
├── src/byesamosa/
│   ├── __init__.py
│   ├── config.py               # pydantic-settings
│   ├── pipeline.py             # Orchestrator: scrape → parse → AI
│   │
│   ├── data/
│   │   ├── __init__.py
│   │   ├── parser.py           # CSV → Pydantic models
│   │   ├── store.py            # JSON file read/write, dedup, upsert
│   │   ├── queries.py          # Baselines (pandas rolling), trends, lookups
│   │   └── models.py           # Pydantic data models
│   │
│   ├── ai/
│   │   ├── __init__.py
│   │   ├── engine.py           # Claude API integration
│   │   ├── prompts.py          # Prompt templates
│   │   └── schemas.py          # AI output Pydantic models
│   │
│   └── api/
│       ├── __init__.py
│       ├── server.py           # FastAPI app
│       └── routes.py           # Endpoint definitions
│
├── tests/
│   ├── test_parser.py
│   ├── test_queries.py
│   └── test_ai_prompts.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── components/
│       │   ├── ScoreGauge.tsx
│       │   ├── RadarChart.tsx
│       │   ├── TrendSparkline.tsx
│       │   ├── SleepHypnogram.tsx
│       │   ├── BaselineComparison.tsx
│       │   ├── AIBriefingCard.tsx
│       │   └── MetricCard.tsx
│       ├── hooks/useApi.ts
│       └── types/index.ts
│
├── data/                       # .gitignored
│   ├── raw/
│   ├── processed/
│   ├── insights/
│   └── logs/
│
└── scripts/
    ├── setup.sh
    └── com.byesamosa.morning.plist
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/today` | Today's sleep, readiness, activity scores + raw metrics |
| GET | `/api/baselines?date=YYYY-MM-DD` | All baseline comparisons for a date |
| GET | `/api/trends?metric=X&days=N` | Time series for a metric (7/30/90d) |
| GET | `/api/sleep/hypnogram?date=YYYY-MM-DD` | 5-min interval sleep phase data |
| GET | `/api/insights/today` | AI briefing, recommendations, score decomposition |
| POST | `/api/insights/regenerate` | Re-run AI engine for today |
| GET | `/api/scores/contributors?type=sleep&date=YYYY-MM-DD` | Contributor breakdown for radar chart |

FastAPI serves both the API (`/api/*`) and the built React frontend (static files at `/`).

---

## AI Engine Design

**Approach:** Assemble a rich data context in Python, inject it into a structured prompt, let Claude reason over it.

**System prompt** establishes Claude as a personal sleep/recovery analyst:
- Provide reasoning chains (observation → physiological explanation → actionable implication)
- Give specific recommendations ("Skip HIIT, do 30min yoga" not "prioritize recovery")
- Decompose scores into contributor impacts vs personal baselines
- Return structured JSON matching the AIInsight Pydantic schema

**Data context** includes: today's metrics, baselines (7d/30d/90d), last 7 days trend, contributor scores. Fits easily in <10K tokens.

**Caching:** Insights stored as JSON files in `data/insights/YYYY-MM-DD-{morning|evening}.json`. Dashboard reads cached insights; `/api/insights/regenerate` re-runs on demand.

---

## Data Import Strategy

**MVP: Manual CSV import**
- User requests export at https://membership.ouraring.com/data-export
- Oura prepares CSV (up to 48 hours), emails when ready
- User downloads CSV, imports via CLI: `python -m byesamosa.pipeline import --file /path/to/export.csv`
- Parser handles CSV → Pydantic models → processed JSON

**Why not Playwright automation (for now):**
- Oura uses **email OTP** authentication (no password login) — requires reading a 6-digit code from email
- Export is **async** (up to 48 hours) — can't scrape-and-download in one run
- Would need: Gmail API for OTP retrieval + polling loop to check export readiness
- Deferred to post-MVP; manual import is simple and reliable

**Post-MVP: Semi-automated pipeline**
- Gmail API to read OTP → Playwright to complete login → request export → Gmail API to detect "export ready" email → Playwright to download
- Or: Oura API if subscription is maintained (Ring 4 requires paid sub for API access)

---

## Implementation Phases

**Phase 1: Data Foundation**
- Project scaffolding (pyproject.toml, .env, directory structure)
- Pydantic data models (`data/models.py`)
- Download first Oura CSV export (requested 2026-02-12, pending) and map actual columns to models
- Build parser (`data/parser.py`) — CSV → Pydantic models
- Build JSON store (`data/store.py`) — read/write/dedup processed files
- Build baseline queries (`data/queries.py`) — pandas rolling windows
- Build CLI import command (`pipeline.py`) — `python -m byesamosa.pipeline import --file export.csv`

**Phase 3: AI Engine**
- Data context assembly from processed JSON files
- Prompt templates with reasoning chain instructions
- Claude API call with structured JSON output
- Insight caching as JSON files

**Phase 4: API Server**
- FastAPI routes wired to data store + insight files
- Static file serving for frontend

**Phase 5: Frontend Dashboard**
- Score gauges (circular, color-coded to baselines)
- Radar chart (score contributors)
- Today-vs-average bars
- Sleep hypnogram
- Trend sparklines
- AI briefing card

**Phase 6: Pipeline & Scheduling**
- Wire orchestrator (`pipeline.py`) — CLI-driven import + AI insight generation
- Optional: launchd to regenerate AI insights daily if new data was imported

**Phase 7 (Post-MVP): Playwright Automation**
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
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "pandas>=2.2.0",
    "anthropic>=0.40.0",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.1.0",
    "python-dotenv>=1.0.0",
]
# Post-MVP (Playwright automation):
# "playwright>=1.41.0",
```

Frontend: `react`, `recharts`, `@nivo/radar`, `tailwindcss`

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Oura export format differs from API docs | Phase 1: inspect actual CSV once first export downloads (requested 2026-02-12) |
| Export takes too long / is unreliable | Manual process — user controls when to request and import. Can request weekly. |
| Oura changes export flow or removes it | Manual import fallback always works as long as you have CSV data |
| AI briefing quality is poor | Iterative prompt engineering; all prompts/responses stored for review |
| JSON files get large over years | Data is tiny (~365 rows/year). If it grows, migrate to DuckDB. |

---

## Verification

1. **Data import:** `python -m byesamosa.pipeline import --file export.csv` → verify CSV parsed → data in processed JSON files → baselines compute correctly
2. **AI engine:** Run against real data → verify briefing contains reasoning chains and specific recommendations
3. **API:** `curl localhost:8000/api/today` → verify JSON shape matches spec
4. **Dashboard:** Open `localhost:8000` → verify all charts render with real data
5. **End-to-end:** Import new CSV → verify fresh data + new AI insights appear in dashboard
