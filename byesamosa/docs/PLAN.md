# ByeSamosa — Implementation Plan

> Generated from `docs/DESIGN.md`. Updated to reflect real Oura CSV integration (formerly tracked in `docs/CSV_INTEGRATION_PLAN.md`, now merged here).

---

## Phase 1: Project Scaffolding & Data Layer

### Step 1.1: Project setup
- **Files:** `pyproject.toml`, `.env.example`, `.gitignore`, `src/byesamosa/__init__.py`, `src/byesamosa/config.py`
- **Verification:** `uv sync` succeeds. `Settings` loads from `.env`.
- [x] Done

### Step 1.2: Directory structure for data
- **Files:** `data/raw/.gitkeep`, `data/processed/.gitkeep`, `data/insights/.gitkeep`, `data/logs/.gitkeep`, `data/logs/api_costs.json`
- [x] Done

### Step 1.3: Pydantic data models
- **Files:** `src/byesamosa/data/models.py`, `src/byesamosa/data/__init__.py`, `src/byesamosa/data/migrations.py`
- **v1 (provisional):** Created initial models with `schema_version=1` and provisional field names.
- **v2 (real CSV):** Models updated to match real Oura CSV export structure. Key changes:
  - [x] Add contributor sub-models: `SleepContributors`, `ReadinessContributors`, `ActivityContributors`, `ResilienceContributors`
  - [x] Update `DailySleep` (schema_version=2): `sleep_score` → `score`, add contributors, rename duration fields (`total_sleep_duration`, `rem_sleep_duration`, `deep_sleep_duration`, `light_sleep_duration`, `awake_time`), efficiency now 0-100, average_hrv now int, add `average_heart_rate`, `average_breath`, `time_in_bed`, `restless_periods`
  - [x] Update `DailyReadiness` (schema_version=2): `readiness_score` → `score`, add contributors, move `hrv_balance`/`recovery_index`/`sleep_balance` into contributors, add `temperature_trend_deviation`
  - [x] Update `DailyActivity` (schema_version=2): `activity_score` → `score`, add contributors, rename time fields, add `equivalent_walking_distance`, `inactivity_alerts`, `target_calories`, `target_meters`
  - [x] Add new models: `DailyStress`, `DailySpO2`, `DailyCardiovascularAge`, `Workout`, `DailyResilience`
  - [x] Keep unchanged: `SleepPhaseInterval`, `Baseline`
- [x] Done

### Step 1.4: Inspect actual Oura export
- **Discovery:** Real data at `~/Downloads/data/App Data/` — 24 semicolon-delimited CSVs with embedded JSON columns, covering 71 days (2025-12-02 to 2026-02-11). `sleepmodel.csv` has raw measurements, `dailysleep.csv` has scores + contributors — must merge by `day`.
- [x] Done

### Step 1.5: CSV parser
- **Files:** `src/byesamosa/data/parser.py`
- **Implementation:**
  - [x] `_read_csv(path) -> list[dict]` — semicolon-delimited, auto-parse JSON columns, empty strings → None
  - [x] Type coercion helpers: `_int_or_none()`, `_float_or_none()`, `_datetime_or_none()`
  - [x] `parse_daily_sleep(dailysleep_csv, sleepmodel_csv)` — merge by day, filter to `type=="long_sleep"`
  - [x] `parse_daily_readiness(csv_path)`
  - [x] `parse_daily_activity(csv_path)` — skip `met` and `class_5_min` columns
  - [x] `parse_daily_stress(csv_path)`
  - [x] `parse_daily_spo2(csv_path)` — flatten `spo2_percentage` JSON
  - [x] `parse_daily_cardiovascular_age(csv_path)`
  - [x] `parse_workouts(csv_path)`
  - [x] `parse_daily_resilience(csv_path)`
  - [x] `parse_sleep_phases(sleepmodel_csv)` — parse `sleep_phase_5_min` into intervals
  - [x] Top-level `parse_oura_export(export_dir) -> ParseResult` dataclass
- **Verified:** Sleep: 66, Readiness: 66, Activity: 68, Stress: 73, SpO2: 66, CardioAge: 65, Workouts: 36, Resilience: 50, SleepPhases: 6354
- [x] Done

