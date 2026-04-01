# QuantProto — Roadmap

## Phase 1: Housekeeping & Ship ✅ DONE
> Commit pending audit fixes, create root README, push to GitHub

- [x] Commit + push all uncommitted audit fixes (8 modified + 1 new)
- [x] Create comprehensive root `README.md`
- [x] Update `.gitignore` for dashboard artifacts (`.next/`, `node_modules/`, `.env.local`)

---

## Phase 2: Dashboard Decomposition ✅ DONE
> Break monolithic page.tsx into testable components

- [x] Extract `MetricCard`, `DecisionBadge`, `ErrorBanner`, `ChartTooltip` → `src/components/ui/`
- [x] Extract tab panels → `src/components/tabs/` (OverviewTab, PerformanceTab, etc.)
- [x] Extract API calls → `src/lib/api.ts`
- [x] Extract types → `src/lib/types.ts`
- [x] `ThemeToggle` → `src/components/ui/ThemeToggle.tsx`
- [ ] Install jest + testing-library, wire up test runner
- [ ] Write unit tests for each extracted component

---

## Phase 3: Real Market Data ✅ DONE
> Replace synthetic data with live market data

- [x] Integrate `yfinance` for real price fetching (with synthetic fallback)
- [x] Data source toggle in dashboard UI (Synthetic / Live Yahoo)
- [x] Local CSV caching (via fetcher.py cache layer)
- [x] Date range picker in dashboard config bar (Start Date / End Date)
- [ ] Ticker autocomplete/validation against known universe (deferred)

---

## Phase 4: GenAI Integration ✅ DONE
> LLM-powered analysis and conversational interface

- [x] Add Gemini 2.0 Flash integration for risk narrative generation
- [x] Add executive summary auto-generation after analysis (AISummary component)
- [x] Add conversational chat panel (floating ChatPanel with suggested questions)
- [x] Fallback to mock responses when no API key configured
- [x] API endpoints: `/api/ai/status`, `/api/ai/summary`, `/api/ai/chat`

---

## Phase 5: CI/CD & Production Readiness ✅ DONE
> Automated testing + deployment pipeline

- [x] GitHub Actions: lint + test + build on push/PR (Python 3.11+3.12, Node 22)
- [x] Production Docker build for dashboard (multi-stage standalone)
- [x] Production Docker build for backend API (multi-stage slim)
- [x] docker-compose.yml: 4 services (api, dashboard, timescaledb, redis)
- [x] .dockerignore files for both contexts
- [ ] Playwright E2E tests (deferred)
- [ ] Database migration layer — Alembic + SQLAlchemy (deferred)

---

## Phase 6: Advanced Features
> Power-user capabilities

- [ ] Export analysis results (PDF report, CSV data download)
- [ ] Custom strategy builder (UI for defining factor weights)
- [ ] Alert system (email/webhook on risk gate violations)
- [ ] Multi-user sessions with saved analysis history
- [ ] Mobile-responsive dashboard layout
