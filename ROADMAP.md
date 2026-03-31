# QuantProto — Roadmap

## Phase 1: Housekeeping & Ship ⬅️ CURRENT
> Commit pending audit fixes, create root README, push to GitHub

- [ ] Commit + push all uncommitted audit fixes (8 modified + 1 new)
- [ ] Create comprehensive root `README.md`
- [ ] Update `.gitignore` for dashboard artifacts (`.next/`, `node_modules/`, `.env.local`)

---

## Phase 2: Dashboard Decomposition
> Break monolithic page.tsx into testable components

- [ ] Extract `MetricCard`, `DecisionBadge`, `ErrorBanner`, `ChartTooltip` → `src/components/`
- [ ] Extract tab panels → `src/components/tabs/` (OverviewTab, PerformanceTab, etc.)
- [ ] Extract API calls → `src/lib/api.ts`
- [ ] Extract types → `src/lib/types.ts`
- [ ] Install jest + testing-library, wire up test runner
- [ ] Write unit tests for each extracted component

---

## Phase 3: Real Market Data
> Replace synthetic data with live market data

- [ ] Integrate `yfinance` or Alpha Vantage for real price fetching
- [ ] Add ticker autocomplete/validation against known universe
- [ ] Cache fetched data (Redis or local file cache)
- [ ] Add date range picker to dashboard config bar

---

## Phase 4: GenAI Integration
> LLM-powered analysis and conversational interface

- [ ] Add Gemini/OpenAI integration for risk narrative generation
- [ ] Add executive summary auto-generation after analysis
- [ ] Add conversational chat panel (ask questions about results)
- [ ] Fallback to mock responses when no API key configured

---

## Phase 5: CI/CD & Production Readiness
> Automated testing + deployment pipeline

- [ ] GitHub Actions: lint + test + build on PR
- [ ] Add Playwright E2E tests for critical dashboard flows
- [ ] Add database migration layer (Alembic + SQLAlchemy)
- [ ] Production Docker build for dashboard
- [ ] Staging/preview deploy (Vercel or Railway)

---

## Phase 6: Advanced Features
> Power-user capabilities

- [ ] Export analysis results (PDF report, CSV data download)
- [ ] Custom strategy builder (UI for defining factor weights)
- [ ] Alert system (email/webhook on risk gate violations)
- [ ] Multi-user sessions with saved analysis history
- [ ] Mobile-responsive dashboard layout
