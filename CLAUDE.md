# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ByeSamosa is a personal Oura Ring data analyzer that replaces the $7/month subscription with AI-powered insights. Users download CSV exports from Oura's Membership Hub (manually or via Playwright automation) and import them via CLI. A Next.js + Tailwind dashboard (warm editorial aesthetic) displays health metrics and AI-generated recommendations. A FastAPI backend exposes the Python data layer as REST endpoints.

## Development Commands

### Setup
```bash
# Install Python dependencies (use uv for fast package management)
uv sync

# Install frontend dependencies
cd frontend && npm install && cd ..

# Copy environment template and add your ANTHROPIC_API_KEY
cp .env.example .env
```

### Running the Application
```bash
# Start both FastAPI backend (port 8000) + Next.js frontend (port 3000)
uv run python -m byesamosa.pipeline serve

# Or run them separately:
uv run uvicorn byesamosa.api.main:app --reload    # FastAPI on :8000
cd frontend && npm run dev                         # Next.js on :3000

# Pull Oura export via browser automation
uv run python -m byesamosa.pipeline pull
```

### Data Operations
```bash
# Pull Oura export via browser automation (requires playwright install chromium)
uv run python -m byesamosa.pipeline pull
uv run python -m byesamosa.pipeline pull --no-import
uv run python -m byesamosa.pipeline pull --date 2026-02-23

# Import Oura CSV export (place exported CSVs in a dated directory under data/raw/)
uv run python -m byesamosa.pipeline import --raw-dir data/raw/YYYY-MM-DDThh-mm-ssTZ

# Compute/recompute baselines (rolling averages)
uv run python -c "from byesamosa.data.store import DataStore; from byesamosa.data.queries import compute_baselines; from pathlib import Path; compute_baselines(DataStore(Path('data')))"
```

### Testing
```bash
uv run pytest tests/
uv run pytest tests/test_queries.py
uv run pytest -v
```

## Architecture

### Stack
- **Frontend**: Next.js 16 (App Router) + Tailwind v4 + Recharts + Framer Motion
- **Backend**: FastAPI (thin wrapper over data layer) + Uvicorn
- **Data layer**: Pydantic models + JSON file storage + Pandas baselines
- **AI**: Claude API for daily health insights

### Frontend → Backend Communication
Next.js `next.config.ts` rewrites `/api/*` → `http://localhost:8000/api/*`, so frontend and backend appear same-origin (no CORS issues in dev).

### API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard` | GET | Scores, deltas, cached AI insight (above-the-fold) |
| `/api/trends?days=30` | GET | Sleep score, HRV, RHR time series |
| `/api/baselines?metric=sleep_score` | GET | Baseline band data for chart overlays |
| `/api/workouts?days=30` | GET | Workout bars + readiness line data |
| `/api/insights/refresh` | POST | Generate new AI insight (rate-limited 60s) |

### JSON-Based Storage (Not Database)

**Key Decision:** Data is stored as structured JSON files, not a database. This is intentional for a personal tool with small data volume (~365 rows/year).

```
data/
├── raw/                     # Untouched CSV exports from Oura (dirs named YYYY-MM-DDThh-mm-ssTZ)
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

### Data Pipeline Flow

```
0. (Automated) python -m byesamosa.pipeline pull
   → Playwright logs into Oura, downloads export, extracts CSVs to data/raw/
   OR
1. (Manual) User downloads CSV from membership.ouraring.com/data-export
2. python -m byesamosa.pipeline import --raw-dir data/raw/YYYY-MM-DDThh-mm-ssTZ
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

**All Pydantic models include `schema_version: int`**

This handles two scenarios:
1. **Oura changes export format** → Increment schema version, write migration script in `src/byesamosa/data/migrations.py`
2. **We refactor models** → Same process

Raw CSV exports are always retained in `data/raw/` so data can be reprocessed if schema changes.

## AI Engine Cost Protection

**Rate limiting and token caps prevent runaway costs:**

