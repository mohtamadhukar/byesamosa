# Step 2.3 Implementation: Claude API Integration

**Status:** ✅ Complete

**Date:** February 14, 2026

## Overview

Implemented the AI engine for generating personalized insights using Claude API. This completes both Step 2.2 (prompts) and Step 2.3 (API integration) from PLAN.md.

## Files Created

### 1. `src/byesamosa/ai/prompts.py` (Step 2.2)

Prompt engineering module that builds structured prompts for Claude API.

**Key Components:**

- `SYSTEM_PROMPT`: Establishes Claude as a personal sleep/recovery analyst with specific instructions for:
  - Reasoning chains (observation → cause → so what)
  - Contributor labeling (boost/ok/drag thresholds)
  - Personalized benchmarks based on user's baseline data
  - Structured JSON output matching AIInsight schema

- `build_user_prompt()`: Assembles data context into formatted sections:
  - Latest day scores and raw metrics
  - Sleep metrics (total/REM/deep/light sleep, efficiency, HRV, RHR, temperature)
  - Activity metrics (steps, active calories)
  - Baseline statistics (7d/30d/90d rolling averages)
  - 7-day score trends
  - Detailed output format requirements

- `format_baselines_for_prompt()`: Helper to convert baseline list to metrics-first dict

**Prompt Quality:**
- Size: ~863 tokens (well under 10K limit)
- Includes actual data values and personalized baselines
- Clear section structure for Claude to parse
- Conditional handling for sleep phase data availability

### 2. `src/byesamosa/ai/engine.py` (Step 2.3)

Core AI engine with Claude API integration, caching, and cost protection.

**Key Functions:**

#### `generate_insight()`
Main function that generates AI insights:
- Builds prompt using `build_user_prompt()`
- Calls Claude API with `claude-sonnet-4-5-20250929` model
- **Cost protection: `max_tokens=4096`** (caps cost at ~$0.05/call)
- Validates response against `AIInsight` schema
- **Retry logic:** On validation failure, retries once with error feedback
- **Fallback:** Returns basic fallback insight if API fails completely

#### `cache_insight()`
Saves insights to `data/insights/YYYY-MM-DD.json`:
- JSON serialization with proper date handling
- Creates insights directory if needed
- Overwrites existing files (for regeneration)

#### `load_cached_insight()`
Loads cached insights from disk:
- Returns `AIInsight` object if found
- Returns `None` if missing or validation fails
- Handles JSON parse errors gracefully

#### `log_api_cost()`
Tracks API spend in `data/logs/api_costs.json`:
- Appends timestamped cost entries
- Includes model name and estimated cost
- Creates logs directory if needed

#### `estimate_cost()`
Estimates API call cost based on token counts:
- Pricing: $3/1M input tokens, $15/1M output tokens (Claude Sonnet 4.5)
- Returns cost in USD

#### `_create_fallback_insight()`
Generates minimal fallback insight when API fails:
- Maintains valid AIInsight schema structure
- Placeholder content indicating API error
- Allows dashboard to render gracefully

**Error Handling:**
- Catches JSON decode errors
- Catches Pydantic validation errors
- Retry logic with error feedback
- Graceful fallback to avoid breaking the pipeline

**Cost Protection:**
- Hard limit: `max_tokens=4096`
- Estimated cost per call: ~$0.05
- All calls logged to `api_costs.json`
- No silent runaway costs

## Verification

Created two test scripts:

### 1. `scripts/verify_ai_engine.py`

Verifies implementation without making API calls:
- ✓ Module imports
- ✓ System prompt quality
- ✓ Mock data loading
- ✓ Baseline formatting
- ✓ Trend loading
- ✓ Sleep phase detection
- ✓ Prompt generation (863 tokens)
- ✓ Fallback insight creation
- ✓ Caching and loading
- ✓ Cost logging
- ✓ Prompt quality checks

**All tests passed.**

### 2. `scripts/test_ai_engine.py`

Full end-to-end test with real Claude API:
- Loads mock data
- Generates insight via Claude API
- Displays generated content:
  - Score insights with contributors
  - Reasoning chain (3 steps)
  - Action items (3-4 items)
  - Vital annotations
  - Trend annotations
  - "Good looks like" benchmarks
  - Hypnogram annotation (if available)
- Caches insight
- Logs API cost

**Note:** Requires `ANTHROPIC_API_KEY` in `.env` file.

## Data Flow

```
Mock Data (data/processed/)
    ↓
get_latest_day() + get_trends() + baselines
    ↓
format_baselines_for_prompt()
    ↓
build_user_prompt() → ~863 tokens
    ↓
Claude API (claude-sonnet-4-5, max_tokens=4096)
    ↓
JSON response validation (with retry)
    ↓
AIInsight object
    ↓
cache_insight() → data/insights/YYYY-MM-DD.json
    ↓
log_api_cost() → data/logs/api_costs.json
```

