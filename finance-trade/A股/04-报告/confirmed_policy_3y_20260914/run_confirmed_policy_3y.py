# -*- coding: utf-8 -*-
"""
run_confirmed_policy_3y.py  —  已确认买卖策略三年验证主运行器
============================================================
真实执行, 无未来函数, 隔离研究。输出全部落在本目录。
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

OUT = HERE
INIT_CASH_MAIN = 13822.47      # 研究假设: 最新已知成本+现金 (非核实实时净资产)
INIT_CASH_ALT = 100000.0
CODES = list(E.STOCKS.keys())


# ---------------------------------------------------------------------------
def metrics(res: E.RunResult, cal, start, end) -> dict:
    eq = pd.DataFrame(res.daily_equity)
    init = res.init_cash
    out = {"label": res.label, "scenario": res.scenario, "init_cash": init}
    if eq.empty:
        out.update({"status": "no_equity"}); return out
    eq = eq.drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)
    end_eq = float(eq["equity"].iloc[-1])
    out["end_equity"] = round(end_eq, 2)
    out["total_return_pct"] = round((end_eq / init - 1) * 100, 4)
    days = (pd.Timestamp(end) - pd.Timestamp(start)).days
    if days > 0 and end_eq > 0:
        out["annualized_pct"] = round(((end_eq / init) ** (365.0 / days) - 1) * 100, 4)
    else:
        out["annualized_pct"] = None
    peak = eq["equity"].cummax()
    dd = (eq["equity"] - peak) / peak
    out["max_drawdown_pct"] = round(float(dd.min()) * 100, 4)
    out["avg_exposure_pct"] = round(float(eq["exposure_pct"].mean()), 3)
    out["max_exposure_pct"] = round(float(eq["exposure_pct"].max()), 3)
    out["days_flat_pct"] = round(float((eq["n_pos"] == 0).mean()) * 100, 3)

    closed = [t for t in res.trades if t.exit_date]
    out["n_closed_trades"] = len(closed)
    out["n_open_positions"] = len(res.open_positions)
    wins = [t for t in closed if t.pnl_net > 0]
    losses = [t for t in closed if t.pnl_net < 0]
    out["n_wins"] = len(wins); out["n_losses"] = len(losses)
    out["win_rate_pct"] = round(len(wins) / len(closed) * 100, 3) if closed else None
    out["avg_pnl_per_trade"] = round(float(np.mean([t.pnl_net for t in closed])), 2) if closed else None
    out["avg_win"] = round(float(np.mean([t.pnl_net for t in wins])), 2) if wins else None
    out["avg_loss"] = round(float(np.mean([t.pnl_net for t in losses])), 2) if losses else None
    gp = sum(t.pnl_net for t in wins); gl = -sum(t.pnl_net for t in losses)
    out["gross_profit"] = round(gp, 2); out["gross_loss"] = round(gl, 2)
    out["profit_factor"] = round(gp / gl, 4) if gl > 0 else None
    out["realized_pnl"] = round(sum(t.pnl_net for t in closed), 2)
    out["unrealized_pnl_open"] = round(sum(p["unrealized_pnl"] for p in res.open_positions), 2)
    out["fee_total"] = round(res.fee_total, 2)
    out["slippage_cost_total"] = round(res.slip_total, 2)
    out["fee_pct_of_init"] = round(res.fee_total / init * 100, 4)
    # 连亏
    mx = cur = 0
    for t in closed:
        if t.pnl_net < 0: cur += 1; mx = max(mx, cur)
        else: cur = 0
    out["max_consecutive_losses"] = mx
    # 收益集中度
    tot = sum(t.pnl_net for t in closed)
    if closed and tot > 0:
        best = max(t.pnl_net for t in closed)
        out["top_trade_share_of_gross_pnl_pct"] = round(best / tot * 100, 3)
    else:
        out["top_trade_share_of_gross_pnl_pct"] = None
    # 逐年
    eq["y"] = eq["date"].str[:4]
    yr = {}
    prev = init
    for y, g in eq.groupby("y"):
        ev = float(g["equity"].iloc[-1])
        yr[y] = round((ev / prev - 1) * 100, 4)
        prev = ev
    out["yearly_return_pct"] = yr
    out["blocked"] = dict(sorted(res.blocked.items(), key=lambda kv: -kv[1]))
    out["open_positions"] = res.open_positions
    out["end_cash"] = res.extra.get("end_cash")
    return out


# ---------------------------------------------------------------------------
def buy_and_hold(data, code, cash, cal, start_i, end_i, slip=E.SLIPPAGE_BASE):
    d = data[code]["np"]; dates = data["_calendar"]
    p0 = d["close"][start_i]; p1 = d["close"][end_i]
    res = {"stock": code, "name": E.STOCKS[code][0], "start_price": round(p0, 4),
           "end_price": round(p1, 4), "return_pct": round((p1 / p0 - 1) * 100, 4)}
    if not np.isnan(p0) and p0 > 0:
        qty = int(cash // (p0 * (1 + slip) * 100)) * 100
        if qty >= 100:
            amt = p0 * (1 + slip) * qty; fee = E.buy_fees(amt)
            if amt + fee > cash:
                qty -= 100
                amt = p0 * (1 + slip) * qty; fee = E.buy_fees(amt)
            amt1 = p1 * (1 - slip) * qty; fee1 = E.sell_fees(amt1)
            res.update({"qty": qty, "cash_left": round(cash - amt - fee, 2),
                        "net_pnl": round(amt1 - fee1 - amt - fee, 2),
                        "net_return_pct": round((amt1 - fee1 - amt - fee) / cash * 100, 4)})
        else:
            res.update({"qty": 0, "net_return_pct": 0.0, "note": "现金不足一手"})
    return res


# ---------------------------------------------------------------------------
def main():
    print("loading data ...", flush=True)
    data = E.load_all(CODES)
    cal = data["_calendar"]
    s_i, e_i = cal.index(E.BACKTEST_START), cal.index(E.BACKTEST_END)
    print(f"calendar: {len(cal)} days; backtest {cal[s_i]} .. {cal[e_i]} ({e_i-s_i+1} days)", flush=True)

    runs = {}

    def fresh():
        for c in CODES:
            data[c]["last_close"] = 0.0

    def go(label, scenario, **kw):
        fresh()
        codes = kw.pop("codes", CODES)
        sim = E.Simulator(data, codes, label=label, scenario=scenario, **kw)
        r = sim.run()
        runs[label] = r
        print(f"  [{label}] trades={len(r.trades)} closed={len([t for t in r.trades if t.exit_date])} "
              f"open={len(r.open_positions)} end_eq={r.daily_equity[-1]['equity'] if r.daily_equity else None}",
              flush=True)
        return r

    print("== 主场景: 真实组合 (13,822.47 现金池, 即刻执行) ==", flush=True)
    go("portfolio_main", "同一现金池真实组合 / 主资金 13,822.47 / 即刻执行",
       init_cash=INIT_CASH_MAIN, delay_bars=0)

    print("== 执行延迟敏感性 (5 / 15 分钟) ==", flush=True)
    go("portfolio_delay5", "主资金 / 下单后 5 分钟执行", init_cash=INIT_CASH_MAIN, delay_bars=1)
    go("portfolio_delay15", "主资金 / 下单后 15 分钟执行", init_cash=INIT_CASH_MAIN, delay_bars=3)

    print("== 资金敏感性 100,000 ==", flush=True)
    go("portfolio_100k", "100,000 现金池 / 即刻执行", init_cash=INIT_CASH_ALT, delay_bars=0)

    print("== 滑点敏感性 (0% / 0.2%) ==", flush=True)
    go("portfolio_slip0", "主资金 / 滑点 0%", init_cash=INIT_CASH_MAIN, slippage=0.0)
    go("portfolio_slip2", "主资金 / 滑点 0.2%", init_cash=INIT_CASH_MAIN, slippage=0.002)

    print("== 盘中最高/最低先后顺序敏感性 ==", flush=True)
    go("portfolio_intra_OLHC", "主资金 / 严格 O-L-H-C 盘中顺序", init_cash=INIT_CASH_MAIN,
       intra_order="OLHC")

    print("== 参数邻域脆弱性 ==", flush=True)
    go("nb_atr2", "邻域: ATR下界 2.0", init_cash=INIT_CASH_MAIN, atr_k=(2.0, 4.5))
    go("nb_atr3", "邻域: ATR下界 3.0", init_cash=INIT_CASH_MAIN, atr_k=(3.0, 4.5))
    go("nb_vol07", "邻域: 量比 0.7", init_cash=INIT_CASH_MAIN, vol_ratio_max=0.7)

    print("== 12 只各自独立实验 (各 13,822.47) ==", flush=True)
    indep = {}
    for c in CODES:
        fresh()
        sim = E.Simulator(data, [c], init_cash=INIT_CASH_MAIN,
                          label=f"indep_{c}", scenario="单股独立实验")
        indep[c] = sim.run()
        print(f"  [{c}] {E.STOCKS[c][0]}: trades={len(indep[c].trades)} "
              f"closed={len([t for t in indep[c].trades if t.exit_date])}", flush=True)

    # ---------- 基准 ----------
    print("== 基准: 买入持有 ==", flush=True)
    bh = {c: buy_and_hold(data, c, INIT_CASH_MAIN, cal, s_i, e_i) for c in CODES}
    bh_alt = {c: buy_and_hold(data, c, INIT_CASH_ALT, cal, s_i, e_i) for c in CODES}
    eq_weight = []
    for c in CODES:
        bh_alt[c]["theoretical_fractional_return_pct"] = bh_alt[c]["return_pct"]
        eq_weight.append(bh_alt[c].get("net_return_pct", 0.0))
    ew_feasible = float(np.mean([v for v in eq_weight if v is not None])) if eq_weight else None

    # ---------- 汇总 ----------
    summary = {
        "study": "confirmed_policy_3y_20260914",
        "generated_at": pd.Timestamp.now().isoformat(timespec="seconds"),
        "status": "completed_minute_level_3y",
        "strategy_version_sell": "SELL-POLICY-v1.0-20260914",
        "buy_policy": "用户 2026-09-14 确认版 (固定参数, 未调参)",
        "backtest_window": {"start": E.BACKTEST_START, "end": E.BACKTEST_END,
                            "trading_days": e_i - s_i + 1},
        "data_source": {
            "provider": "baostock (免费公开, 匿名登录, 无需密钥)",
            "daily": "频率 d, adjustflag=2 前复权; 另取 adjustflag=3 不复权用于对账",
            "minute": "频率 5 (5分钟), adjustflag=2 前复权",
            "note": "5分钟为可获得的最细粒度; baostock 不提供 1 分钟。"
                    "东财/新浪分钟历史实测仅 32~42 个交易日, 无法用于三年验证。",
        },
        "minute_resolution_note": (
            "成交量同刻条件在 5 分钟网格上精确成立(9:45 为网格收盘时刻)。"
            "13:00 时刻与 11:30 时刻的累计量完全相同(中间不交易), 故窗口 13:00 起由 11:30 覆盖; "
            "下午首个可评估时刻为 13:05。"),
        "assumptions": {
            "slippage_base_single_side": E.SLIPPAGE_BASE,
            "commission_rate": E.COMMISSION_RATE, "commission_min": E.COMMISSION_MIN,
            "stamp_duty_sell": E.STAMP_RATE_SELL, "transfer_fee_single_side": E.TRANSFER_RATE,
            "lot": 100, "loss_budget": E.LOSS_BUDGET_PCT,
            "portfolio_risk_cap": E.PORTFOLIO_RISK_PCT, "single_mv_cap": E.SINGLE_MV_PCT,
            "hard_stop": E.HARD_STOP_PCT, "order_valid_min": E.ORDER_VALID_MIN,
            "price_basis_caveat": "仅前复权日线/分钟, 无复权因子与分红明细, 故 100 股整手、"
                                  "费用、现金账本只能标为近似",
            "intra_bar_order": "同一根 5 分钟K线内, 先按 bar high 更新 H/保护线, 再按 bar low 判触发"
                               "(悲观顺序, 不把有利顺序当事实)",
        },
        "scenarios": {}, "independent_experiments": {}, "benchmarks": {},
        "data_coverage": [], "blocked_legend": {},
        "minute_availability_probe": {
            "eastmoney_5min": "1536 根 / 32 个交易日 (2026-07-31~2026-09-14), start/end 参数被忽略",
            "eastmoney_1min": "ConnectionError (RemoteDisconnected), 且历史上限约 5 个交易日",
            "eastmoney_15/30/60min": "ConnectionError (IP 限流)",
            "sina_5min": "1970 根 / 42 个交易日 (2026-07-17~2026-09-14)",
            "sina_1min": "1970 根 / 9 个交易日 (2026-09-02~2026-09-14)",
            "baostock_5min": "38352 根 / 726 个交易日 (2023-06-01~2026-09-14) —— 采用",
            "conclusion": "三年分钟数据在东财/新浪不可得; baostock(免费公开, 匿名登录, 无需密钥, 不购买数据, 不绕过访问控制) 可得, 故本验证为真实三年分钟级回测。",
        },
        "gaps": [
            "自选股清单为 2026-09-14 快照回溯, 存在幸存者/选股前视偏差, 不是历史动态自选股池",
            "仅前复权价格, 无复权因子与分红明细 -> 100 股整手/费用/现金账本只能标为近似",
            "5 分钟为可获得最细粒度 (baostock 无 1 分钟)",
            "无法重现人工确认流程; 以「下单后延迟 0/5/15 分钟执行, 越界不成交」近似, 与真实提醒系统有差异",
            "日线代理层无法验证交易时间窗口与 15 分钟限价条件",
            "最高价与最低价盘中先后顺序未知, 采用悲观顺序并另做 OLHC 敏感性",
            "不假定涨跌停一定成交或一定不成交; 无法确定排队的场景保守跳过",
            "历史回放而非前瞻样本外证明, 不能推出未来收益",
        ],
    }

    for label, r in runs.items():
        summary["scenarios"][label] = metrics(r, cal, E.BACKTEST_START, E.BACKTEST_END)
    for c, r in indep.items():
        summary["independent_experiments"][c] = metrics(r, cal, E.BACKTEST_START, E.BACKTEST_END)
        summary["independent_experiments"][c]["name"] = E.STOCKS[c][0]

    summary["benchmarks"] = {
        "per_stock_buy_and_hold_13822": bh,
        "per_stock_buy_and_hold_100k": bh_alt,
        "equal_weight_12_feasible_100k_avg_return_pct": round(ew_feasible, 4) if ew_feasible is not None else None,
        "equal_weight_12_theoretical_fractional_avg_return_pct":
            round(float(np.mean([v["return_pct"] for v in bh.values()])), 4),
        "note": "买入持有=首日收盘买入、末日收盘卖出, 含双边费用与滑点; 独立实验收益不可相加当组合。",
    }

    # ---------- 数据覆盖 ----------
    cov = []
    for c in CODES:
        d5 = data[c]["min5"]
        win_days = [cal[i] for i in range(s_i, e_i + 1)]
        have5 = [d for d in win_days if d in d5]
        miss5 = [d for d in win_days if d not in d5]
        dl = data[c]["daily"]
        inwin = dl[(dl["date"] >= E.BACKTEST_START) & (dl["date"] <= E.BACKTEST_END)]
        cov.append({
            "stock": c, "name": E.STOCKS[c][0],
            "daily_rows": int(len(dl)), "daily_first": dl["date"].iloc[0], "daily_last": dl["date"].iloc[-1],
            "daily_rows_in_window": int(len(inwin)),
            "daily_halted_days_in_window": int((inwin["tradestatus"] == 0).sum()),
            "daily_missing_or_nan_close_in_window": int(inwin["close"].isna().sum()),
            "min5_rows": int(sum(len(v["hm"]) for v in d5.values())),
            "min5_days": len(d5),
            "min5_first_day": min(d5) if d5 else "", "min5_last_day": max(d5) if d5 else "",
            "min5_days_in_window": len(have5),
            "min5_missing_days_in_window": len(miss5),
            "min5_missing_days_sample": ",".join(miss5[:8]),
            "bars_per_day_mode": int(pd.Series([len(v["hm"]) for v in d5.values()]).mode().iloc[0]) if d5 else 0,
            "price_basis": "前复权(qfq, adjustflag=2)",
            "duplicate_dates_daily": int(len(dl) - dl["date"].nunique()),
        })
    summary["data_coverage"] = cov

    # ---------- 落盘 ----------
    with open(OUT / "summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2, default=str)

    # per_stock.csv
    rows = []
    for c, m in summary["independent_experiments"].items():
        rows.append({
            "stock": c, "name": m["name"],
            "total_return_pct": m.get("total_return_pct"), "annualized_pct": m.get("annualized_pct"),
            "max_drawdown_pct": m.get("max_drawdown_pct"), "n_closed_trades": m.get("n_closed_trades"),
            "win_rate_pct": m.get("win_rate_pct"), "avg_pnl_per_trade": m.get("avg_pnl_per_trade"),
            "profit_factor": m.get("profit_factor"), "realized_pnl": m.get("realized_pnl"),
            "unrealized_pnl_open": m.get("unrealized_pnl_open"),
            "end_equity": m.get("end_equity"), "avg_exposure_pct": m.get("avg_exposure_pct"),
            "fee_total": m.get("fee_total"), "max_consecutive_losses": m.get("max_consecutive_losses"),
            "bh_net_return_pct": bh[c].get("net_return_pct"),
            "yearly_2023": (m.get("yearly_return_pct") or {}).get("2023"),
            "yearly_2024": (m.get("yearly_return_pct") or {}).get("2024"),
            "yearly_2025": (m.get("yearly_return_pct") or {}).get("2025"),
            "yearly_2026": (m.get("yearly_return_pct") or {}).get("2026"),
            "blocked_json": json.dumps(m.get("blocked", {}), ensure_ascii=False),
        })
    pd.DataFrame(rows).to_csv(OUT / "per_stock.csv", index=False)

    # portfolio_equity.csv
    pe = []
    for label, r in runs.items():
        for row in r.daily_equity:
            pe.append({"run": label, **row})
    for c, r in indep.items():
        for row in r.daily_equity:
            pe.append({"run": f"indep_{c}", **row})
    pd.DataFrame(pe).to_csv(OUT / "portfolio_equity.csv", index=False)

    # trades.csv
    tr = []
    for label, r in runs.items():
        for t in r.trades:
            tr.append({"run": label, **t.__dict__})
    for c, r in indep.items():
        for t in r.trades:
            tr.append({"run": f"indep_{c}", **t.__dict__})
    pd.DataFrame(tr).to_csv(OUT / "trades.csv", index=False)

    # data_coverage.csv
    pd.DataFrame(cov).to_csv(OUT / "data_coverage.csv", index=False)

    print("\nDONE. files written to", OUT, flush=True)
    print(json.dumps(summary["scenarios"]["portfolio_main"], ensure_ascii=False, indent=2, default=str)[:2500], flush=True)


if __name__ == "__main__":
    main()
