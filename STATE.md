# QuantProto — Current State

**Last updated:** 2026-03-31

## Build Health

| Check            | Status | Details                                 |
|------------------|--------|-----------------------------------------|
| Backend tests    | ✅ PASS | 246/246 passed in 6.9s                  |
| `tsc --noEmit`   | ✅ PASS | No type errors                          |
| `next build`     | ✅ PASS | Static pages optimized                  |
| Lint             | ⚠️ TBD | Needs `npx eslint .` re-verification    |

## Git Status

- **Branch:** `main`
- **Last commit:** `31a0209` — layout fixes (pie labels, matrix spacing, gate violations)
- **Uncommitted changes:** 8 modified files + 1 new directory (audit fixes from prior session)

### Uncommitted Files
| File | Change | What |
|------|--------|------|
| `PROJECT.md` | Modified | Updated to reflect full architecture |
| `dashboard/README.md` | Modified | Replaced boilerplate with real docs |
| `dashboard/next.config.ts` | Modified | Added API proxy + security headers |
| `dashboard/src/app/layout.tsx` | Modified | Replaced Google Fonts link with next/font |
| `dashboard/src/app/page.tsx` | Modified | All audit fixes (a11y, types, validation, errors) |
| `dashboard/tsconfig.json` | Modified | Excluded test files |
| `quantproto/dashboard/__init__.py` | Modified | WS origin check, try/catch, zero-value fix |
| `quantproto/dashboard/api.py` | Modified | CORS restrict, API key auth, field validators |
| `dashboard/src/app/__tests__/` | New | Smoke test file |
| `dashboard/.env.local` | New | API_URL config |
| `dashboard/.env.example` | New | Documented env template |

## Architecture Decisions
- API requests proxied through Next.js rewrites (not direct to backend)
- Optional API key auth (enabled via `API_KEY` env var, disabled in dev)
- CORS restricted to configurable `ALLOWED_ORIGINS` (default: localhost:3000)
- Test files excluded from `tsc` compilation (jest types not installed yet)
- Legacy WebSocket dashboard retained but hardened (origin check, JSON safety)

## Active Phase: Phase 1 (Housekeeping & Ship)
