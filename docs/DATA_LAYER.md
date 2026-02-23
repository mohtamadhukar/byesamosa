# Data Layer (`src/byesamosa/data/`) & AI Insights (`src/byesamosa/ai/`)

This document explains how the data layer and AI insight system work for developers new to the codebase.

## Overview

The data layer handles the full lifecycle of Oura Ring health data, and the AI layer generates personalized insights from it:

```
Oura CSV export  -->  parser.py  -->  Pydantic models  -->  store.py  -->  JSON files on disk
                                                                              |
                                                            queries.py  <-----+
                                                         (baselines, trends, deltas)
                                                                              |
                                                            engine.py   <-----+
                                                         (Claude API → cached insights)
```

There are five data-layer files and three AI-layer files:

| File | Role |
|---|---|
| `data/models.py` | Pydantic models defining the shape of every data type |
| `data/parser.py` | Reads Oura's semicolon-delimited CSV exports into Pydantic models |
| `data/store.py` | Reads/writes processed JSON files, handles upsert and dedup |
| `data/queries.py` | Analytics: rolling baselines, trends, deltas for the dashboard |
| `data/migrations.py` | Placeholder for future schema migrations |
| `ai/schemas.py` | Pydantic models for AI-generated insights |
| `ai/prompts.py` | System prompt and user prompt builder for Claude API |
| `ai/engine.py` | Claude API call, retry, caching, and cost tracking |

## models.py

All data types are Pydantic `BaseModel` subclasses with `schema_version` for forward compatibility. Every field except `day` is `Optional` because Oura can leave any field blank.

### Contributor sub-models

Four nested models represent Oura's breakdown of how a score was calculated:

- **`SleepContributors`** (7 sub-scores): deep_sleep, efficiency, latency, rem_sleep, restfulness, timing, total_sleep
- **`ReadinessContributors`** (9 sub-scores): activity_balance, body_temperature, hrv_balance, previous_day_activity, previous_night, recovery_index, resting_heart_rate, sleep_balance, sleep_regularity
- **`ActivityContributors`** (6 sub-scores): meet_daily_targets, move_every_hour, recovery_time, stay_active, training_frequency, training_volume
- **`ResilienceContributors`** (3 sub-scores): daytime_recovery, sleep_recovery, stress

### Core daily models

| Model | Source CSV(s) | Key fields |
|---|---|---|
| `DailySleep` | dailysleep.csv + sleepmodel.csv | score, contributors, durations (total/rem/deep/light/awake), HRV, heart rate, breath, efficiency, temperature_deviation, bedtime timestamps |
| `DailyReadiness` | dailyreadiness.csv | score, contributors, temperature_deviation/trend |
| `DailyActivity` | dailyactivity.csv | score, contributors, steps, calories, activity time breakdowns |
| `DailyStress` | dailystress.csv | day_summary (restored/normal/stressful), recovery_high, stress_high (seconds) |
| `DailySpO2` | dailyspo2.csv | breathing_disturbance_index, spo2_average (flattened from JSON) |
| `DailyCardiovascularAge` | dailycardiovascularage.csv | vascular_age |
| `Workout` | workout.csv | activity, calories, distance, start/end datetime, intensity, label, source |
| `DailyResilience` | dailyresilience.csv | level (limited/adequate/solid/strong/exceptional), contributors |
| `SleepPhaseInterval` | sleepmodel.csv | timestamp, phase (awake/rem/light/deep), duration_seconds (always 300 = 5 min) |
| `Baseline` | computed by queries.py | metric name, 7d/30d/90d rolling averages, 30d standard deviation |

### Units

- All durations are in **seconds** (e.g., `total_sleep_duration=22590` = 6.3 hours)
- Temperature deviation is in **degrees Celsius** (e.g., `-0.39`)
- Distance is in **meters**
- Contributor sub-scores are integers in range **[0, 100]**

## parser.py

Converts Oura's CSV export files into Pydantic model instances.

### CSV format

Oura exports use **semicolon delimiters** (not commas) and embed **JSON objects** in some cells. For example, a row in dailysleep.csv looks like:

```
id;contributors;day;score;timestamp
abc-123;{"deep_sleep": 95, "efficiency": 65, ...};2025-12-03;71;2025-12-03T00:00:00.000+00:00
```

The base reader `_read_csv()` handles this: it auto-detects JSON cells (strings starting with `{`) and parses them into Python dicts. Empty strings become `None`.

### Sleep parsing: the two-source merge

This is the most complex part of the parser. Oura splits sleep data across **two files** that correspond to two separate API endpoints:

| File | API endpoint | What it contains |
|---|---|---|
| `dailysleep.csv` | `/v2/usercollection/daily_sleep` | One row per day: sleep **score** and **contributor** sub-scores |
| `sleepmodel.csv` | `/v2/usercollection/sleep` | One row per **sleep session**: raw metrics (durations, HRV, HR, breath, efficiency, bedtime timestamps, sleep phases) |

