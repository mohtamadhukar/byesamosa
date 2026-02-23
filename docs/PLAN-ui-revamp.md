# ByeSamosa UI Revamp: Streamlit → Next.js + FastAPI

## Context

The current Streamlit dashboard works but is limited by Streamlit's widget-based layout — everything looks like a data tool, not a product. Moving to Next.js + Tailwind gives full control over aesthetics, animations, and layout. A thin FastAPI layer exposes the existing Python data layer as REST endpoints, keeping the proven data architecture intact.

**Aesthetic**: Warm editorial — cream backgrounds, serif headings (Playfair Display), clean sans body (DM Sans), warm amber/terracotta accents, generous whitespace, card-based layout with subtle shadows and Framer Motion reveal animations.

---

## Phase 1: FastAPI Backend

Create `src/byesamosa/api/` — a thin HTTP wrapper over existing data layer functions.

### Files to create:
- `src/byesamosa/api/__init__.py`
- `src/byesamosa/api/deps.py` — DataStore + Settings dependency injection
- `src/byesamosa/api/main.py` — FastAPI app, CORS, router includes
- `src/byesamosa/api/routers/__init__.py`
- `src/byesamosa/api/routers/dashboard.py` — `GET /api/dashboard`
- `src/byesamosa/api/routers/trends.py` — `GET /api/trends?days=30`
- `src/byesamosa/api/routers/baselines.py` — `GET /api/baselines?metric=sleep_score`
- `src/byesamosa/api/routers/workouts.py` — `GET /api/workouts?days=30`
- `src/byesamosa/api/routers/insights.py` — `POST /api/insights/refresh`

### Endpoint → Data Layer Mapping:
| Endpoint | Calls | Returns |
|----------|-------|---------|
| `GET /api/dashboard` | `get_latest_day()` + `get_deltas()` + `load_cached_insight()` | Scores, deltas, insight (above-the-fold data) |
| `GET /api/trends` | `get_trends(store, metric, days)` for 3 metrics | Sleep score, HRV, RHR time series |
| `GET /api/baselines` | Read `baselines.json`, filter by metric | Baseline band data for trend overlays |
| `GET /api/workouts` | `get_workout_recovery_data(store, days)` | Workout bars + readiness line data |
| `POST /api/insights/refresh` | `generate_insight()` + `cache_insight()` | New AI insight (rate-limited 60s) |

### Dependencies to add:
- `fastapi` + `uvicorn` in `pyproject.toml`

### Verify:
```bash
uvicorn byesamosa.api.main:app --reload
curl http://localhost:8000/api/dashboard | python -m json.tool
```

---

## Phase 2: Next.js Scaffold

Create `frontend/` directory with Next.js App Router + Tailwind.

- [ ] `npx create-next-app@latest frontend --typescript --tailwind --app`
- [ ] Configure `tailwind.config.ts` — warm editorial color palette (cream `#FDFBF7`, amber `#D97706`, terracotta `#C2410C`, sage `#65A30D`)
- [ ] Configure `next.config.js` — rewrite proxy: `/api/*` → `http://localhost:8000/api/*` (avoids CORS)
- [ ] Set up fonts via `next/font/google`: Playfair Display (serif headings) + DM Sans (body)
- [ ] `globals.css` — cream background, serif headings base styles
- [ ] `lib/types.ts` — TypeScript interfaces matching Python models + API responses
- [ ] `lib/api.ts` — fetch wrappers for all 5 endpoints
- [ ] `lib/utils.ts` — score color helper, date formatter
- [ ] `lib/constants.ts` — chart color palette

### NPM dependencies:
- `recharts` (charts — lightweight React-native alternative to Plotly)
- `framer-motion` (animations)

---

## Phase 3: Core Components

Build top-to-bottom matching dashboard scroll order:

- [ ] `components/AnimatedCard.tsx` — Framer Motion wrapper (fade-in + slide-up)
- [ ] `components/SectionDivider.tsx` — warm styled divider
- [ ] `components/Header.tsx` — "ByeSamosa" serif title + "Data as of Feb 23" caption
- [ ] `components/RefreshButton.tsx` — POST trigger, loading spinner, rate-limit countdown
- [ ] `components/RadarChart.tsx` — Recharts RadarChart for score contributors
- [ ] `components/ScoreCard.tsx` — score number + delta badge + radar + AI one-liner + benchmark
- [ ] `components/ScoreCardsRow.tsx` — 3-column responsive grid
- [ ] `components/ReasoningChain.tsx` — Observation/Cause/So what with icons
- [ ] `components/ActionItems.tsx` — priority-colored action cards
- [ ] `components/AIBriefing.tsx` — 2-column layout wrapper
- [ ] `components/VitalCard.tsx` — single metric card
- [ ] `components/Vitals.tsx` — 4-column grid

---

## Phase 4: Chart Components

- [ ] `components/WorkoutRecovery.tsx` — Recharts ComposedChart (stacked bars + readiness line, dual Y-axis)
- [ ] `components/SleepScoreTrend.tsx` — Line chart + baseline Area band (avg±σ)
- [ ] `components/HrvRhrTrend.tsx` — Dual-axis line chart (HRV green, RHR red)
- [ ] `components/TrendCharts.tsx` — Container with AI trend annotations

---

## Phase 5: Page Assembly + Polish

- [ ] Wire `app/page.tsx` — client component, parallel fetch all endpoints on mount, render all sections
- [ ] `app/loading.tsx` — skeleton loading state (pulsing card placeholders)
- [ ] Framer Motion stagger animations on card reveals
- [ ] Responsive: single column on mobile, multi-column on desktop
- [ ] Empty state / error handling for missing data

---

## Phase 6: Pipeline Integration

Update `cmd_serve` in `src/byesamosa/pipeline.py` to start both:
1. FastAPI backend (`uvicorn byesamosa.api.main:app`)
2. Next.js dev server (`npm run dev` in `frontend/`)
3. Graceful shutdown of both on Ctrl+C

---

## Key Design Decisions

| Decision | Choice | Why |
|----------|--------|-----|
| **Recharts over Plotly** | Recharts | 150KB vs 800KB, tree-shakeable, React-native. All current charts have direct equivalents. |
| **Client-side fetching** | `'use client'` + `useEffect` | Personal tool, no SEO need. Loading skeleton for instant feedback. |
| **API proxy via next.config.js** | `rewrites` to `localhost:8000` | Zero CORS complexity. Frontend/backend appear same-origin. |
| **Single dashboard endpoint** | Bundle scores+deltas+insight | Minimize round-trips for above-fold content. Trends/workouts fetch separately (below fold). |
| **Existing data layer untouched** | FastAPI is pure wrapper | Zero refactoring risk. Proven code stays proven. |

## Critical Files (existing, to reference/modify):
- `src/byesamosa/data/queries.py` — all query functions FastAPI calls
- `src/byesamosa/ai/schemas.py` — AIInsight model → TypeScript interface contract
- `src/byesamosa/ai/engine.py` — generate/cache insight functions
- `streamlit_app.py` — reference for exact data flow and chart behavior
- `src/byesamosa/pipeline.py` — update `cmd_serve` for dual-server
- `pyproject.toml` — add fastapi + uvicorn deps
