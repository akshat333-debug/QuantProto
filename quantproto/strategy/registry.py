"""Strategy registry — register, discover, and instantiate strategies by name."""

from __future__ import annotations

from typing import Any, Type

from quantproto.strategy.base import (
    Strategy,
    MomentumStrategy,
    MeanReversionStrategy,
    CompositeStrategy,
)


_REGISTRY: dict[str, Type[Strategy]] = {}


def register(name: str, cls: Type[Strategy]) -> None:
    """Register a strategy class under a name."""
    _REGISTRY[name.lower()] = cls


def get(name: str, **kwargs: Any) -> Strategy:
    """Instantiate a registered strategy by name."""
    key = name.lower()
    if key not in _REGISTRY:
        raise KeyError(f"Strategy '{name}' not registered. Available: {list_strategies()}")
    return _REGISTRY[key](**kwargs)


def list_strategies() -> list[str]:
    """List all registered strategy names."""
    return sorted(_REGISTRY.keys())


# ── Auto-register built-in strategies ─────────────────────────────────
register("momentum", MomentumStrategy)
register("mean_reversion", MeanReversionStrategy)
register("composite", CompositeStrategy)
