# -*- coding: utf-8 -*-
"""
run_daily_proxy.py  —  三年日线代理敏感性研究 (非原规则完整回测)
================================================================
明确声明 (用户 2026-09-14 要求):
  * 代理只能用「前一日完整信号 + 下一日开盘检查可执行性/区间后买入」;
  * 「前一日全天量 / 此前5日全天均量 < 0.8」是**替代条件**, 不等价于盘中同刻累计量比;
  * 保护按 O-L-H-C 与 O-H-L-C 两条明确假设路径分别模拟, 不声称是严格收益上下界;
  * 交易时间窗口 (9:45-11:30 / 13:00-14:45) 与 15 分钟限价条件在日线**无法验证, 明确排除**;
  * 本脚本结果**不是**原规则回测, 只作脆弱性/方向性对照。
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

INIT_CASH_MAIN, INIT_CASH_ALT = 13822.47, 100000.0
CODES = list(E.STOCKS.keys())


def proxy_signals(data, code, cal):
    """返回 {D: dict(ma60_chg, hh20, atr14, vol_ratio, ref_close)} —— 全部来自 D-1 及更早。"""
    a = data[code]["np"]
    out = {}
    for i, d in enumerate(cal):
        if i < 70:
            continue
        j = i - 1                                   # 信号日 = 前一交易日
        ma60, ma60l = a["ma60"][j], a["ma60_lag5"][j]
        hh, atr, c = a["hh20"][j], a["atr14"][j], a["close"][j]
        v, vm = a["volume"][j], a["vol_ma5_prev"][j]
        if np.isnan(ma60) or np.isnan(ma60l) or np.isnan(hh) or np.isnan(atr) or np.isnan(vm):
            continue
        if not (c > ma60 and ma60 > ma60l):
            continue
        if atr <= 0 or vm <= 0:
            continue
        k = (hh - c) / atr
        if not (E.ATR_K_MIN <= k <= E.ATR_K_MAX):
            continue
        vr = v / vm
        if not (vr < E.VOL_RATIO_MAX):
            continue
        out[d] = {"ma60_chg": float(ma60 / ma60l - 1), "hh20": float(hh), "atr14": float(atr),
                  "vol_ratio": float(vr), "ref_close": float(c), "k_ref": float(k)}
    return out


def run_proxy(data, codes, *, init_cash, path="OLHC", slippage=E.SLIPPAGE_BASE,
              label="", scenario=""):
    cal = data["_calendar"]
    s_i, e_i = cal.index(E.BACKTEST_START), cal.index(E.BACKTEST_END)
    sig = {c: proxy_signals(data, c, cal) for c in codes}
    cash = init_cash
    positions, cooldown = {}, {}
    res = E.RunResult(label=label, scenario=scenario, init_cash=init_cash)
    a_all = {c: data[c]["np"] for c in codes}

    for i in range(s_i, e_i + 1):
        D = cal[i]
        for c in list(positions):
            SP.roll_trading_day(positions[c]["st"])

        # ---- 收盘代理: 先判退出 ----
        for c in list(positions):
            p = positions[c]; st = p["st"]; a = a_all[c]
            o, h, l, cl = a["open"][i], a["high"][i], a["low"][i], a["close"][i]
            if np.isnan(o):
                continue
            if path == "OLHC":
                # 严格 O-L-H-C: 当日低点发生在当日高点之前, 故当日低点只能用「当日之前」已确立的线判定;
                # 当日高点不得抬高线来触发当日低点。
                eff = st.effective_exit_line()
                fired = l <= eff
            else:  # OHLC: 先 high 抬高保护线, 再判 low (更保守, 更早退出)
                SP.update_quote(st, cl, quote_time=D, intraday_high=h)
                eff = st.effective_exit_line()
                fired = l <= eff
            if not fired:
                SP.update_quote(st, cl, quote_time=D, intraday_high=h)
                continue
            base = min(eff, o)
            fill = base * (1 - slippage)
            qty = st.sellable_qty
            if qty <= 0:
                continue
            amt = fill * qty; fee = E.sell_fees(amt)
            cash += amt - fee
            tr = p["trade"]; tr.exit_date, tr.exit_time, tr.exit_price = D, "OPEN", fill
            tr.exit_reason = "日线代理触发"
            tr.sell_fee += fee; tr.partial = qty < st.total_qty
            res.fee_total += fee
            res.slip_total += abs(amt - base * qty)
            if tr.partial:
                SP.confirm_sell(st, qty)
                st.pending_exit = {"event_id": "proxy", "reason": "日线代理", "line": eff,
                                   "at": D, "qty_sellable": 0, "qty_pending": st.today_new_qty}
                p["forced_exit"] = {"reason": "日线代理", "line": eff}
            else:
                SP.confirm_clear(st)
                tr.pnl_net = round((amt - fee) - (tr.entry_price * tr.qty + tr.buy_fee), 2)
                tr.pnl_pct = round(tr.pnl_net / (tr.entry_price * tr.qty + tr.buy_fee) * 100, 4)
                try:
                    tr.holding_days = int((pd.Timestamp(D) - pd.Timestamp(tr.entry_date)).days)
                except Exception:
                    pass
                cooldown[c] = {"clear_date": D, "earliest_buy": None}
                del positions[c]

        # T+1 被挡部分的次日开盘续退出
        for c in list(positions):
            st = positions[c]["st"]
            if st.total_qty > 0 and st.is_exit_pending():
                o = a_all[c]["open"][i]
                if np.isnan(o):
                    continue
                ex = positions[c].get("forced_exit")
                base = min(o, ex["line"]) if ex else o
                fill = base * (1 - slippage)
                amt = fill * st.total_qty; fee = E.sell_fees(amt)
                cash += amt - fee
                tr = positions[c]["trade"]
                tr.exit_date, tr.exit_time, tr.exit_price = D, "OPEN", fill
                tr.exit_reason = (tr.exit_reason or "触发") + "+T+1续退出"
                tr.sell_fee += fee; tr.partial = True
                tr.pnl_net = round((amt - fee) - (tr.entry_price * tr.qty + tr.buy_fee), 2)
                tr.pnl_pct = round(tr.pnl_net / (tr.entry_price * tr.qty + tr.buy_fee) * 100, 4)
                res.fee_total += fee
                SP.confirm_clear(st)
                cooldown[c] = {"clear_date": D, "earliest_buy": None}
                del positions[c]

        # ---- 开盘买入 (信号来自 D-1) ----
        cands = []
        for c in codes:
            if c in positions:
                res.block("held_no_add")
                continue
            cd = cooldown.get(c)
            if cd is not None and (cd["earliest_buy"] is None or D < cd["earliest_buy"]):
                res.block("cooldown_block"); continue
            s = sig[c].get(D)
            if s is None:
                continue
            if data[c]["daily"].iloc[i]["tradestatus"] == 0:
                res.block("halted"); continue
            o = a_all[c]["open"][i]
            if np.isnan(o) or o <= 0:
                res.block("no_open"); continue
            k = (s["hh20"] - o) / s["atr14"]           # 开盘重新验证区间
            if not (E.ATR_K_MIN <= k <= E.ATR_K_MAX):
                res.block("open_band_fail"); continue
            cands.append((s["ma60_chg"], c, o))
        if cands:
            cands.sort(key=lambda x: (-x[0], x[1]))
            for chg, c, o in cands:
                nav = cash + sum(positions[x]["st"].total_qty * a_all[x]["close"][i]
                                 for x in positions if not np.isnan(a_all[x]["close"][i]))
                port_risk = 0.0
                for x, p in positions.items():
                    px = a_all[x]["close"][i]
                    if np.isnan(px):
                        continue
                    line = p["st"].effective_exit_line()
                    if px > line:
                        port_risk += (px - line) * p["st"].total_qty + E.sell_fees(px * p["st"].total_qty)
                fill = o * (1 + slippage)
                n_max = int(cash // (fill * 100)) + 2
                best = 0
                for kk in range(max(1, n_max), 0, -1):
                    qty = 100 * kk; amt = fill * qty; fee = E.buy_fees(amt)
                    if amt + fee > cash + 1e-9 or amt > E.SINGLE_MV_PCT * nav + 1e-9:
                        continue
                    C = SP.round_cost((amt + fee) / qty)
                    hard = SP.round_price(C * (1 - E.HARD_STOP_PCT))
                    risk = (fill - hard) * qty + E.sell_fees(fill * qty)
                    if risk > E.LOSS_BUDGET_PCT * nav + 1e-9:
                        continue
                    if port_risk + risk > E.PORTFOLIO_RISK_PCT * nav + 1e-9:
                        continue
                    best = kk; break
                if best == 0:
                    res.block("size_block"); continue
                qty = 100 * best; amt = fill * qty; fee = E.buy_fees(amt)
                C = SP.round_cost((amt + fee) / qty)
                st = SP.init_position(("sh" if c.startswith("6") else "sz") + c,
                                      E.STOCKS[c][0], C, qty, sellable_qty=0, today_new_qty=qty,
                                      entry_date=D)
                tr = E.Trade(stock=c, name=E.STOCKS[c][0], entry_date=D, entry_time="OPEN",
                             entry_price=fill, qty=qty, buy_fee=fee, cost_incl_fee=C,
                             hard_stop=st.hard_stop)
                cash -= amt + fee
                res.fee_total += fee
                res.trades.append(tr)
                positions[c] = {"st": st, "trade": tr}
                res.block("bought")
                break

        # 冷却重置 (收盘三条件任一失效)
        for c, cd in cooldown.items():
            if cd["earliest_buy"] is not None or D <= cd["clear_date"]:
                continue
            a = a_all[c]
            broken = False
            if not np.isnan(a["ma60"][i]) and a["close"][i] <= a["ma60"][i]:
                broken = True
            elif not np.isnan(a["ma60_lag5"][i]) and a["ma60"][i] <= a["ma60_lag5"][i]:
                broken = True
            if not (np.isnan(a["hh20"][i]) or np.isnan(a["atr14"][i])) and a["atr14"][i] > 0:
                kk = (a["hh20"][i] - a["close"][i]) / a["atr14"][i]
                if not (E.ATR_K_MIN <= kk <= E.ATR_K_MAX):
                    broken = True
            if not np.isnan(a["vol_ma5_prev"][i]) and a["vol_ma5_prev"][i] > 0:
                if a["volume"][i] / a["vol_ma5_prev"][i] >= E.VOL_RATIO_MAX:
                    broken = True
            if broken:
                cd["earliest_buy"] = cal[i + 1] if i + 1 < len(cal) else None

        mv = sum(p["st"].total_qty * a_all[x]["close"][i] for x, p in positions.items()
                 if not np.isnan(a_all[x]["close"][i]))
        res.daily_equity.append({"date": D, "cash": round(cash, 2), "market_value": round(mv, 2),
                                 "equity": round(cash + mv, 2), "n_pos": len(positions),
                                 "exposure_pct": round(mv / (cash + mv) * 100, 3) if cash + mv > 0 else 0.0})

    for c, p in positions.items():
        st = p["st"]; px = data[c].get("last_close", st.cost)
        res.open_positions.append({"stock": c, "name": E.STOCKS[c][0], "qty": st.total_qty,
                                   "cost": st.cost, "last_price": round(px, 2),
                                   "unrealized_pnl": round((px - st.cost) * st.total_qty, 2),
                                   "unrealized_pct": round((px / st.cost - 1) * 100, 3),
                                   "peak_h": st.peak_h, "protection_active": st.protection_active,
                                   "exit_line": st.effective_exit_line()})
    res.extra["end_cash"] = round(cash, 2)
    return res


def main():
    import run_confirmed_policy_3y as R
    data = E.load_all(CODES)
    cal = data["_calendar"]
    out = {"study": "daily_proxy_sensitivity", "generated_at": pd.Timestamp.now().isoformat(timespec="seconds"),
           "disclaimer": "日线代理敏感性研究 — 非原规则完整回测; 交易时间窗口与15分钟限价条件不可验证已排除; "
                         "量比用前一日全天量/此前5日全天均量替代, 不等价于盘中同刻累计量比。",
           "paths": {}, "per_stock": {}}
    for path in ("OLHC", "OHLC"):
        for cash, tag in ((INIT_CASH_MAIN, "13822"), (INIT_CASH_ALT, "100k")):
            for c in CODES:
                data[c]["last_close"] = 0.0
            r = run_proxy(data, CODES, init_cash=cash, path=path,
                          label=f"proxy_{path}_{tag}", scenario=f"日线代理 {path} / {tag}")
            m = R.metrics(r, cal, E.BACKTEST_START, E.BACKTEST_END)
            out["paths"][f"{path}_{tag}"] = m
            print(f"[{path} {tag}] ret={m.get('total_return_pct')}% trades={m.get('n_closed_trades')} "
                  f"wr={m.get('win_rate_pct')}", flush=True)
        for c in CODES:
            data[c]["last_close"] = 0.0
            r = run_proxy(data, [c], init_cash=INIT_CASH_MAIN, path=path, label=f"proxy_{path}_{c}",
                          scenario="日线代理 单股")
            out["per_stock"].setdefault(c, {})[path] = R.metrics(r, cal, E.BACKTEST_START, E.BACKTEST_END)
    with open(HERE / "proxy_sensitivity.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, default=str)
    print("DONE proxy", flush=True)


if __name__ == "__main__":
    main()
