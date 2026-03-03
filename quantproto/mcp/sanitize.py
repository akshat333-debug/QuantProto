"""Input sanitization for MCP tool parameters.

All validators raise ValueError with descriptive messages on invalid input.
"""

from __future__ import annotations

MAX_DATA_POINTS = 10_000


def validate_prices_input(prices: dict[str, list[float]]) -> None:
    """Validate price/return dict: {ticker: [float]}."""
    if not isinstance(prices, dict):
        raise ValueError(f"Expected dict, got {type(prices).__name__}")
    if len(prices) == 0:
        raise ValueError("Empty price data")
    for ticker, values in prices.items():
        if not isinstance(ticker, str):
            raise ValueError(f"Ticker must be str, got {type(ticker).__name__}")
        if not isinstance(values, list):
            raise ValueError(f"Values for {ticker} must be list, got {type(values).__name__}")
        if len(values) == 0:
            raise ValueError(f"Empty values for ticker {ticker}")
        if len(values) > MAX_DATA_POINTS:
            raise ValueError(
                f"Too many data points for {ticker}: {len(values)} > {MAX_DATA_POINTS}"
            )
        for v in values:
            if not isinstance(v, (int, float)):
                raise ValueError(f"Non-numeric value in {ticker}: {v}")


def validate_returns_input(returns: list[float]) -> None:
    """Validate flat return list."""
    if not isinstance(returns, list):
        raise ValueError(f"Expected list, got {type(returns).__name__}")
    if len(returns) == 0:
        raise ValueError("Empty returns list")
    if len(returns) > MAX_DATA_POINTS:
        raise ValueError(f"Too many data points: {len(returns)} > {MAX_DATA_POINTS}")
    for v in returns:
        if not isinstance(v, (int, float)):
            raise ValueError(f"Non-numeric value in returns: {v}")


def validate_positive_int(value: int, name: str, max_val: int = 10000) -> None:
    """Validate that value is a positive integer within range."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(f"{name} must be int, got {type(value).__name__}")
    if value < 1:
        raise ValueError(f"{name} must be >= 1, got {value}")
    if value > max_val:
        raise ValueError(f"{name} must be <= {max_val}, got {value}")


def validate_confidence(confidence: float) -> None:
    """Validate confidence level is in (0, 1)."""
    if not isinstance(confidence, (int, float)):
        raise ValueError(f"confidence must be numeric, got {type(confidence).__name__}")
    if not (0 < confidence < 1):
        raise ValueError(f"confidence must be in (0, 1), got {confidence}")


def validate_weights(weights: dict[str, float]) -> None:
    """Validate factor weights dict."""
    if not isinstance(weights, dict):
        raise ValueError(f"weights must be dict, got {type(weights).__name__}")
    for k, v in weights.items():
        if not isinstance(v, (int, float)):
            raise ValueError(f"Weight for '{k}' must be numeric, got {type(v).__name__}")
        if v < 0:
            raise ValueError(f"Weight for '{k}' must be >= 0, got {v}")
