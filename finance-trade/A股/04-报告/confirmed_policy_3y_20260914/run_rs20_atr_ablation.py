#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""② / ⑤ 条件隔离 A/B 实验（2026-10-13）

目的：量化「条件②(ATR回调) 与 条件⑤(相对强度) 的组合」牺牲了多少信号、躲掉了多少亏损。

纪律（依 skill: rule-isolation-ab-experiments.md）：
  ① 先冻结身份（基线 sha256 + 副本在 backups/）
  ② **基线复现门槛**：arm A 必须逐项复现旧摘要 —— 期末权益 15444.34 / 平仓 121 笔 / 费用 1408.09
  ③ 新增约束只收紧：rs_gate=True 是基线的子集（min 语义）
  ④ 所有臂共用同一费用模型（不引入新费率）
  ⑤ 如实报告组间等价，不为了制造差异而暗改基准

臂：
  A  base            ①②③（= 引擎基线，⑤关闭）
  B  base+rs20       ①②③ + ⑤          ← ⑤ 的边际影响 = B − A
  C  no_atr          ①③（②关闭，⑤关闭）  ← ② 的边际影响 = C − A
  D  no_atr+rs20     ①③ + ⑤
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import confirmed_policy_engine as E                                   # noqa: E402
import run_confirmed_policy_3y as R                                   # noqa: E402

INIT_CASH = R.INIT_CASH_MAIN
CODES = list(E.STOCKS.keys())


def main():
    print("loading data ...", flush=True)
    data = E.load_all(CODES)
    cal = data["_calendar"]
    bench = data.get("_bench_ret20") or {}
    print(f"  日历 {len(cal)} 天 | 基准(沪深300)覆盖 {len(bench)} 天", flush=True)
    if not bench:
        print("❌ 缺沪深300基准 → ⑤ 全部不可判，实验无意义", file=sys.stderr)
        return 1

    arms = [
        ("A_base",          "①②③（引擎基线，⑤关闭）",        dict(rs_gate=False)),
        ("B_base_rs20",     "①②③ + ⑤相对强度",               dict(rs_gate=True)),
        ("C_no_atr",        "①③（②关闭）",                    dict(rs_gate=False, atr_k=(0.0, 1e9))),
        ("D_no_atr_rs20",   "①③ + ⑤",                         dict(rs_gate=True,  atr_k=(0.0, 1e9))),
    ]

    rows, details = [], {}
    for label, note, kw in arms:
        sim = E.Simulator(data, CODES, label=label, scenario=note,
                          init_cash=INIT_CASH, delay_min=0, path="OHLC", **kw)
        r = sim.run()
        m = R.metrics(r, cal, E.BACKTEST_START, E.BACKTEST_END)
        m["arm"] = label
        m["note"] = note
        rows.append(m)
        details[label] = {
            "n_trades": len(r.trades),
            "n_orders_placed": getattr(r, "n_orders_placed", None),
            "block_counts": dict(getattr(r, "block_counts", {}) or {}),
        }
        print(f"  [{label}] end={m.get('end_equity')} ret={m.get('total_return_pct')}% "
              f"mdd={m.get('max_drawdown_pct')}% closed={m.get('n_closed_trades')} "
              f"fee={m.get('fee_total')}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(HERE / "rs20_atr_ablation.csv", index=False)

    # ── 基线复现门槛 ────────────────────────────────────────────────
    print("\n=== 基线复现门槛检查（arm A vs 冻结摘要） ===", flush=True)
    frozen = {"end_equity": 15444.34, "n_closed_trades": 121, "fee_total": 1408.09}
    a = rows[0]
    ok = True
    for k, v in frozen.items():
        got = a.get(k)
        same = (got is not None and abs(float(got) - float(v)) < 0.01)
        ok &= same
        print(f"  {k:<18} 期望 {v:<12} 实得 {got:<12} {'✅' if same else '❌'}")
    print(f"  ⇒ 基线复现：{'✅ 通过' if ok else '❌ 未通过（结果不可用）'}", flush=True)

    # ── 关键对照 ──────────────────────────────────────────────────
    def g(lbl, key):
        for r_ in rows:
            if r_["arm"] == lbl:
                return r_.get(key)
        return None

    print("\n=== 关键对照 ===", flush=True)
    print(f"  ⑤ 的边际影响 (B − A)：")
    print(f"     收益 {g('A_base','total_return_pct')}% → {g('B_base_rs20','total_return_pct')}%")
    print(f"     回撤 {g('A_base','max_drawdown_pct')}% → {g('B_base_rs20','max_drawdown_pct')}%")
    print(f"     平仓 {g('A_base','n_closed_trades')} → {g('B_base_rs20','n_closed_trades')} 笔")
    print(f"  ② 的边际影响 (C − A)：")
    print(f"     收益 {g('A_base','total_return_pct')}% → {g('C_no_atr','total_return_pct')}%")
    print(f"     平仓 {g('A_base','n_closed_trades')} → {g('C_no_atr','n_closed_trades')} 笔")

    (HERE / "rs20_atr_ablation_details.json").write_text(
        json.dumps({"arms": details, "frozen_gate_ok": bool(ok)},
                   ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("\nDONE.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
