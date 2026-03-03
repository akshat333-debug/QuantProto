# ---- Build stage ----
FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml ./
COPY quantproto/ ./quantproto/

RUN pip install --no-cache-dir .

# ---- Runtime stage ----
FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

EXPOSE 8000

# Default: run the A2A HTTP server
CMD ["uvicorn", "quantproto.agents.http_server:app", "--host", "0.0.0.0", "--port", "8000"]
