"""Deterministic demo CLI — runs the full QuantProto pipeline.

Usage:
    python -m quantproto.demo.run_demo [--seed 42] [--output-dir output/]

Produces:
    - backtest.json      (backtest results + bootstrap CI)
    - manifest.json      (file hashes for reproducibility)
    - equity_curve.png   (equity curve plot)
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")  # non-interactive backend
import matplotlib.pyplot as plt

from quantproto.demo.data_loader import load_universe, generate_prices
from quantproto.agents.orchestrator import Orchestrator


def seed_all(seed: int) -> None:
    """Seed all RNGs for full determinism."""
    np.random.seed(seed)
    random.seed(seed)


def hash_file(filepath: str) -> str:
    """SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def run_demo(seed: int = 42, output_dir: str = "output") -> dict:
    """Execute the full deterministic demo pipeline.

    Parameters
    ----------
    seed : RNG seed.
    output_dir : directory for output files.

    Returns
    -------
    Dict with pipeline results and file paths.
    """
    # 1. Seed everything
    seed_all(seed)

    # 2. Load universe + generate data
    universe = load_universe()
    prices = generate_prices(universe, n_days=504, seed=seed)

    # 3. Run orchestrator pipeline
    orchestrator = Orchestrator(
        lookback=20,
        train_window=60,
        test_window=20,
        seed=seed,
    )
    result = orchestrator.run_pipeline(prices)

    # 4. Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # 5. Save backtest.json
    backtest_path = os.path.join(output_dir, "backtest.json")
    backtest_data = {
        "seed": seed,
        "universe": universe,
        "action": result["action"],
        "n_splits": result["backtest"]["n_splits"],
        "bootstrap_ci": result["backtest"]["bootstrap_ci"],
        "risk_report": result["risk_report"],
        "gate": result["gate"],
    }
    with open(backtest_path, "w") as f:
        json.dump(backtest_data, f, indent=2, default=_json_serializer)

    # 6. Plot equity curve
    equity_path = os.path.join(output_dir, "equity_curve.png")
    eq = result["backtest"]["equity_curve"]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(eq, color="#2196F3", linewidth=1.5)
    ax.set_title("Walk-Forward Equity Curve", fontsize=14, fontweight="bold")
    ax.set_xlabel("Trading Days")
    ax.set_ylabel("Portfolio Value")
    ax.grid(True, alpha=0.3)
    ax.axhline(y=1.0, color="gray", linestyle="--", alpha=0.5)
    fig.tight_layout()
    fig.savefig(equity_path, dpi=150)
    plt.close(fig)

    # 7. Generate manifest
    manifest_path = os.path.join(output_dir, "manifest.json")
    manifest = {
        "seed": seed,
        "files": {
            "backtest.json": hash_file(backtest_path),
            "equity_curve.png": hash_file(equity_path),
        },
    }
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)

    # Also add manifest's own hash (meta)
    manifest["files"]["manifest.json"] = "(self)"

    return {
        "backtest_path": backtest_path,
        "equity_path": equity_path,
        "manifest_path": manifest_path,
        "result": backtest_data,
    }


def _json_serializer(obj):
    """Handle numpy/pandas types in JSON serialisation."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return str(obj)
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


def main():
    parser = argparse.ArgumentParser(description="QuantProto Demo")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--output-dir", type=str, default="output", help="Output directory")
    args = parser.parse_args()

    print(f"Running QuantProto demo with seed={args.seed}...")
    result = run_demo(seed=args.seed, output_dir=args.output_dir)
    print(f"Action: {result['result']['action']}")
    print(f"Sharpe CI: {result['result']['bootstrap_ci']}")
    print(f"Files saved to: {args.output_dir}/")
    print(f"  - backtest.json")
    print(f"  - equity_curve.png")
    print(f"  - manifest.json")


if __name__ == "__main__":
    main()
