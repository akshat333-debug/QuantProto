"""WebSocket dashboard — live streaming metrics.

FastAPI WebSocket server that streams real-time equity,
drawdown, regime, and alert data.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(title="QuantProto Dashboard", version="0.1.0")


# Connection manager
class ConnectionManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.connections.remove(ws)

    async def broadcast(self, message: dict):
        for ws in self.connections:
            try:
                await ws.send_json(message)
            except Exception:
                pass


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo received + acknowledge
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard HTML."""
    html = DASHBOARD_HTML
    return HTMLResponse(content=html)


@app.get("/api/status")
async def api_status():
    return {"connections": len(manager.connections), "status": "running"}


# ── Inline Dashboard HTML ─────────────────────────────────────────────
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>QuantProto Dashboard</title>
<style>
  :root {
    --bg: #0a0e17;
    --card: #111827;
    --accent: #3b82f6;
    --green: #10b981;
    --red: #ef4444;
    --yellow: #f59e0b;
    --text: #e5e7eb;
    --muted: #6b7280;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    min-height: 100vh;
  }
  .header {
    background: linear-gradient(135deg, #1e3a5f 0%, #0a0e17 100%);
    padding: 1.5rem 2rem;
    border-bottom: 1px solid #1f2937;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  .header h1 {
    font-size: 1.5rem;
    background: linear-gradient(90deg, var(--accent), var(--green));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .status-dot {
    width: 10px; height: 10px; border-radius: 50%;
    display: inline-block; margin-right: 8px;
    animation: pulse 2s infinite;
  }
  .status-dot.live { background: var(--green); }
  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 1.5rem;
    padding: 2rem;
  }
  .card {
    background: var(--card);
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 1.5rem;
    transition: transform 0.2s, box-shadow 0.2s;
  }
  .card:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(59,130,246,0.1);
  }
  .card h3 {
    color: var(--muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.75rem;
  }
  .metric {
    font-size: 2rem;
    font-weight: 700;
  }
  .metric.positive { color: var(--green); }
  .metric.negative { color: var(--red); }
  .metric.neutral { color: var(--yellow); }
  .sub { color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem; }
  #log {
    background: #0d1117;
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 1rem;
    max-height: 200px;
    overflow-y: auto;
    font-family: monospace;
    font-size: 0.8rem;
    color: var(--muted);
  }
  .wide { grid-column: span 2; }
  canvas { width: 100% !important; height: 200px !important; }
</style>
</head>
<body>
  <div class="header">
    <h1>⚡ QuantProto Dashboard</h1>
    <div><span class="status-dot live"></span><span id="conn-status">Connecting...</span></div>
  </div>

  <div class="grid">
    <div class="card">
      <h3>Portfolio Value</h3>
      <div class="metric positive" id="equity">$1,000,000</div>
      <div class="sub" id="equity-change">+0.00%</div>
    </div>
    <div class="card">
      <h3>Sharpe Ratio</h3>
      <div class="metric neutral" id="sharpe">--</div>
      <div class="sub">Annualised</div>
    </div>
    <div class="card">
      <h3>Max Drawdown</h3>
      <div class="metric negative" id="drawdown">--</div>
      <div class="sub">Peak to trough</div>
    </div>
    <div class="card">
      <h3>Regime</h3>
      <div class="metric neutral" id="regime">NEUTRAL</div>
      <div class="sub" id="regime-conf">Confidence: --</div>
    </div>
    <div class="card">
      <h3>VaR (95%)</h3>
      <div class="metric" id="var">--</div>
      <div class="sub">Daily</div>
    </div>
    <div class="card">
      <h3>Active Positions</h3>
      <div class="metric" id="positions">0</div>
      <div class="sub" id="pos-detail">--</div>
    </div>
    <div class="card wide">
      <h3>Event Log</h3>
      <div id="log">Waiting for connection...</div>
    </div>
  </div>

  <script>
    const ws = new WebSocket(`ws://${location.host}/ws`);
    const log = document.getElementById('log');
    const connStatus = document.getElementById('conn-status');

    ws.onopen = () => {
      connStatus.textContent = 'Live';
      addLog('Connected to QuantProto server');
    };
    ws.onclose = () => {
      connStatus.textContent = 'Disconnected';
      addLog('Connection lost');
    };
    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'metrics') updateMetrics(msg.data);
      addLog(JSON.stringify(msg));
    };

    function updateMetrics(d) {
      if (d.equity) document.getElementById('equity').textContent =
        '$' + Number(d.equity).toLocaleString();
      if (d.sharpe) document.getElementById('sharpe').textContent =
        Number(d.sharpe).toFixed(2);
      if (d.drawdown) document.getElementById('drawdown').textContent =
        (Number(d.drawdown) * 100).toFixed(1) + '%';
      if (d.regime) document.getElementById('regime').textContent = d.regime;
      if (d.var) document.getElementById('var').textContent =
        (Number(d.var) * 100).toFixed(2) + '%';
    }

    function addLog(msg) {
      const line = document.createElement('div');
      line.textContent = new Date().toLocaleTimeString() + ' | ' + msg;
      log.prepend(line);
      if (log.children.length > 50) log.lastChild.remove();
    }
  </script>
</body>
</html>"""
