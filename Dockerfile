# ── QuantProto Backend ────────────────────────────────────────────
# Multi-stage: build → slim runtime

# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml ./
COPY quantproto/ ./quantproto/

RUN pip install --no-cache-dir ".[live,ai]"

# ---- Runtime stage ----
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

EXPOSE 9000

# Default: run the dashboard API
CMD ["uvicorn", "quantproto.dashboard.api:app", "--host", "0.0.0.0", "--port", "9000"]