A single day can have multiple sleepmodel rows -- a primary nighttime sleep (`type=long_sleep`) and naps (`type=sleep`). The parser merges them into one `DailySleep` record per day:

1. **Index dailysleep by day** -- simple dict lookup
2. **Group sleepmodel by day, pick the best row:**
   - Prefer `type == "long_sleep"` over naps
   - If multiple long_sleep rows exist, pick the one with the longest `total_sleep_duration`
3. **Merge by day key:**
   - From dailysleep: `score` and `contributors`
   - From the winning sleepmodel row: all raw metrics
   - Special: `temperature_deviation` is extracted from a nested `readiness` JSON column inside sleepmodel (e.g., `{"score": 84, "temperature_deviation": -0.39}`)

The `day` field means "the day you woke up" in both files. A sleep session starting at 23:37 on Dec 3 and ending at 07:24 on Dec 4 has `day=2025-12-04` in both CSVs.

**Nap data is intentionally discarded.** Oura's daily sleep score only reflects the primary sleep session.

### Sleep phase parsing

A separate function reads sleepmodel.csv again for hypnogram data:

- Only processes `long_sleep` rows
- Reads `sleep_phase_5_min` -- a string like `"42211111112332..."` where each digit is a 5-minute bucket:
  - `1` = deep, `2` = light, `3` = rem, `4` = awake
- Starting from `bedtime_start`, generates one `SleepPhaseInterval` per digit, timestamped 5 minutes apart
- 96 digits = 8-hour sleep session at 5-minute resolution

### Other parsers

All other data types follow a simple pattern: read one CSV, map columns to one Pydantic model per row. Notable quirks:

- **SpO2**: `spo2_percentage` column contains JSON (`{"average": 98.5}`), parser flattens it to `spo2_average`
- **Readiness**: nested `contributors` JSON with 9 sub-scores
- **Activity**: nested `contributors` JSON with 6 sub-scores; skips `met` and `class_5_min` columns (large time-series not needed)
- **Resilience**: nested `contributors` JSON with 3 float sub-scores

### Orchestrator

`parse_oura_export(export_dir)` ties everything together:

- **Required files** (raises `FileNotFoundError` if missing): dailysleep.csv, sleepmodel.csv, dailyreadiness.csv, dailyactivity.csv
- **Optional files** (skipped if missing): dailystress.csv, dailyspo2.csv, dailycardiovascularage.csv, workout.csv, dailyresilience.csv
- Returns a `ParseResult` dataclass with all parsed lists
- Every individual row is wrapped in try/except so one bad row doesn't kill the import

## store.py

`DataStore` is a thin JSON read/write layer. It manages the `data/processed/` directory.

### Operations

Each data type has three methods:

- **`load_*()`** -- Read JSON file, return list of Pydantic model instances. Returns empty list if file doesn't exist.
- **`save_*()`** -- Serialize models to JSON, sorted by day. Overwrites the file.
- **`upsert_*()`** -- Load existing data, merge with new records (new wins on day conflicts), save. This is how re-imports work without duplicating data.

### Dedup keys

| Data type | Dedup key |
|---|---|
| Sleep, Readiness, Activity | `day` |
| Stress, SpO2, Cardiovascular Age, Resilience | `day` |
| Workouts | `(day, start_datetime)` tuple |
| Sleep phases | `(day, timestamp)` tuple |

### File layout

```
data/processed/
  daily_sleep.json
  daily_readiness.json
  daily_activity.json
  daily_stress.json
  daily_spo2.json
  daily_cardiovascular_age.json
  workouts.json
  daily_resilience.json
  sleep_phases.json
  baselines.json        # written by queries.py, not store.py
```

## queries.py

Analytics functions that power the Streamlit dashboard.

### `compute_baselines(store)`

Computes rolling window statistics for 12 tracked metrics:

| Metric | Source |
|---|---|
| sleep_score, average_hrv, lowest_heart_rate, deep_sleep_duration, rem_sleep_duration, total_sleep_duration, efficiency, temperature_deviation | Sleep records |
| readiness_score | Readiness records |
| activity_score, steps, active_calories | Activity records |

For each metric, computes:
- **7-day rolling average** (recent trend)
- **30-day rolling average** (monthly baseline)
- **90-day rolling average** (long-term baseline)
- **30-day rolling standard deviation** (variability)

Results are saved to `data/processed/baselines.json`.

### `get_latest_day(store)`

Returns the most recent day's sleep, readiness, and activity data as a dict. Used by the dashboard header cards.

### `get_trends(store, metric, days=30)`

Returns time-series data for a single metric over the last N days. Returns `[{day, value}, ...]` for charting.

