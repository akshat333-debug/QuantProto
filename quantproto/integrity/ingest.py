"""Bring-your-own-backtest ingestion.

Practitioners already have backtests — in Backtrader, QuantConnect, Excel, a
notebook. The auditor meets them where they are: paste a return series, an
equity curve, a list of trade P&Ls, or a matrix of strategy variants, and it
normalises everything to per-period returns ready for the integrity engine.

All parsers raise ``ValueError`` with an actionable message on bad input.
"""

from __future__ import annotations

import csv
import io

import numpy as np

MAX_POINTS = 100_000


def _coerce_floats(values, label: str) -> np.ndarray:
    out = []
    for i, v in enumerate(values):
        if v is None or v == "":
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            raise ValueError(f"{label}: non-numeric value {v!r} at position {i}")
    arr = np.asarray(out, dtype=float)
    if arr.size == 0:
        raise ValueError(f"{label}: no numeric values found")
    if arr.size > MAX_POINTS:
        raise ValueError(f"{label}: too many points ({arr.size} > {MAX_POINTS})")
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{label}: contains NaN or infinite values")
    return arr


def parse_returns(values) -> np.ndarray:
    """Parse a per-period return series (list of floats)."""
    return _coerce_floats(values, "returns")


def equity_to_returns(equity) -> np.ndarray:
    """Convert an equity / NAV curve to per-period simple returns."""
    eq = _coerce_floats(equity, "equity_curve")
    if eq.size < 2:
        raise ValueError("equity_curve: need at least 2 points")
    if np.any(eq <= 0):
        raise ValueError("equity_curve: values must be positive")
    return np.diff(eq) / eq[:-1]


def trades_to_returns(pnl, capital: float | None = None) -> np.ndarray:
    """Convert a series of trade P&Ls into per-trade returns.

    If ``capital`` is given, returns are P&L / capital; otherwise P&L is
    interpreted as already-fractional per-trade returns.
    """
    arr = _coerce_floats(pnl, "trades")
    if capital is not None:
        if capital <= 0:
            raise ValueError("capital must be positive")
        return arr / capital
    return arr


def parse_csv(text: str, has_header: bool | None = None) -> dict[str, np.ndarray]:
    """Parse CSV text into named numeric columns.

    Returns a mapping ``{column_name: np.ndarray}``. Single-column CSVs are
    keyed ``"col_0"``. Used for variant matrices (PBO) and single series alike.
    """
    if not text or not text.strip():
        raise ValueError("Empty CSV input")
    sample = text[:4096]
    if has_header is None:
        try:
            has_header = csv.Sniffer().has_header(sample)
        except csv.Error:
            has_header = False

    reader = csv.reader(io.StringIO(text))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise ValueError("CSV contains no data rows")

    if has_header:
        header = [h.strip() or f"col_{i}" for i, h in enumerate(rows[0])]
        data_rows = rows[1:]
    else:
        header = [f"col_{i}" for i in range(len(rows[0]))]
        data_rows = rows

    columns: dict[str, list] = {h: [] for h in header}
    for row in data_rows:
        for i, h in enumerate(header):
            if i < len(row):
                columns[h].append(row[i])

    return {h: _coerce_floats(vals, h) for h, vals in columns.items()}


def parse_variant_matrix(data) -> np.ndarray:
    """Parse a (T, N) strategy-variant return matrix for PBO.

    Accepts a list of lists, a 2D array, or CSV text (columns = variants).
    """
    if isinstance(data, str):
        cols = parse_csv(data)
        lengths = {len(v) for v in cols.values()}
        if len(lengths) != 1:
            raise ValueError("All variant columns must have equal length")
        return np.column_stack([cols[k] for k in cols])

    arr = np.asarray(data, dtype=float)
    if arr.ndim != 2:
        raise ValueError(f"variant matrix must be 2D (T, N); got shape {arr.shape}")
    if not np.all(np.isfinite(arr)):
        raise ValueError("variant matrix contains NaN or infinite values")
    return arr