### Step 1.6: JSON store (read/write/dedup)
- **Files:** `src/byesamosa/data/store.py`
- **Current state:** load/save/upsert for sleep, readiness, activity, sleep_phases.
- **Needs update for new types:**
  - [x] `load_stress/save_stress/upsert_stress` → `daily_stress.json` (dedup by day)
  - [x] `load_spo2/save_spo2/upsert_spo2` → `daily_spo2.json` (dedup by day)
  - [x] `load_cardiovascular_age/save_cardiovascular_age/upsert_cardiovascular_age` → `daily_cardiovascular_age.json` (dedup by day)
  - [x] `load_workouts/save_workouts/upsert_workouts` → `workouts.json` (dedup by `(day, start_datetime)`)
  - [x] `load_resilience/save_resilience/upsert_resilience` → `daily_resilience.json` (dedup by day)
- [x] Done

### Step 1.7: Baseline queries (pandas rolling windows)
- **Files:** `src/byesamosa/data/queries.py`
- **Current state:** `compute_baselines()`, `get_latest_day()`, `get_trends()`, `get_deltas()`, `has_sleep_phases()` all exist — but use v1 field names.
- **Needs update for v2 field names:**
  - [x] Update `metrics_config` in `compute_baselines`: field references must use v2 names (`score` not `sleep_score`, `total_sleep_duration` not `total_sleep_seconds`, etc.)
    - `"sleep_score": ("sleep", "score")`
    - `"readiness_score": ("readiness", "score")`
    - `"activity_score": ("activity", "score")`
    - `"average_hrv": ("sleep", "average_hrv")`
    - `"lowest_heart_rate": ("sleep", "lowest_heart_rate")`
    - `"deep_sleep_duration": ("sleep", "deep_sleep_duration")`
    - `"rem_sleep_duration": ("sleep", "rem_sleep_duration")`
    - `"total_sleep_duration": ("sleep", "total_sleep_duration")`
    - `"efficiency": ("sleep", "efficiency")`
    - `"temperature_deviation": ("readiness", "temperature_deviation")`
    - `"steps": ("activity", "steps")`
    - `"active_calories": ("activity", "active_calories")`
  - [x] Update `get_latest_day` — already returns `model_dump()` which uses v2 field names
  - [x] Update `get_trends` — update `metric_sources` dict field names
  - [x] Update `get_deltas` — `record.sleep_score` → `record.score`, etc.
- [x] Done

### Step 1.8: Mock data generator update
- **Files:** `scripts/generate_mock_json.py`
- **Current state:** Generates v1 data with `sleep_score`, `readiness_score`, `activity_score` field names.
- **Needs update:**
  - [ ] Rewrite to produce v2 model structure: `score` + contributor sub-models + renamed fields
  - [ ] Add generators for stress, spo2, cardiovascular_age, resilience data
- Partially done

### Phase 1 Checkpoint
> **Status:** Core data layer complete. Models and parser fully updated for real Oura CSV data. Store and queries need v2 field name updates. Mock data generator needs v2 update.

---

## Phase 2: AI Engine

### Step 2.1: AI output schemas
- **Files:** `src/byesamosa/ai/schemas.py`, `src/byesamosa/ai/__init__.py`
- `ContributorLabel`, `ScoreInsight`, `ReasoningStep`, `ActionItem`, `ChartAnnotation`, `TrendAnnotation`, `AIInsight`
- [x] Done

### Step 2.2: Prompt templates
- **Files:** `src/byesamosa/ai/prompts.py`
- **Current state:** `SYSTEM_PROMPT` and `build_user_prompt()` exist but use v1 field names.
- **Needs update for v2:**
  - [x] Score references: `sleep.get('sleep_score')` → `sleep.get('score')` (same for readiness, activity)
  - [x] Sleep metrics: `total_sleep_seconds` → `total_sleep_duration`
  - [x] Fix efficiency formatting: no longer multiply by 100 (already 0-100 in v2)
  - [x] Add contributor sections using real data from `sleep.get('contributors', {})`
  - [x] Add sections for stress, SpO2, cardiovascular age if present
  - [x] Update output requirements: "use ACTUAL contributor values from data"
  - [x] Update baseline metric key references
