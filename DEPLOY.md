# Deployment Guide

Two components to deploy:

| Component | What it is | Where to deploy |
|-----------|-----------|-----------------|
| **API** (`quantproto/dashboard/api.py`) | FastAPI + Python | Railway or Fly.io |
| **Frontend** (`dashboard/`) | Next.js | Vercel |

---

## 1 — Deploy the API (Railway — easiest)

### Railway

1. Create a Railway account at [railway.app](https://railway.app) and install the CLI:
   ```bash
   npm install -g @railway/cli
   railway login
   ```

2. From the repo root:
   ```bash
   railway init          # creates a new project
   railway up            # builds Dockerfile and deploys
   ```

3. Set environment variables in Railway dashboard (or CLI):
   ```bash
   railway variables set GEMINI_API_KEY=your_key_here
   railway variables set API_KEY=your_api_secret        # optional auth
   railway variables set ALLOWED_ORIGINS=https://your-vercel-url.vercel.app
   ```

4. Railway auto-assigns a public URL like `https://quantproto-api-production.up.railway.app`.
   Copy it — you'll need it for step 3.

### Fly.io (alternative)

```bash
brew install flyctl
fly auth login
fly launch --no-deploy    # reads fly.toml at repo root
fly secrets set GEMINI_API_KEY=your_key ALLOWED_ORIGINS=https://your-vercel-url.vercel.app
fly deploy
```

The deployed URL will be `https://quantproto-api.fly.dev` (or your chosen app name).

### Verify the API

```bash
curl https://your-api-url/api/health
# → {"status":"ok"}
```

---

## 2 — Add a free Postgres database (optional but recommended)

### Railway (built-in)

In the Railway project dashboard: **+ New** → **Database** → **Add PostgreSQL**.

Railway auto-injects `DATABASE_URL` into your service — no manual configuration.

Audit runs are then persisted to Postgres (hash-chained, tamper-evident).
Without this, QuantProto falls back to a local SQLite file (works fine for
single-instance deploys).

### Fly.io

```bash
fly postgres create --name quantproto-db
fly postgres attach --app quantproto-api quantproto-db
```

Fly auto-injects `DATABASE_URL`.

---

## 3 — Deploy the frontend (Vercel)

1. Import the GitHub repo at [vercel.com/new](https://vercel.com/new).

2. In the **Configure Project** step:
   - **Framework**: Next.js (auto-detected)
   - **Root directory**: `dashboard`
   - **Build command**: `npm run build` (auto-detected)

3. Add environment variable:
   | Name | Value |
   |------|-------|
   | `API_URL` | `https://your-api-url.railway.app` |

4. Click **Deploy**.  Vercel bakes the `API_URL` into the Next.js rewrite so
   all `/api/*` calls proxy to your Railway/Fly backend.

### Verify

Open the Vercel URL → click **Run Analysis** → watch the Integrity tab populate.

---

## 4 — Connect Redis (optional, for distributed rate limiting)

Railway: **+ New** → **Database** → **Add Redis**.
Railway auto-injects `REDIS_URL`.

Without Redis, rate limiting falls back to an in-memory token bucket (fine for
single-instance deploys).

---

## Environment variable reference

| Variable | Where to set | Default | Purpose |
|----------|-------------|---------|---------|
| `API_URL` | Vercel | `http://localhost:9000` | Backend URL for Next.js rewrite |
| `DATABASE_URL` | Railway/Fly | SQLite at `~/.quantproto/audit.db` | Postgres for audit-run persistence |
| `REDIS_URL` | Railway/Fly | in-memory | Distributed rate limiting |
| `GEMINI_API_KEY` | Railway/Fly | mock fallback | AI executive summaries |
| `ALLOWED_ORIGINS` | Railway/Fly | `http://localhost:3000` | CORS — set to Vercel URL |
| `API_KEY` | Railway/Fly | disabled | Optional API key auth |

---

## Full Docker stack (self-hosted)

For on-prem or VPS deploys with all services included:

```bash
GEMINI_API_KEY=your_key docker compose up -d
```

Services: API (:9000), Dashboard (:3000), TimescaleDB, Redis.