### `get_deltas(store, target_date)`

Computes "today vs 30-day average" deltas for the three primary scores (sleep, readiness, activity). Used for the "+5 above average" style indicators on the dashboard.

### `has_sleep_phases(store)`

Simple check for whether sleep phase interval data exists. Used to conditionally show the hypnogram section in the dashboard.

## AI Insights (`src/byesamosa/ai/`)

The AI layer generates personalized daily health insights using Claude API. There are three files:

| File | Role |
|---|---|
| `schemas.py` | Pydantic models defining the shape of AI-generated insights |
| `prompts.py` | System prompt and user prompt builder |
| `engine.py` | Claude API call, retry logic, caching, and cost tracking |

### schemas.py

`AIInsight` is the top-level model cached as one JSON file per day (`data/insights/YYYY-MM-DD.json`). It contains:

| Field | Type | Purpose |
|---|---|---|
| `date` | str | Target date |
| `score_insights` | dict[str, ScoreInsight] | Per-score cards for Sleep, Readiness, Activity |
| `reasoning_chain` | list[ReasoningStep] | 3-step chain: Observation → Cause → So what |
| `actions` | list[ActionItem] | 3-4 prioritized recommendations |
| `hypnogram_annotation` | Optional[ChartAnnotation] | Sleep phase insight (only if phase data exists) |
| `vital_annotations` | dict[str, ChartAnnotation] | Context for HRV, RHR, temp, breath vitals |
| `trend_annotations` | list[TrendAnnotation] | Trend chart insights with up/down/heart icons |
| `good_looks_like` | dict[str, str] | Personalized benchmarks based on user's own data |

Supporting models:

- **`ScoreInsight`** -- one per score (sleep/readiness/activity): a `one_liner` summary plus a list of `ContributorLabel` objects
- **`ContributorLabel`** -- name, value (0-100), and a tag: `"boost"` (≥85), `"ok"` (75-84), or `"drag"` (<75)
- **`ReasoningStep`** -- label ("Observation" / "Cause" / "So what") + text
- **`ActionItem`** -- title, detail, priority (high/medium/low), and a category tag (e.g., "Fix REM", "Prevent injury")
- **`ChartAnnotation`** -- simple text callout for a chart
- **`TrendAnnotation`** -- icon ("up"/"down"/"heart") + text

### prompts.py

Two components build the Claude API messages:

**`SYSTEM_PROMPT`** (~434 tokens) establishes Claude as a personal sleep/recovery analyst. Key instructions:
- Label each contributor as boost/ok/drag using the thresholds above
- Follow a 3-step reasoning chain (observation → cause → so what)
- Emphasize personalization over generic health advice

**`build_user_prompt(latest, baselines, trends_7d, has_phases)`** (~863 tokens) constructs a structured data payload:

1. Latest day's scores (sleep, readiness, activity)
2. Sleep metrics -- durations as hours, efficiency %, HRV, RHR, breath rate, temp deviation
3. Contributor breakdowns with pre-computed boost/ok/drag tags
4. Stress, SpO2, cardiovascular age (if available)
5. Baseline statistics (7d/30d/90d rolling averages)
6. Last 7 days of score history
7. Output format instructions matching the `AIInsight` JSON schema

### engine.py

**`generate_insight(latest, baselines, trends_7d, has_sleep_phases, settings)`** is the core function:

1. Builds messages from `SYSTEM_PROMPT` + `build_user_prompt()`
2. Calls Claude API (model: `claude-sonnet-4-5-20250929`, `max_tokens=4096`)
3. Parses JSON response into `AIInsight` via Pydantic validation
4. **Retry on validation failure:** sends the Pydantic error back to Claude and retries once
5. **Fallback:** returns a placeholder `AIInsight` with "Unable to generate" messages if the API call fails entirely

### Insight caching

- **`cache_insight(insight, data_dir)`** -- writes `AIInsight` to `data/insights/YYYY-MM-DD.json`
- **`load_cached_insight(target_date, data_dir)`** -- returns cached `AIInsight` or `None` if not found / invalid

One insight per day. The dashboard checks for a cached insight first and only calls the API if none exists (or if the user forces a refresh).

### Cost tracking

- **`estimate_cost(input_tokens, output_tokens, model)`** -- computes USD cost from token counts
- **`log_api_cost(data_dir, timestamp, estimated_cost, model)`** -- appends to `data/logs/api_costs.json`

Pricing (Claude Sonnet 4.5): $3/1M input tokens, $15/1M output tokens. With the 4096 max_tokens cap, each insight costs ~$0.05.

### File layout

```
data/
├── insights/
│   └── YYYY-MM-DD.json     # Cached AIInsight (one per day)
└── logs/
    └── api_costs.json       # Append-only cost log
```