- [x] Done

### Step 2.3: Claude API integration
- **Files:** `src/byesamosa/ai/engine.py`
- **Current state:** `generate_insight()`, `cache_insight()`, `load_cached_insight()`, `log_api_cost()` all exist.
- **Needs update:**
  - [x] Update `_create_fallback_insight` contributor names to match real Oura names
  - [x] Adjust any field references in insight generation logic
- [x] Done

### Phase 2 Checkpoint
> **Status:** AI engine complete. All v2 field name updates done — prompts, contributors, baselines, fallback insight, and `get_latest_day()` now includes stress/SpO2/cardiovascular age.

---

## Phase 3: ~~API Server~~ (Superseded by Streamlit)

> Phase 3 originally implemented a FastAPI API server. Superseded by Streamlit dashboard (Phase 4) which accesses data layer directly. API code removed.

---

## Phase 4: Streamlit Dashboard

### Step 4.1: Add Streamlit and Plotly dependencies
- **Files:** `pyproject.toml` — add `streamlit`, `plotly`
- [x] Done

### Step 4.2: Create streamlit_app.py — data loading, header, tabs
- **Files:** `streamlit_app.py` (project root)
- Import DataStore, queries, AI engine directly. `@st.cache_data` for loading. Page config: wide layout. Tab structure: Today | Week | Month.
- [x] Done

### Step 4.3: Score cards — st.metric() + Plotly radar charts
- `st.columns(3)` for Sleep, Readiness, Activity. `st.metric()` + delta. Plotly `Scatterpolar` radar per card. AI one-liner + "good looks like" benchmark.
- [x] Done

### Step 4.4: AI briefing — reasoning chain + action items
- Left column: reasoning chain (observation → cause → so what). Right column: prioritized action items.
- [x] Done

### Step 4.5: Vitals — st.metric() with deltas and AI annotations
- `st.columns(4)` for HRV, RHR, Body Temp, Breathing Rate. Delta + AI context.
- [x] Done

### Step 4.6: Trend charts — Plotly line charts
- Sleep Score trend (30d). Dual-axis HRV + RHR overlay. Baseline band (30d avg +/- 1 stddev). AI trend annotation.
- [x] Done

### Step 4.7: Refresh insights — session-state rate limiting
- "Refresh Insights" button. 60s rate limit via `st.session_state`. Cost confirmation (~$0.05).
- [x] Done

### Step 4.8: Week/Month tabs — aggregated data views
- Week tab: 7-day averages. Month tab: 30-day averages. Reuse Plotly charts.
- [x] Done

### Phase 4 Checkpoint
> `streamlit run streamlit_app.py` → dashboard renders with data → score cards, AI briefing, vitals, and trend charts display correctly. ✅ Verified

---

## Phase 5: Pipeline & CLI

### Step 5.1: Import script
- **Files:** `src/byesamosa/data/importer.py` — **NEW**
- **Import pipeline flow:**
  ```
  data/raw/YYYY-MM-DD/*.csv (manually placed)
          │
          ▼
    1. PARSE: CSV → Pydantic (semicolon-delim, JSON cols)
          │
          ▼
    2. STORE: Upsert into data/processed/*.json
          │
          ▼
    3. COMPUTE: Recompute baselines (7d/30d/90d)
  ```
- [x] `import_oura_export(raw_dir: Path, data_dir: Path, refresh: bool = False) -> dict`
  1. Parse → `parse_oura_export()` on raw CSV directory
  2. Store → Default: upsert (merge by day/id, idempotent). `--refresh`: delete processed JSONs first, insert fresh.
  3. Compute → Recompute baselines
  4. Return summary dict with counts
- **Why upsert:** Each Oura export contains full history (~71 days). Upsert is idempotent and handles retroactive score corrections.
- **Raw storage convention:** `data/raw/YYYY-MM-DD/*.csv` — date of export, all CSVs flat in folder.

