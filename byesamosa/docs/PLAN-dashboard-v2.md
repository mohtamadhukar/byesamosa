# Dashboard V2 — Workout Recovery Overlay

## Context

The dashboard currently shows scores, AI briefings, vitals, and trends — but doesn't visualize workout-recovery cause/effect. The design doc (`docs/DESIGN-dashboard-v2.md`) specifies a new section between Vitals and Trends, using data that's already collected but not displayed.

## Files to Modify

| File | Changes |
|------|---------|
| `src/byesamosa/data/queries.py` | Add `get_workout_recovery_data()` |
| `streamlit_app.py` | Add Workout & Recovery dashboard section, update `load_data()` |

**Not modified** (AI annotation for workout/recovery deferred — no schema/prompt/engine changes needed).

---

## Step 1: Query Helpers (`queries.py`)

- [x] **1a. `get_workout_recovery_data(store, days=30)`** — append after `has_sleep_phases()`
  - Load `store.load_workouts()` + `store.load_readiness()`
  - **Filter out workouts with `calories=None`** — track excluded count
  - Filter remaining workouts to last `days` from latest workout date
  - Build readiness lookup `dict[date, int]` (day → score)
  - Build continuous readiness list for the full window (every day, not just workout days)
  - Return `{"workouts": [{day, activity, calories}], "readiness": [{day, readiness}], "activity_types": [sorted unique], "excluded_count": int}`

## Step 2: Dashboard (`streamlit_app.py`)

- [x] **2a. Update imports** — Add `get_workout_recovery_data`

- [x] **2b. Update `load_data()`** — Add:
  - `workout_recovery = get_workout_recovery_data(store)`
  - Expand return tuple; update unpacking

- [x] **2c. Workout & Recovery section** (insert between Vitals and Trends)
  - Guard: `if workout_recovery and workout_recovery.get("workouts"):`
  - Plotly dual-axis via `make_subplots(specs=[[{"secondary_y": True}]])`
  - Bar traces: one per activity type, stacked, showing calories on left Y-axis
  - Line trace: continuous readiness on right Y-axis (full 30-day window)
  - Caption explaining recovery arc visualization
  - If `workout_recovery["excluded_count"] > 0`: caption noting excluded workouts

## Step 3: Verification

- [x] **3a.** `python -c "from byesamosa.data.queries import get_workout_recovery_data"` — import check
- [x] **3b.** `streamlit run streamlit_app.py` — visual check: section renders between Vitals and Trends
- [x] **3c.** Verify existing cached insights still load without error (no schema changes made)