1. FastAPI insights endpoint enforces 1 request per 60 seconds (in-memory timestamp)
2. Frontend RefreshButton shows cooldown timer after each request
3. `max_tokens=4096` cap in Claude API calls (~$0.05 per insight)
4. All API calls logged to `data/logs/api_costs.json` with timestamp + estimated cost

## Frontend Design

**Aesthetic:** Warm editorial — cream backgrounds (#FDFBF7), serif headings (Playfair Display), clean sans body (DM Sans), warm amber/terracotta accents, generous whitespace, card-based layout with Framer Motion reveal animations.

**Dashboard sections (scroll order):**
1. Header + Refresh button
2. Score cards (Sleep, Readiness, Activity) with radar charts
3. AI Briefing (reasoning chain + action items)
4. Vitals (HRV, RHR, Body Temp, Breathing Rate)
5. Workout & Recovery (stacked bars + readiness line)
6. Trend charts (Sleep Score with baseline band, HRV + RHR dual-axis)

**Key decisions:**
- Client-side fetching (`'use client'` + `useEffect`) — personal tool, no SEO needed
- Recharts over Plotly (150KB vs 800KB, tree-shakeable)
- Parallel fetch on mount via `Promise.all` for all endpoints

## Baseline Computation (Pandas)

Baselines are computed via pandas rolling windows after each data import.

Tracked metrics: `sleep_score`, `readiness_score`, `activity_score`, `average_hrv`, `lowest_heart_rate`, `deep_sleep_duration`, `rem_sleep_duration`, `total_sleep_duration`, `efficiency`, `temperature_deviation`, `steps`, `active_calories`.

Baselines are saved to `data/processed/baselines.json` as a flat list of `Baseline` records.

## Project Status

**Phase 1 (Complete):** Project scaffolding, data models, DataStore, baseline queries
**Phase 2 (Complete):** AI engine (prompts, Claude API integration, insight caching)
**Phase 3 (Complete):** Pipeline CLI orchestrator (`pipeline.py` and `importer.py`)
**Phase 4 (Complete):** Playwright automation for export download (`pull` command, Gmail OTP)
**Phase 5 (Complete):** UI Revamp — Next.js + FastAPI replaces Streamlit + Plotly

## Key Files

**Backend (FastAPI):**
- `src/byesamosa/api/main.py`: FastAPI app, CORS, router includes
- `src/byesamosa/api/deps.py`: Dependency injection (DataStore + Settings)
- `src/byesamosa/api/routers/`: Endpoint handlers (dashboard, trends, baselines, workouts, insights)

**Data layer:**
- `src/byesamosa/config.py`: Settings (loads from .env)
- `src/byesamosa/data/models.py`: Pydantic models with schema versioning
- `src/byesamosa/data/store.py`: JSON file read/write/upsert/dedup
- `src/byesamosa/data/queries.py`: Baseline computation + helper queries

**Frontend (Next.js):**
- `frontend/app/page.tsx`: Main dashboard page (client component)
- `frontend/app/layout.tsx`: Root layout with fonts
- `frontend/components/`: All UI components (ScoreCard, AIBriefing, TrendCharts, etc.)
- `frontend/lib/types.ts`: TypeScript interfaces matching Python models
- `frontend/lib/api.ts`: Fetch wrappers for all endpoints

**Pipeline:**
- `src/byesamosa/pipeline.py`: CLI orchestrator (import, insights, serve, pull)
- `src/byesamosa/ai/engine.py`: Claude API insight generation + caching
- `src/byesamosa/ai/schemas.py`: AIInsight Pydantic model
- `src/byesamosa/data/importer.py`: Oura CSV import pipeline
- `src/byesamosa/data/export_pull.py`: Playwright browser automation

## Environment Variables

- `ANTHROPIC_API_KEY`: Claude API key (required for AI insights)
- `OURA_EMAIL`: Oura account email (required for pull command)
- `GMAIL_OTP_EMAIL`: Gmail address for receiving Oura OTP codes
- `GMAIL_OTP_APP_PASSWORD`: Gmail App Password (16-char) for IMAP access
