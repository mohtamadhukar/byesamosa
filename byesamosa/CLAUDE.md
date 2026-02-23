# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ByeSamosa is a personal Oura Ring data analyzer that replaces the $7/month subscription with AI-powered insights. Users manually download CSV exports from Oura's Membership Hub and import them via CLI. A Streamlit dashboard provides health metrics and AI-generated recommendations powered by Claude API, accessing the data layer directly (no API intermediary).

## Development Commands

### Setup
```bash
# Install Python dependencies (use uv for fast package management)
uv sync

# Copy environment template and add your ANTHROPIC_API_KEY
cp .env.example .env

```

### Running the Application
```bash
# Start the Streamlit dashboard
streamlit run streamlit_app.py

# Or use the CLI
python -m byesamosa.pipeline serve

# Pull Oura export via browser automation
python -m byesamosa.pipeline pull
```

### Data Operations
```bash
# Pull Oura export via browser automation (requires playwright install chromium)
python -m byesamosa.pipeline pull
python -m byesamosa.pipeline pull --no-import
python -m byesamosa.pipeline pull --date 2026-02-23

# Import Oura CSV export (place exported CSVs in a dated directory under data/raw/)
python -m byesamosa.pipeline import --raw-dir data/raw/YYYY-MM-DD

# Compute/recompute baselines (rolling averages)
python -c "from byesamosa.data.store import DataStore; from byesamosa.data.queries import compute_baselines; from pathlib import Path; compute_baselines(DataStore(Path('data')))"
```

### Testing
```bash
# Run all tests (when test suite is implemented)
pytest tests/

# Run specific test file
pytest tests/test_queries.py

# Run with verbose output
pytest -v
```

## Architecture: Data Flow & Storage

### JSON-Based Storage (Not Database)

**Key Decision:** Data is stored as structured JSON files, not a database. This is intentional for a personal tool with small data volume (~365 rows/year).

```
data/
├── raw/                     # Untouched CSV exports from Oura
├── processed/               # Normalized JSON (source of truth for API)
│   ├── daily_sleep.json
│   ├── daily_readiness.json
│   ├── daily_activity.json
│   ├── sleep_phases.json    # 5-min intervals (conditional feature)
│   └── baselines.json       # Pre-computed rolling averages
├── insights/                # AI-generated briefings (one per import)
│   └── YYYY-MM-DD.json
└── logs/
    └── api_costs.json       # API spend tracking
```

**Why JSON?**
- Data is tiny (Oura generates ~1 row per day)
- Eliminates database setup complexity
- Files are human-readable and git-friendly for versioning
- Streamlit reruns on each interaction (no caching = no race conditions with import pipeline)

### Data Pipeline Flow

```
0. (Automated) python -m byesamosa.pipeline pull
   → Playwright logs into Oura, downloads export, extracts CSVs to data/raw/
   OR
1. (Manual) User downloads CSV from membership.ouraring.com/data-export
2. python -m byesamosa.pipeline import --file export.csv
   ↓
3. Parser: CSV → Pydantic models → JSON (upsert/dedup by day)
   ↓
4. Baseline computation: pandas rolling windows (7d/30d/90d)
   ↓
5. AI Engine: Claude API generates insight for latest day
   ↓
6. Cache insight as JSON in data/insights/
```

## Schema Versioning Strategy

**All Pydantic models include `schema_version: int = 1`**

This handles two scenarios:
1. **Oura changes export format** → Increment schema version, write migration script in `src/byesamosa/data/migrations.py`
2. **We refactor models** → Same process

Raw CSV exports are always retained in `data/raw/` so data can be reprocessed if schema changes.

## Conditional Features: Sleep Hypnogram (Deferred)

**Sleep hypnogram visualization is deferred from current scope.** The data layer supports sleep phase data (`has_sleep_phases()` in queries.py), but the Streamlit dashboard does not currently render it.

## AI Engine Cost Protection

**Rate limiting and token caps prevent runaway costs:**

1. Streamlit refresh button enforces 1 request per 60 seconds (session-state timestamp check)
2. `max_tokens=4096` cap in Claude API calls (~$0.05 per insight)
3. All API calls logged to `data/logs/api_costs.json` with timestamp + estimated cost

## Dashboard Design (Streamlit)

**Streamlit reruns the script on each interaction (no startup caching).**

This eliminates race conditions between the import pipeline and the dashboard:
- Streamlit reloads data from disk on each rerun → always fresh data
- Performance: Data is ~365 rows/year, JSON parse is negligible (~1ms)
- Dashboard calls DataStore/queries/AI engine directly — no API intermediary

## Baseline Computation (Pandas)

Baselines are computed via pandas rolling windows after each data import:

```python
# For each metric (sleep_score, readiness_score, etc.):
df = pd.DataFrame(records)
df["avg_7d"] = df[metric].rolling(7, min_periods=1).mean()
df["avg_30d"] = df[metric].rolling(30, min_periods=1).mean()
df["avg_90d"] = df[metric].rolling(90, min_periods=1).mean()
df["std_30d"] = df[metric].rolling(30, min_periods=1).std()
```

Tracked metrics: `sleep_score`, `readiness_score`, `activity_score`, `average_hrv`, `lowest_heart_rate`, `deep_sleep_duration`, `rem_sleep_duration`, `total_sleep_duration`, `efficiency`, `temperature_deviation`, `steps`, `active_calories`.

Baselines are saved to `data/processed/baselines.json` as a flat list of `Baseline` records.

## Project Status

**Phase 1 (Complete):** Project scaffolding, data models, mock data, DataStore, baseline queries
**Phase 2 (Complete):** AI engine (prompts, Claude API integration, insight caching)
**Phase 3 (Superseded):** API server — replaced by Streamlit direct data access. Code removed.
**Phase 4 (Complete):** Streamlit Dashboard (Streamlit + Plotly). Hypnogram deferred.
**Phase 5 (Complete):** Pipeline CLI orchestrator (`pipeline.py` and `importer.py`)
**Phase 6 (In Progress):** Playwright automation for export download (`pull` command, Gmail OTP)

See `docs/PLAN.md` for detailed implementation steps and dependencies.

## Key Files

- `docs/DESIGN.md`: Complete technical architecture and data models
- `docs/PLAN.md`: Step-by-step implementation plan with verification checkpoints
- `streamlit_app.py`: Streamlit dashboard entry point (calls data layer directly)
- `src/byesamosa/config.py`: Settings (loads from .env)
- `src/byesamosa/data/models.py`: Pydantic models with schema versioning
- `src/byesamosa/data/store.py`: JSON file read/write/upsert/dedup
- `src/byesamosa/data/queries.py`: Baseline computation + helper queries
- `src/byesamosa/pipeline.py`: CLI orchestrator (import, insights, serve, pull)
- `src/byesamosa/data/importer.py`: Oura CSV import pipeline
- `src/byesamosa/data/export_pull.py`: Playwright browser automation for Oura export download
- `src/byesamosa/data/gmail_otp.py`: Gmail IMAP OTP extraction for Oura login

## Environment Variables

- `ANTHROPIC_API_KEY`: Claude API key (required for AI insights)
- `OURA_EMAIL`: Oura account email (required for pull command)
- `GMAIL_OTP_EMAIL`: Gmail address for receiving Oura OTP codes
- `GMAIL_OTP_APP_PASSWORD`: Gmail App Password (16-char) for IMAP access
