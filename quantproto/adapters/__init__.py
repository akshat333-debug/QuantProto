"""Framework adapters — meet practitioners inside their existing tools.

Each adapter extracts a return series (and optionally turnover) from a
framework-specific result object and passes it straight to
``robustness_report``.  None of the adapters import the target framework at
module level — they guard the import so the package works without Backtrader,
QuantConnect, bt, or zipline installed.

Quick-start
-----------
>>> from quantproto.adapters import audit_backtrader, audit_quantconnect
>>> from quantproto.adapters import audit_bt, audit_zipline, audit_returns
"""

from quantproto.adapters.backtrader import audit_backtrader
from quantproto.adapters.quantconnect import audit_quantconnect
from quantproto.adapters.bt import audit_bt
from quantproto.adapters.zipline import audit_zipline
from quantproto.adapters.base import audit_returns

__all__ = [
    "audit_backtrader",
    "audit_quantconnect",
    "audit_bt",
    "audit_zipline",
    "audit_returns",
]
