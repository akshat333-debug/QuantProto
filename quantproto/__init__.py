"""QuantProto — backtest-integrity auditor and experiment tracker."""

__version__ = "0.1.0"


def experiment(name: str, ledger_path: str | None = None):
    """Open (or create) a tracked experiment — see :mod:`quantproto.tracker`.

    Lazy import so ``import quantproto`` stays cheap.
    """
    from quantproto.tracker import experiment as _experiment

    return _experiment(name, ledger_path=ledger_path)
