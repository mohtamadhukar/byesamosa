# Dashboard V2 — Workout Recovery Overlay

## Context

The dashboard currently answers "how did I sleep/recover/move?" with scores and AI briefings. But it doesn't help the user understand **cause and effect** (how workouts impact recovery). A new section fills this gap using data that's already collected but not visualized.

**Placement:** The section goes between Vitals and Trends — it's more detailed than vitals but less abstract than 30-day trend lines.

---

## Workout + Recovery Overlay

### Problem

Users don't know which workouts tank their recovery and which ones barely register. "Take a rest day" is generic advice without knowing your personal recovery patterns. The dashboard shows readiness scores and workout data separately — the connection between them is invisible.

### User Value

After a few weeks of data, patterns emerge visually:
- "Strength training drops my readiness by 15 points the next day"
- "Walking barely affects my recovery"
- "Back-to-back high-intensity days compound the readiness hit"

This turns vague feelings ("I think heavy lifting wrecks me") into data-backed training decisions. The chart is the evidence; the user draws their own conclusions.

### Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Time window** | 30 days | Enough history to see patterns, but not so much that the chart gets crowded. Matches the existing Trends section window. |
| **Data sources** | `DataStore.load_workouts()` + `DataStore.load_readiness()` | Both already exist. Workouts have `day`, `activity`, `calories`. Readiness has `day`, `score`. |
| **Chart type** | Plotly dual-axis: bar chart (workouts) + line chart (readiness) | Bars show workout intensity (calories burned). Line shows recovery impact. Overlaying them makes the cause-effect relationship visible. |
| **Workout grouping** | Color-coded by `activity` type | 6 activity types in the data. Color coding lets users visually correlate specific workout types with readiness drops. |
| **Readiness line** | Continuous daily readiness for the full 30-day window | Shows the full multi-day recovery arc — dips after workouts, how many days to recover, and compounding effects of back-to-back training. |
| **Missing workouts** | Days without workouts show no bar (gap in bars, line continues) | Rest days are just as informative — readiness should recover on rest days. |
| **Multiple workouts/day** | Stack bars (sum calories) | Rare but possible. Stacked bar preserves per-activity color coding. |
| **Missing calories** | Filter out workouts with `calories=None`, show count of excluded workouts in caption | `Workout.calories` is `Optional[float]`. Workouts without calorie data can't be meaningfully plotted on an intensity axis. Caption notes how many were excluded so the user knows data is incomplete. |
| **AI annotation** | Deferred | The chart itself shows the cause-effect relationship visually. AI annotation would require new plumbing across 4 files (schema, prompt, engine, dashboard) for uncertain value over what the chart already communicates. Can be added later — the `Optional[ChartAnnotation]` pattern is already established. |

### Data Confirmed

- **39 workouts** across **6 activity types** in `workouts.json`
- **100% have next-day readiness data** (verified — every workout day N has a readiness record for day N+1)
- Model: `Workout` — fields: `day`, `activity`, `calories`, `distance`, `intensity`, `start_datetime`, `end_datetime`
- Model: `DailyReadiness` — fields: `day`, `score`
- Store methods: `load_workouts()`, `load_readiness()`

### Implementation Outline

1. **New query helper** in `queries.py`: `get_workout_recovery_data(store, days=30)` — returns a dict with:
   - `workouts`: list of `{day, activity, calories}` dicts for the window (**excludes workouts with `calories=None`**)
   - `excluded_count`: int — number of workouts dropped due to missing calories
   - `readiness`: list of `{day, readiness}` dicts — continuous daily readiness for the full window
   - `activity_types`: sorted list of unique activity names (for legend/color mapping)
2. **Dashboard section** in `streamlit_app.py` (after Vitals, before Trends):
   - Guard: skip if no workout data
   - Header: `st.subheader("Workout & Recovery")`
   - Plotly figure with:
     - Bar traces: one per activity type, stacked, showing calories on left Y-axis
     - Line trace: continuous readiness score on right Y-axis
   - Caption explaining recovery arc visualization
   - If `excluded_count > 0`: caption noting how many workouts were excluded due to missing calorie data

### AI Annotation — Deferred

The workout/recovery AI annotation is deferred from this version. The chart communicates the cause-effect relationship visually; AI commentary can be added later using the same `Optional[ChartAnnotation]` pattern. No changes to schema, prompt, or engine are needed for this feature.

---

## Dashboard Layout (Updated)

```
┌─────────────────────────────────────────────┐
│  Header (date, data freshness)              │
├─────────────────────────────────────────────┤
│  Score Cards (Sleep / Readiness / Activity)  │
├─────────────────────────────────────────────┤
│  AI Briefing (reasoning chain + actions)     │
├─────────────────────────────────────────────┤
│  Vitals (HRV, RHR, Temp, Breath)            │
├─────────────────────────────────────────────┤
│  *** NEW: Workout & Recovery (overlay) ***   │
├─────────────────────────────────────────────┤
│  Trends (30-day score lines)                 │
└─────────────────────────────────────────────┘
```

---

## What This Design Does NOT Include

- **Workout recommendations** — the AI annotation spots patterns in the data, but specific training advice comes from the existing AI briefing actions.
- **Recovery prediction** — tempting but requires modeling. The overlay gives users raw data to draw their own conclusions first.

---

## Verification

- [x] Design doc explains the *why* (problem + user value) for the feature
- [x] References correct existing data methods: `load_workouts()`, `load_readiness()`
- [x] References correct existing models: `Workout`, `DailyReadiness`
- [x] Implementation outline specifies new code locations: `queries.py` helper + `streamlit_app.py` section
- [x] Placement decision (between Vitals and Trends) is documented with rationale
- [x] Fallback behavior defined for missing data