### Step 5.2: Pipeline CLI orchestrator
- **Files:** `src/byesamosa/pipeline.py`
- [x] CLI: `python -m byesamosa.pipeline import --raw-dir data/raw/2026-02-17 [--refresh]`
- [x] `serve` subcommand: `python -m byesamosa.pipeline serve` → launches Streamlit
- [x] `insights` subcommand: `python -m byesamosa.pipeline insights [--date YYYY-MM-DD]`
  - Default: generate insight for latest day in processed data
  - `--date`: generate insight for specific date
  - Flow: DataStore → get_latest_day() / get_trends() / has_sleep_phases() → generate_insight() → cache_insight() + log_api_cost()
  - Skips if cached insight already exists for that date (use --force to regenerate)

### Phase 5 Checkpoint
> Import fresh CSV → new data in processed files + baselines recomputed. `streamlit run streamlit_app.py` → dashboard shows fresh data.

---

## Phase 6: Tests & Setup

### Step 6.1: Update existing tests for v2
- **Files:** `tests/test_models.py`, `tests/test_store.py`, `tests/test_queries.py`, `tests/test_ai_engine.py`
- [ ] `test_models.py` — Rewrite for v2 field names, test contributor sub-models, test new model types
- [ ] `test_store.py` — Update fixtures, add tests for new type load/save/upsert
- [ ] `test_queries.py` — Update metrics_config references, field names in assertions
- [ ] `test_ai_engine.py` — Update fixtures with v2 model structure

### Step 6.2: New parser tests
- **Files:** `tests/test_parser.py` — **NEW**
- [ ] Create `tests/fixtures/` with small sample CSVs (3-5 rows, semicolon-delimited, with JSON)
- [ ] Test `_read_csv` helper
- [ ] Test each per-type parser
- [ ] Test sleepmodel merge (long_sleep preference, missing days, naps)
- [ ] Test `parse_oura_export` end-to-end
- [ ] Test missing optional CSV handling

### Step 6.3: Setup script
- **Files:** `scripts/setup.sh`
- [ ] `uv sync`, `.env` copy, data dir creation, verification

### Phase 6 Checkpoint
> `pytest tests/ -v` → all pass. `bash scripts/setup.sh` runs on clean clone.

---

## Phase 7: Documentation Update

- [ ] `CLAUDE.md` — Update field names, tracked metrics, project status
- [ ] `docs/PLAN.md` — Keep current (this file)

---

## Risks & Mitigations

1. **sleepmodel.csv has multiple rows per day** (naps + long_sleep) → Parser filters by `type=="long_sleep"`, falls back to longest duration
2. **dailyactivity.csv `met` column is huge JSON** (~1440 items/day) → Skipped in parser
3. **Existing processed JSON is incompatible** with schema v2 → Delete and regenerate via `--refresh`
4. **Contributor values can be null** (e.g., `hrv_balance: null` in early days) → All contributor fields are Optional
5. **queries.py uses v1 field names** (e.g., `record.sleep_score`) while models use v2 (`record.score`) → Must update before running with real data

---

## Current Priority: v2 Migration

The models and parser are v2-ready, but several downstream modules still reference v1 field names. These must be updated before the pipeline works end-to-end:

```
Step 1.6  store.py        — ✅ Add new type methods (stress, spo2, etc.)
Step 1.7  queries.py      — ✅ v2 field names + get_latest_day includes stress/spo2/cardio
Step 1.8  generate_mock   — Match v2 model structure
Step 2.2  prompts.py      — ✅ v2 field names, contributors, stress/spo2/cardio sections
Step 2.3  engine.py       — ✅ Fallback insight uses real Oura contributor names
Step 5.1  importer.py     — ✅ Import orchestrator created
Step 6.1  tests/*         — Update all test fixtures for v2
Step 6.2  test_parser.py  — Create parser test suite
```

---

## Not in Scope (Post-MVP)

- Playwright automation for Oura export download
- Gmail API for OTP
- DuckDB migration
- Authentication / multi-user
- Deployment beyond localhost
- Sleep hypnogram visualization (data layer supports it, dashboard deferred)
