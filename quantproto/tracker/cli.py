"""``qp`` — command-line view of the experiment ledger.

    qp list                     experiments + run counts
    qp status <experiment>      research-budget meter
    qp runs <experiment>        run history table
    qp report <experiment>      full robustness report (JSON)
    qp sensitivity <experiment> <param>
    qp verify <experiment>      hash-chain check
"""

from __future__ import annotations

import argparse
import json
import sys

from quantproto.tracker.ledger import RunLedger
from quantproto.tracker.experiment import Experiment


def _fmt_params(params: dict, width: int = 40) -> str:
    s = ", ".join(f"{k}={v}" for k, v in params.items()) or "-"
    return s if len(s) <= width else s[: width - 1] + "…"


def cmd_list(ledger: RunLedger, _args) -> int:
    exps = ledger.list_experiments()
    if not exps:
        print("No experiments logged yet.")
        return 0
    for e in exps:
        print(f"{e['name']:<32} runs={e['n_runs']:<5} created={e['created_ts'][:19]}")
    return 0


def cmd_status(ledger: RunLedger, args) -> int:
    exp = Experiment(args.experiment, ledger=ledger)
    s = exp.status()
    if s.get("budget_state") == "empty":
        print(s["message"])
        return 0
    print(f"experiment      : {args.experiment}")
    print(f"runs / configs  : {s['n_runs']} / {s['n_configs']}")
    print(f"best Sharpe(ann): {s['best_sharpe_ann']}  params={_fmt_params(s['best_params'])}")
    print(f"noise benchmark : {s['spurious_sharpe_ann']}  (expected max from search)")
    print(f"haircut Sharpe  : {s['haircut_sharpe_ann']}")
    print(f"PSR / DSR       : {s['psr']} / {s['dsr']}")
    if s.get("pbo"):
        print(f"PBO             : {s['pbo']['pbo']}  (OOS-loss prob {s['pbo']['prob_oos_loss']})")
    print(f"state           : {s['budget_state'].upper()}")
    print(s["message"])
    return 0


def cmd_runs(ledger: RunLedger, args) -> int:
    exp = Experiment(args.experiment, ledger=ledger)
    rows = exp.runs()
    if not rows:
        print("No runs logged.")
        return 0
    print(f"{'seq':<5}{'ts':<21}{'source':<13}{'n_obs':<7}{'sharpe(ann)':<12}params")
    for r in rows:
        ann = r["sharpe"] * (252 ** 0.5)
        print(f"{r['seq']:<5}{r['ts'][:19]:<21}{r['source']:<13}{r['n_obs']:<7}"
              f"{ann:<12.3f}{_fmt_params(r['params'], 60)}")
    return 0


def cmd_report(ledger: RunLedger, args) -> int:
    exp = Experiment(args.experiment, ledger=ledger)
    print(json.dumps(exp.report(turnover=args.turnover), indent=2, default=str))
    return 0


def cmd_sensitivity(ledger: RunLedger, args) -> int:
    exp = Experiment(args.experiment, ledger=ledger)
    s = exp.sensitivity(args.param)
    if "sharpe_ann_by_value" in s:
        for v, sr in zip(s["values"], s["sharpe_ann_by_value"]):
            marker = "  ← peak" if v == s["peak_value"] else ""
            print(f"{args.param}={v:<12} sharpe(ann)={sr}{marker}")
        print(f"verdict: {s['verdict']}")
    print(s["message"])
    return 0


def cmd_verify(ledger: RunLedger, args) -> int:
    ok = Experiment(args.experiment, ledger=ledger).verify()
    print(f"chain {'VALID' if ok else 'BROKEN — ledger has been tampered with'}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="qp", description="QuantProto experiment tracker")
    p.add_argument("--ledger", default=None, help="ledger path (default: "
                   "$QUANTPROTO_LEDGER or ~/.quantproto/experiments.db)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="list experiments")
    for name in ("status", "runs", "verify"):
        sp = sub.add_parser(name)
        sp.add_argument("experiment")
    sp = sub.add_parser("report")
    sp.add_argument("experiment")
    sp.add_argument("--turnover", type=float, default=1.0)
    sp = sub.add_parser("sensitivity")
    sp.add_argument("experiment")
    sp.add_argument("param")

    args = p.parse_args(argv)
    ledger = RunLedger(args.ledger)
    handlers = {
        "list": cmd_list, "status": cmd_status, "runs": cmd_runs,
        "report": cmd_report, "sensitivity": cmd_sensitivity, "verify": cmd_verify,
    }
    try:
        return handlers[args.cmd](ledger, args)
    finally:
        ledger.close()


if __name__ == "__main__":
    sys.exit(main())
