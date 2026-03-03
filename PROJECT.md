# Project Overview

## Goal
Build QuantProto — a reproducible quant research engine with alpha generation, risk evaluation, walk-forward backtesting, regime detection, and MCP-based agent orchestration.

## Tech Stack
Frontend: Minimal dashboard (FastAPI + WebSocket)
Backend: Python 3.11, FastAPI, FastMCP
Database: TimescaleDB (Postgres)
Cache/Event Bus: Redis
Containers: Docker Compose

## Core Features
- Factor-based alpha engine
- Walk-forward backtester with slippage + costs
- Bootstrap Sharpe confidence intervals
- HMM-based regime detection
- MCP tool interface
- Minimal A2A agent trio
- Deterministic demo CLI

## Constraints
- Deterministic runs (seeded)
- No unsafe shell execution
- JWT-based A2A auth
- Strict MCP contract validation
- Structured logging
- Rate limiting + sanitization

## Definition of Done
- pytest passes
- demo/run_demo.py produces manifest + equity curve + backtest.json
- MCP tools return exact schemas
- Orchestrator HTTP pipeline works
- Docker Compose spins up required services
