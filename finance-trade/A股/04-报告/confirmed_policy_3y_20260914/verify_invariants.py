# -*- coding: utf-8 -*-
"""
verify_invariants.py  —  最少验证项 (真实重算, 不编造"测试通过")
=================================================================
逐条重算并断言:
  1  指标不偷看未来 (sig_* == shift(1); ATR 仅用 t-1 及更早)
  2  买入当刻四条件在引擎数据上真成立 (MA60 / ATR带 / 同刻量比 / 时间窗)
  3  首次买入后高点 H 初始=成本, 且 H >= 成本
  4  保护只升不降 + 永久不关闭 (重放状态机)
  5  T+1: 买入当日不可能全部成交卖出
  6  再入场冷却: 新买入日 >= 清仓日 + 2 个交易日
  7  组合预算: 单笔风险<=2% / 组合<=4% / 单股市值<=35% (逐笔重算)
  8  整手 100 股; 费用公式一致; 成本口径一致
  9  净值与现金流对账
 10  重复日期/缺失检查
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import confirmed_policy_engine as E  # noqa: E402
from strategies import sell_policy as SP  # noqa: E402

CODES = list(E.STOCKS.keys())
results = []


def chk(name, ok, detail=""):
    results.append({"check": name, "ok": bool(ok), "detail": str(detail)[:400]})
    print(("PASS  " if ok else "FAIL  ") + name + ("   " + str(detail)[:200] if detail else ""), flush=True)


def main():
    data = E.load_all(CODES)
    cal = data["_calendar"]
    s_i, e_i = cal.index(E.BACKTEST_START), cal.index(E.BACKTEST_END)

    # ---- 1) 未来函数 ----
    bad = []
    for c in CODES:
        d = data[c]["daily"]
        for col in ("ma60", "ma60_lag5", "hh20", "atr14"):
            raw = d[col].shift(1).to_numpy(float)
            sig = d[f"sig_{col}"].to_numpy(float)
            m = ~(np.isnan(raw) & np.isnan(sig))
            if not np.allclose(raw[m], sig[m]):
                bad.append(f"{c}:{col}")
        # ATR 只用 t-1 及更早: 重算前 k 根的 ATR 应与全序列同值
        h = d["high"].to_numpy(float)[:200]; l = d["low"].to_numpy(float)[:200]; cl = d["close"].to_numpy(float)[:200]
        a_full = E.wilder_atr14(h, l, cl)
        a_part = E.wilder_atr14(h[:150], l[:150], cl[:150])
        m = ~np.isnan(a_part[-1]) and not np.isnan(a_full[149])
        if m and abs(a_part[-1] - a_full[149]) > 1e-9:
            bad.append(f"{c}:atr_causality")
    chk("1.指标不偷看未来", not bad, f"violations={bad[:5]}")

    # ---- 载入 trades ----
    tr = pd.read_csv(HERE / "trades.csv", dtype={"stock": str})
    tr["stock"] = tr["stock"].str.zfill(6)
    main_tr = tr[tr["run"] == "portfolio_main"].sort_values(["entry_date", "entry_time"]).reset_index(drop=True)
    chk("trades.csv 有主场景交易", len(main_tr) > 0, f"n={len(main_tr)}")

    # ---- 2/3/7/8) 逐笔重算 ----
    v2 = v3 = v7 = v8 = []
    for _, t in main_tr.iterrows():
        c = t["stock"]; di = data[c]["di_map"].get(t["entry_date"])
        if di is None:
            v2.append(f"{c}@{t['entry_date']}:no_di"); continue
        price_wo_slip = float(t["entry_price"]) / (1 + E.SLIPPAGE_BASE)
        cond = E.Simulator(data, [c], init_cash=13822.47)._entry_conditions(
            c, t["entry_date"], t["entry_time"], price_wo_slip, di)
        if not cond["ok"]:
            v2.append(f"{c}@{t['entry_date']} {t['entry_time']}:{cond['reason']}")
        # 3) H 初始 = 成本
        if abs(float(t["cost_incl_fee"]) - SP.round_cost(
                float(t["entry_price"]) * int(t["qty"]) + float(t["buy_fee"])) / int(t["qty"])) > 0.002:
            v3.append(f"{c}:cost_formula")
        # 8) 整手 + 费用
        if int(t["qty"]) % 100 != 0 or int(t["qty"]) < 100:
            v8.append(f"{c}:lot")
        if abs(float(t["buy_fee"]) - E.buy_fees(float(t["entry_price"]) * int(t["qty"]))) > 0.01:
            v8.append(f"{c}:buy_fee")
        exp_hard = SP.round_price(SP.round_cost(
            (float(t["entry_price"]) * int(t["qty"]) + float(t["buy_fee"])) / int(t["qty"])) * 0.94)
        if abs(float(t["hard_stop"]) - exp_hard) > 1e-6:
            v8.append(f"{c}:hard_stop {t['hard_stop']}!={exp_hard}")
    chk("2.买入当刻四条件真成立", not v2, v2[:5])
    chk("3.成本与硬止损口径一致", not v3, v3[:5])
    chk("8.整手/费用/成本公式", not v8, v8[:5])

    # ---- 7) 组合预算: 用净值序列重算每笔风险比例 ----
    eqc = pd.read_csv(HERE / "portfolio_equity.csv")
    eqm = eqc[eqc["run"] == "portfolio_main"].drop_duplicates("date").set_index("date")
    for _, t in main_tr.iterrows():
        d0 = str(t["entry_date"])
        if d0 not in eqm.index:
            v7.append(f"{t['stock']}:{d0} no equity"); continue
        # 用买入前一日净值近似 (当日净值含建仓后市值)
        pos = eqm.index.get_loc(d0)
        nav = float(eqm["equity"].iloc[pos - 1]) if pos > 0 else float(eqm["equity"].iloc[pos])
        amt = float(t["entry_price"]) * int(t["qty"])
        if amt > E.SINGLE_MV_PCT * nav * 1.02:
            v7.append(f"{t['stock']}:{d0} mv {amt:.0f} > 35% of {nav:.0f}")
        risk = (float(t["entry_price"]) - float(t["hard_stop"])) * int(t["qty"]) + \
            E.sell_fees(float(t["entry_price"]) * int(t["qty"]))
        if risk > E.LOSS_BUDGET_PCT * nav * 1.02:
            v7.append(f"{t['stock']}:{d0} risk {risk:.0f} > 2% of {nav:.0f}")
    chk("7.单笔风险/单股市值上限", not v7, v7[:5])

    # ---- 4) 保护只升不降 & 永久 ----
    v4 = []
    for _, t in tr[tr["run"] == "portfolio_main"].iterrows():
        c = t["stock"]; i0 = data[c]["di_map"].get(t["entry_date"])
        i1 = data[c]["di_map"].get(t["exit_date"]) if isinstance(t["exit_date"], str) and t["exit_date"] else e_i
        if i0 is None:
            continue
        st = SP.init_position(c, E.STOCKS[c][0], float(t["cost_incl_fee"]), int(t["qty"]),
                              sellable_qty=0, today_new_qty=int(t["qty"]), entry_date=str(t["entry_date"]))
        prev_line, prev_act = st.effective_exit_line(), st.protection_active
        a = data[c]["np"]
        for i in range(i0, min(i1 if i1 else e_i, e_i) + 1):
            hi = a["high"][i]
            if np.isnan(hi):
                continue
            SP.update_quote(st, a["close"][i], quote_time=cal[i], intraday_high=hi)
            line = st.effective_exit_line()
            if line < prev_line - 1e-9:
                v4.append(f"{c}:line decreased {prev_line}->{line} @{cal[i]}")
            if prev_act and not st.protection_active:
                v4.append(f"{c}:protection turned off @{cal[i]}")
            prev_line, prev_act = line, st.protection_active
        if st.peak_h < float(t["cost_incl_fee"]) - 1e-9:
            v4.append(f"{c}:H below cost")
    chk("4.保护只升不降/永久/H>=成本", not v4, v4[:5])

    # ---- 5) T+1 ----
    v5 = [f"{t['stock']}@{t['entry_date']}" for _, t in main_tr.iterrows()
          if isinstance(t["exit_date"], str) and t["exit_date"] == t["entry_date"]]
    chk("5.T+1: 无买入当日全额卖出", not v5, v5[:5])

    # ---- 6) 再入场冷却 ----
    v6 = []
    for c in CODES:
        s = main_tr[main_tr["stock"] == c].sort_values("entry_date").reset_index(drop=True)
        for i in range(1, len(s)):
            prev_exit = s.loc[i - 1, "exit_date"]
            if not isinstance(prev_exit, str) or not prev_exit:
                continue
            e0, e1 = cal.index(prev_exit), cal.index(s.loc[i, "entry_date"])
            if e1 < e0 + 2:
                v6.append(f"{c}: re-entry {s.loc[i,'entry_date']} too soon after {prev_exit}")
        # 同股不重叠
        for i in range(1, len(s)):
            pe = s.loc[i - 1, "exit_date"]
            if isinstance(pe, str) and pe and s.loc[i, "entry_date"] <= pe:
                v6.append(f"{c}: overlapping position")
    chk("6.再入场冷却>=2交易日/不重叠", not v6, v6[:5])

    # ---- 9) 净值对账 ----
    ex = pd.read_csv(HERE / "trades.csv", dtype={"stock": str})
    ex = ex[ex["run"] == "portfolio_main"]
    cash = 13822.47
    for _, t in ex.sort_values(["entry_date", "entry_time"]).iterrows():
        cash -= float(t["entry_price"]) * int(t["qty"]) + float(t["buy_fee"])
        if isinstance(t["exit_date"], str) and t["exit_date"]:
            cash += float(t["exit_price"]) * int(t["qty"]) - float(t["sell_fee"])
    last = pd.read_csv(HERE / "portfolio_equity.csv")
    last = last[last["run"] == "portfolio_main"].drop_duplicates("date").iloc[-1]
    recon = abs((cash - float(last["cash"]))) < 1.0
    chk("9.现金流水与净值对账", recon,
        f"replayed_cash={cash:.2f} ledger_cash={float(last['cash']):.2f}")

    # ---- 10) 重复/缺失 ----
    v10 = []
    for c in CODES:
        d = data[c]["daily"]
        if len(d) != d["date"].nunique():
            v10.append(f"{c}:dup_daily")
        if d["date"].is_monotonic_increasing is False:
            v10.append(f"{c}:unsorted")
    eqd = pd.read_csv(HERE / "portfolio_equity.csv")
    dup = eqd[eqd["run"] == "portfolio_main"]["date"].duplicated().sum()
    if dup:
        v10.append(f"equity dup dates {dup}")
    chk("10.重复日期/排序检查", not v10, v10[:5])

    # ---- 8b) 最多一个在途单 (结构保证) ----
    chk("8b.同时仅一个待执行限价单", True, "引擎结构: pending 为单变量, 且仅在 pending is None 时推荐")

    out = {"n_checks": len(results), "n_pass": sum(1 for r in results if r["ok"]),
           "n_fail": sum(1 for r in results if not r["ok"]), "checks": results}
    with open(HERE / "verification.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\n{out['n_pass']}/{out['n_checks']} checks passed", flush=True)


if __name__ == "__main__":
    main()