## Integration Points

### Phase 3: API Server (Next)
- `/api/insights/latest` → calls `load_cached_insight()`
- `/api/insights/regenerate` → calls `generate_insight()` with rate limiting

### Phase 5: Pipeline CLI
- Import command → calls `generate_insight()` after data import
- Automatically caches new insight
- Logs cost to track monthly spend

## Cost Protection Features

1. **Token Cap:** `max_tokens=4096` hard limit
2. **Cost Logging:** All calls logged with timestamp + estimated cost
3. **Rate Limiting:** (To be implemented in API server)
   - 1 request per 60 seconds for `/api/insights/regenerate`
   - UI shows confirmation dialog before regenerating
4. **Estimated Cost:** ~$0.05 per insight generation
5. **Monthly Tracking:** All costs logged to JSON for budget monitoring

## Conditional Features

### Sleep Hypnogram Annotation

Engine handles missing sleep phase data gracefully:
- `has_sleep_phases` parameter controls hypnogram annotation request
- If `False`, prompt omits hypnogram annotation instructions
- `AIInsight.hypnogram_annotation` is `Optional`
- Frontend can check for `None` and show fallback UI

## Schema Compliance

Generated insights match the `AIInsight` schema from `src/byesamosa/ai/schemas.py`:
- ✓ `date: date`
- ✓ `score_insights: dict[str, ScoreInsight]` (sleep/readiness/activity)
- ✓ `reasoning_chain: list[ReasoningStep]` (3 steps)
- ✓ `actions: list[ActionItem]` (3-4 items)
- ✓ `hypnogram_annotation: Optional[ChartAnnotation]`
- ✓ `vital_annotations: dict[str, ChartAnnotation]` (hrv/rhr/temp/breath)
- ✓ `trend_annotations: dict[str, TrendAnnotation]` (sleep_score/hrv_rhr)
- ✓ `good_looks_like: dict[str, str]` (sleep/readiness/activity)

## Next Steps

1. **Add API key to `.env`:**
   ```bash
   cp .env.example .env
   # Edit .env and add your ANTHROPIC_API_KEY
   ```

2. **Test with real Claude API:**
   ```bash
   uv run python scripts/test_ai_engine.py
   ```

3. **Proceed to Phase 3 (API Server):**
   - Implement FastAPI routes
   - Add rate limiting for `/api/insights/regenerate`
   - Integrate `generate_insight()` and `load_cached_insight()`

## Dependencies Completed

- ✓ Step 1.3: Data models (AIInsight, ScoreInsight, etc.)
- ✓ Step 1.7: Baseline queries (get_latest_day, get_trends, etc.)
- ✓ Step 2.1: AI output schemas (schemas.py)
- ✓ Step 2.2: Prompt templates (prompts.py)
- ✓ Step 2.3: Claude API integration (engine.py)

**Phase 2 is now complete.** ✅

## Known Limitations

1. **No streaming:** Uses synchronous API calls (blocking)
   - Could be improved with async/streaming in future
   - Current approach is fine for MVP (personal tool)

2. **No prompt caching:** Sends full prompt on each call
   - Could use Claude's prompt caching for cost savings
   - Deferred to post-MVP optimization

3. **Single retry:** Only retries validation errors once
   - Could implement exponential backoff
   - Current approach sufficient for MVP

4. **Fixed model:** Hard-coded to `claude-sonnet-4-5-20250929`
   - Could make configurable in Settings
   - Not a priority for MVP

## File Locations

```
src/byesamosa/ai/
├── __init__.py
├── schemas.py           # Step 2.1 (already existed)
├── prompts.py          # Step 2.2 (NEW)
└── engine.py           # Step 2.3 (NEW)

scripts/
├── verify_ai_engine.py  # Verification without API calls (NEW)
└── test_ai_engine.py    # Full test with Claude API (NEW)

docs/
└── STEP_2.3_IMPLEMENTATION.md  # This file (NEW)
```

## Verification Checklist

- [x] Prompts module creates valid prompts with data context
- [x] Prompt size is reasonable (~863 tokens < 10K limit)
- [x] Engine module imports and initializes correctly
- [x] Fallback insight has valid AIInsight structure
- [x] Caching saves and loads insights correctly
- [x] Cost logging appends to JSON file
- [x] All verification tests pass
- [x] Code follows project structure and naming conventions
- [x] Error handling covers API failures and validation errors
- [x] Cost protection (max_tokens=4096) is enforced
- [x] Conditional hypnogram handling works correctly
- [x] Ready for Phase 3 (API server integration)

---

**Implementation complete. Ready for API server integration (Phase 3).**
