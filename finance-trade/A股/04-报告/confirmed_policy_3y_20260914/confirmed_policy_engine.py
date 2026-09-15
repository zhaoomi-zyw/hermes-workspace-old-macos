# -*- coding: utf-8 -*-
"""
confirmed_policy_engine.py  (v2, 2026-09-14)
============================================
「已确认买卖策略」三年验证 — 隔离研究引擎

原则
----
* 只读 data_cache/ ; 只写本目录。不触碰生产 StateStore / cron / 持仓 / 交易日志, 不发消息, 不下单。
* 卖出规则直接调用生产纯函数模块 strategies/sell_policy.py (SELL-POLICY-v1.0-20260914),
  但每笔用独立 PositionState, 绝不读写 StateStore。

未来函数防呆
------------
日线指标 (MA60, 5日前MA60, ATR14 Wilder, 20日最高价 HH) 全部只用已完成交易日:
对交易日 D 的一切盘中时刻, 取截至 D-1 的值, 当日全天固定。ATR14 用 Wilder 递推,
初值=前14个TR的简单平均。成交量条件用「当日截至当前时刻累计量 / 前5个有效交易日同刻平均累计量」。
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
CACHE = HERE / "data_cache"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from strategies import sell_policy as SP  # noqa: E402

STOCKS: Dict[str, Tuple[str, str]] = {
    "601138": ("工业富联", "sh"), "002156": ("通富微电", "sz"),
    "600487": ("亨通光电", "sh"), "603380": ("易德龙",   "sh"),
    "600988": ("赤峰黄金", "sh"), "600460": ("士兰微",   "sh"),
    "600522": ("中天科技", "sh"), "002396": ("星网锐捷", "sz"),
    "600219": ("南山铝业", "sh"), "000878": ("云南铜业", "sz"),
    "000938": ("紫光股份", "sz"), "600760": ("中航沈飞", "sh"),
}

BACKTEST_START = "2023-09-14"
BACKTEST_END = "2026-09-14"

MA_LEN, MA_LAG = 60, 5
HH_LOOKBACK, ATR_LEN = 20, 14
ATR_K_MIN, ATR_K_MAX = 2.5, 4.5
VOL_RATIO_MAX, VOL_REF_DAYS = 0.8, 5

ALLOWED_TIMES = (["09:45", "09:50", "09:55"]
                 + [f"10:{m:02d}" for m in range(0, 60, 5)]
                 + [f"11:{m:02d}" for m in range(0, 35, 5)]
                 + [f"13:{m:02d}" for m in range(5, 60, 5)]
                 + [f"14:{m:02d}" for m in range(0, 50, 5)])

LOSS_BUDGET_PCT, PORTFOLIO_RISK_PCT, SINGLE_MV_PCT = 0.02, 0.04, 0.35
HARD_STOP_PCT, ORDER_VALID_MIN = 0.06, 15

COMMISSION_RATE, COMMISSION_MIN = 0.00025, 5.0
STAMP_RATE_SELL, TRANSFER_RATE = 0.0005, 0.00001
SLIPPAGE_BASE = 0.001


def buy_fees(amount: float) -> float:
    return max(COMMISSION_MIN, amount * COMMISSION_RATE) + amount * TRANSFER_RATE


def sell_fees(amount: float) -> float:
    return (max(COMMISSION_MIN, amount * COMMISSION_RATE)
            + amount * TRANSFER_RATE + amount * STAMP_RATE_SELL)


# ---------------------------------------------------------------------------
def wilder_atr14(h, l, c) -> np.ndarray:
    n = len(c); tr = np.full(n, np.nan)
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr = np.full(n, np.nan)
    if n <= ATR_LEN: return atr
    atr[ATR_LEN] = np.nanmean(tr[1:ATR_LEN + 1])
    for i in range(ATR_LEN + 1, n):
        atr[i] = (atr[i - 1] * (ATR_LEN - 1) + tr[i]) / ATR_LEN
    return atr


def load_all(codes: List[str]) -> Dict[str, dict]:
    """载入全部数据并预计算; 返回含 '_calendar' 的容器。"""
    data: Dict[str, dict] = {}
    daily_raw: Dict[str, pd.DataFrame] = {}
    for code in codes:
        df = pd.read_csv(CACHE / f"daily_qfq_{code}.csv", dtype=str)
        for c in ("open", "high", "low", "close", "volume", "amount", "turn"):
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        df["tradestatus"] = pd.to_numeric(df.get("tradestatus"), errors="coerce").fillna(1).astype(int)
        df["date"] = df["date"].astype(str)
        df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        daily_raw[code] = df

    cal = sorted(set().union(*[set(d["date"]) for d in daily_raw.values()]))
    cal = [d for d in cal if BACKTEST_START > d or True]     # 保留全历史(预热用)
    data["_calendar"] = cal

    for code in codes:
        df = daily_raw[code].set_index("date").reindex(cal)
        for c in ("open", "high", "low", "close", "volume"):
            df[c] = df[c].astype(float)
        df["tradestatus"] = df["tradestatus"].fillna(0).astype(int)
        df = df.reset_index().rename(columns={"index": "date"})
        data[code] = {"daily": build_daily_indicators(df)}

    # 5 分钟
    for code in codes:
        data[code]["min5"], data[code]["min5_index"] = {}, {}
        p = CACHE / f"min5_qfq_{code}.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p, dtype=str)
        for c in ("open", "high", "low", "close", "volume", "amount"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
        t = df["time"].astype(str)
        df["date"] = t.str[:4] + "-" + t.str[4:6] + "-" + t.str[6:8]
        df["hm"] = t.str[8:10] + ":" + t.str[10:12]
        df = df.drop_duplicates(subset=["date", "hm"]).sort_values(["date", "hm"])
        for dd, g in df.groupby("date", sort=True):
            g = g.sort_values("hm")
            hm = g["hm"].to_numpy()
            v = g["volume"].to_numpy(dtype=float)
            data[code]["min5"][str(dd)] = {
                "hm": hm, "o": g["open"].to_numpy(float), "h": g["high"].to_numpy(float),
                "l": g["low"].to_numpy(float), "c": g["close"].to_numpy(float),
                "v": v, "cum": np.cumsum(v),
            }
            data[code]["min5_index"][str(dd)] = {h: i for i, h in enumerate(hm)}
        data[code]["last_close"] = 0.0

    # 成交量同刻比
    for code in codes:
        data[code]["volratio"] = build_volume_ratio(data[code]["min5"], cal)

    # 快速访问层: numpy 数组 + 同刻量比矩阵 (避免逐行 iloc, 大幅提速)
    aidx = {hm: i for i, hm in enumerate(ALLOWED_TIMES)}
    for code in codes:
        d = data[code]["daily"]
        data[code]["np"] = {
            "open": d["open"].to_numpy(float),
            "high": d["high"].to_numpy(float),
            "low": d["low"].to_numpy(float),
            "sig_ma60": d["sig_ma60"].to_numpy(float),
            "sig_ma60_lag5": d["sig_ma60_lag5"].to_numpy(float),
            "sig_hh20": d["sig_hh20"].to_numpy(float),
            "sig_atr14": d["sig_atr14"].to_numpy(float),
            "sig_ma60_chg": d["sig_ma60_chg"].to_numpy(float),
            "close": d["close"].to_numpy(float),
            "ma60": d["ma60"].to_numpy(float),
            "ma60_lag5": d["ma60_lag5"].to_numpy(float),
            "hh20": d["hh20"].to_numpy(float),
            "atr14": d["atr14"].to_numpy(float),
            "vol_ma5_prev": d["vol_ma5_prev"].to_numpy(float),
            "volume": d["volume"].to_numpy(float),
        }
        vr = np.full((len(cal), len(ALLOWED_TIMES)), np.nan)
        for di_, dt in enumerate(cal):
            for hm, v in data[code]["volratio"].get(dt, {}).items():
                if v is not None:
                    vr[di_, aidx[hm]] = v
        data[code]["vr_arr"] = vr

    data["_aidx"] = aidx
    # 当日时刻网格 + 日线索引映射
    for code in codes:
        data[code]["di_map"] = {d: i for i, d in enumerate(data[code]["daily"]["date"])}
    return data


def build_volume_ratio(min5, dates) -> Dict[str, Dict[str, Optional[float]]]:
    idx_of = {dt: {hm: i for i, hm in enumerate(blk["hm"])} for dt, blk in min5.items()}
    out: Dict[str, Dict[str, Optional[float]]] = {}
    for pos, dt in enumerate(dates):
        out[dt] = {}
        blk = min5.get(dt)
        if blk is None:
            continue
        prev_valid = [d for d in dates[max(0, pos - VOL_REF_DAYS):pos] if d in min5]
        ci = idx_of[dt]
        for hm in ALLOWED_TIMES:
            i = ci.get(hm)
            out[dt][hm] = None
            if i is None or len(prev_valid) < VOL_REF_DAYS:
                continue
            refs, ok = [], True
            for pd_ in prev_valid[-VOL_REF_DAYS:]:
                j = idx_of[pd_].get(hm)
                if j is None:
                    ok = False; break
                refs.append(min5[pd_]["cum"][j])
            if not ok or not refs:
                continue
            ref = float(np.mean(refs))
            if ref > 0:
                out[dt][hm] = float(blk["cum"][i] / ref)
    return out


# ---------------------------------------------------------------------------
@dataclass
class Trade:
    stock: str; name: str; entry_date: str; entry_time: str; entry_price: float
    qty: int; buy_fee: float; cost_incl_fee: float; hard_stop: float
    exit_date: str = ""; exit_time: str = ""; exit_price: float = 0.0
    exit_reason: str = ""; sell_fee: float = 0.0; pnl_net: float = 0.0
    pnl_pct: float = 0.0; holding_days: int = 0; slip_cost: float = 0.0
    partial: bool = False; rank_score: float = 0.0


@dataclass
class RunResult:
    label: str; scenario: str; init_cash: float
    daily_equity: List[dict] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)
    blocked: Dict[str, int] = field(default_factory=dict)
    open_positions: List[dict] = field(default_factory=list)
    fee_total: float = 0.0; slip_total: float = 0.0
    extra: Dict = field(default_factory=dict)

    def block(self, k: str, n: int = 1):
        self.blocked[k] = self.blocked.get(k, 0) + n


class Simulator:
    def __init__(self, data, codes, *, init_cash, slippage=SLIPPAGE_BASE,
                 delay_bars=0, label="", scenario="", vol_ratio_max=VOL_RATIO_MAX,
                 atr_k=(ATR_K_MIN, ATR_K_MAX), intra_order="OHLC"):
        self.data, self.codes, self.init_cash = data, codes, init_cash
        self.slippage, self.delay_bars = slippage, delay_bars
        self.vol_ratio_max = vol_ratio_max
        self.atr_k = atr_k
        self.intra_order = intra_order
        self.res = RunResult(label=label, scenario=scenario, init_cash=init_cash)

    # ------------------------------------------------------------------
    def run(self) -> RunResult:
        data = self.data
        cal = data["_calendar"]
        start_i = cal.index(BACKTEST_START); end_i = cal.index(BACKTEST_END)
        cash = self.init_cash
        positions: Dict[str, dict] = {}
        cooldown: Dict[str, dict] = {}
        pending: Optional[dict] = None

        for di in range(start_i, end_i + 1):
            D = cal[di]
            # 交易日开始: T+1 解禁
            for code in list(positions):
                SP.roll_trading_day(positions[code]["st"])

            # 昨日被 T+1 挡住、仍有待退出的部分 -> 今日首个可交易时点继续退出
            for code in list(positions):
                p = positions[code]; st = p["st"]
                if st.total_qty > 0 and st.is_exit_pending():
                    blk = data[code]["min5"].get(D)
                    if blk is None:
                        continue
                    base = float(blk["o"][0]); fill = base * (1 - self.slippage)
                    amt = fill * st.total_qty; fee = sell_fees(amt)
                    cash += amt - fee
                    tr = p["trade"]
                    tr.exit_date, tr.exit_time, tr.exit_price = D, str(blk["hm"][0]), fill
                    tr.exit_reason = (tr.exit_reason or "退出") + "+T+1续退出"
                    tr.sell_fee += fee; tr.partial = True
                    self.res.fee_total += fee
                    self.res.slip_total += abs(amt - base * st.total_qty)
                    self._close_trade(tr)
                    cooldown[code] = {"clear_date": D, "earliest_buy": None, "reset_date": None}
                    del positions[code]

            hm_grid = self._day_grid(D)
            if not hm_grid:
                self._mark_equity(D, "15:00", cash, positions)
                self._update_cooldown_close(D, cooldown, di)
                continue

            holder = {"cash": cash}
            for ti, hm in enumerate(hm_grid):
                # 1) 持仓退出
                self._exit_step(D, hm, holder, positions, cooldown)
                # 2) 待执行限价单
                if pending is not None and ti >= pending["exec_ti"]:
                    holder["cash"] = self._execute_pending(pending, D, hm, di, holder["cash"], positions)
                    pending = None
                # 3) 新推荐 (若无在途单)
                if pending is None and hm in ALLOWED_TIMES:
                    pending = self._recommend(D, hm, ti, di, holder["cash"], positions, cooldown)
                # 4) delay=0 时同刻立即执行
                if pending is not None and ti >= pending["exec_ti"]:
                    holder["cash"] = self._execute_pending(pending, D, hm, di, holder["cash"], positions)
                    pending = None

            cash = holder["cash"]

            self._mark_equity(D, "15:00", cash, positions)
            self._update_cooldown_close(D, cooldown, di)

        self._finalize(cash, positions)
        return self.res

    # ------------------------------------------------------------------
    def _day_grid(self, D) -> List[str]:
        for code in self.codes:
            blk = self.data[code]["min5"].get(D)
            if blk is not None:
                return list(blk["hm"])
        return []

    def _bar(self, code, D, hm):
        blk = self.data[code]["min5"].get(D)
        if blk is None: return None
        j = self.data[code]["min5_index"][D].get(hm)
        if j is None: return None
        return blk, j

    # ------------------------------------------------------------------
    def _exit_step(self, D, hm, holder, positions, cooldown):
        for code in list(positions):
            p = positions[code]; st = p["st"]
            if st.total_qty <= 0: continue
            r = self._bar(code, D, hm)
            if r is None: continue
            blk, j = r
            bh, bl, bc, bo = float(blk["h"][j]), float(blk["l"][j]), float(blk["c"][j]), float(blk["o"][j])
            if self.intra_order == "OLHC":
                # 严格 O-L-H-C: 本根K线低点发生在高点之前 -> 低点只能用本根之前的线判定
                eff = st.effective_exit_line()
                fired = bl <= eff
                if not fired:
                    SP.update_quote(st, bc, quote_time=f"{D} {hm}", intraday_high=bh)
                    continue
            else:
                # 悲观顺序 (默认): 先用 bar high 更新 H/线, 再用 bar low 判触发
                SP.update_quote(st, bc, quote_time=f"{D} {hm}", intraday_high=bh)
                eff = st.effective_exit_line()
                if bl > eff:
                    continue
            ev = SP.evaluate_exit(st, eff, quote_time=f"{D} {hm}")
            if ev is None:
                ev = {"event_id": f"{st.lifecycle_id}:cont", "reason": "续触发", "line": eff,
                      "price": eff, "qty_sellable": st.sellable_qty,
                      "qty_pending": st.today_new_qty, "at": f"{D} {hm}"}
            SP.fire_exit(st, ev)
            qty = st.sellable_qty
            if qty <= 0:
                continue                      # 全部被 T+1 锁住, 次日首笔退出
            base = min(eff, bo)               # 不保证在虚构保护线成交; 跳空则按更差的开盘价
            fill = base * (1 - self.slippage)
            amt = fill * qty; fee = sell_fees(amt)
            holder["cash"] += amt - fee
            self.res.fee_total += fee
            self.res.slip_total += abs(amt - base * qty)
            tr = p["trade"]
            if qty >= st.total_qty:
                tr.exit_date, tr.exit_time, tr.exit_price = D, hm, fill
                tr.exit_reason = ev["reason"]; tr.sell_fee += fee
                SP.confirm_clear(st); self._close_trade(tr)
                cooldown[code] = {"clear_date": D, "earliest_buy": None, "reset_date": None}
                del positions[code]
            else:
                tr.partial = True; tr.sell_fee += fee
                tr.exit_reason = ev["reason"]
                SP.confirm_sell(st, qty)

    # ------------------------------------------------------------------
    def _execute_pending(self, pending, D, hm, di, cash, positions) -> float:
        code = pending["code"]
        r = self._bar(code, D, hm)
        if r is None or hm not in ALLOWED_TIMES:
            self.res.block("order_expired"); return cash
        blk, j = r
        bc = float(blk["c"][j]); L = pending["limit"]
        cond = self._entry_conditions(code, D, hm, bc, di)
        if not cond["ok"]:
            self.res.block("recheck_fail_" + cond["reason"]); return cash
        if bc > L + 1e-9:
            self.res.block("price_band_exceeded"); return cash
        fill = bc * (1 + self.slippage)
        got = self._try_buy(code, D, hm, fill, cash, positions, di)
        if not got["ok"]:
            self.res.block("size_" + got["reason"]); return cash
        self.res.trades.append(got["trade"])
        positions[code] = got["pos"]
        return cash - got["cash_used"]

    # ------------------------------------------------------------------
    def _recommend(self, D, hm, ti, di, cash, positions, cooldown) -> Optional[dict]:
        cands = []
        for code in self.codes:
            if code in positions:
                continue
            cd = cooldown.get(code)
            if cd is not None and (cd["earliest_buy"] is None or D < cd["earliest_buy"]):
                self.res.block("cooldown_block")
                continue
            r = self._bar(code, D, hm)
            if r is None:
                self.res.block("no_min_data"); continue
            blk, j = r
            price = float(blk["c"][j])
            cond = self._entry_conditions(code, D, hm, price, di)
            if not cond["ok"]:
                self.res.block("cond_" + cond["reason"]); continue
            cands.append((float(self.data[code]["np"]["sig_ma60_chg"][di]), code, price))
        if not cands:
            return None
        cands.sort(key=lambda x: (-x[0], x[1]))       # MA60涨幅降序; 并列代码升序(复现约定)
        for chg, code, price in cands:
            probe = self._try_buy(code, D, hm, price * (1 + self.slippage), cash, positions, di)
            if not probe["ok"]:
                self.res.block("size_" + probe["reason"])
                continue
            self.res.block("recommended")
            return {"code": code, "limit": float(np.ceil(round(price, 6) * 100) / 100),
                    "placed_ti": ti,
                    "exec_ti": ti + self.delay_bars, "placed_hm": hm, "placed_date": D,
                    "rank_score": chg}
        return None

    # ------------------------------------------------------------------
    def _entry_conditions(self, code, D, hm, price, di) -> dict:
        d = self.data[code]
        if d["min5"].get(D) is None:
            return {"ok": False, "reason": "no_min_data"}
        a = d["np"]
        ma60, ma60l, hh, atr = (a["sig_ma60"][di], a["sig_ma60_lag5"][di],
                                a["sig_hh20"][di], a["sig_atr14"][di])
        if np.isnan(ma60) or np.isnan(ma60l) or np.isnan(hh) or np.isnan(atr):
            return {"ok": False, "reason": "warmup"}
        if not (price > ma60 and ma60 > ma60l):
            return {"ok": False, "reason": "ma60"}
        if atr <= 0:
            return {"ok": False, "reason": "atr"}
        k = (hh - price) / atr
        if not (self.atr_k[0] <= k <= self.atr_k[1]):
            return {"ok": False, "reason": "atr_band"}
        vr = d["vr_arr"][di, self.data["_aidx"][hm]]
        if np.isnan(vr):
            return {"ok": False, "reason": "vol_missing"}
        if not (vr < self.vol_ratio_max):
            return {"ok": False, "reason": "vol_ratio"}
        return {"ok": True, "reason": "", "vr": float(vr), "k": float(k)}

    # ------------------------------------------------------------------
    def _try_buy(self, code, D, hm, fill_price, cash, positions, di) -> dict:
        nav = cash + sum(p["st"].total_qty * self._cur_price(c, D, hm)
                         for c, p in positions.items())
        port_risk = 0.0
        for c, p in positions.items():
            st = p["st"]; px = self._cur_price(c, D, hm)
            line = st.effective_exit_line()
            if px > line:
                port_risk += (px - line) * st.total_qty + sell_fees(px * st.total_qty)
        n_max = int(cash // (fill_price * 100)) + 2
        best, reasons = 0, []
        for k in range(max(1, n_max), 0, -1):
            qty = 100 * k
            amt = fill_price * qty; fee = buy_fees(amt)
            if amt + fee > cash + 1e-9:
                reasons.append("cash"); continue
            C = SP.round_cost((amt + fee) / qty)
            hard = SP.round_price(C * (1 - HARD_STOP_PCT))
            risk = (fill_price - hard) * qty + sell_fees(fill_price * qty)
            if risk > LOSS_BUDGET_PCT * nav + 1e-9:
                reasons.append("single_risk"); continue
            if port_risk + risk > PORTFOLIO_RISK_PCT * nav + 1e-9:
                reasons.append("port_risk"); continue
            if amt > SINGLE_MV_PCT * nav + 1e-9:
                reasons.append("mv_cap"); continue
            best = k; break
        if best == 0:
            return {"ok": False, "reason": reasons[-1] if reasons else "lot_100"}
        qty = 100 * best
        amt = fill_price * qty; fee = buy_fees(amt)
        C = SP.round_cost((amt + fee) / qty)
        st = SP.init_position(("sh" if code.startswith("6") else "sz") + code,
                              STOCKS[code][0], C, qty, sellable_qty=0, today_new_qty=qty,
                              entry_date=D)
        tr = Trade(stock=code, name=STOCKS[code][0], entry_date=D, entry_time=hm,
                   entry_price=fill_price, qty=qty, buy_fee=fee, cost_incl_fee=C,
                   hard_stop=st.hard_stop)
        self.res.fee_total += fee
        self.res.slip_total += abs(fill_price - fill_price / (1 + self.slippage)) * qty
        return {"ok": True, "cash_used": amt + fee,
                "pos": {"st": st, "trade": tr, "entry_i": di}, "trade": tr}

    # ------------------------------------------------------------------
    def _cur_price(self, code, D, hm) -> float:
        blk = self.data[code]["min5"].get(D)
        if blk is not None:
            j = self.data[code]["min5_index"][D].get(hm)
            if j is None:
                k = int(np.searchsorted(blk["hm"], hm, side="right")) - 1
                j = k if k >= 0 else None
            if j is not None:
                px = float(blk["c"][j])
                self.data[code]["last_close"] = px
                return px
        di = self.data[code]["di_map"].get(D)
        if di is not None:
            px = float(self.data[code]["daily"].iloc[di]["close"])
            if not np.isnan(px):
                self.data[code]["last_close"] = px
                return px
        return self.data[code].get("last_close", 0.0)

    def _close_trade(self, tr: Trade):
        amt_buy = tr.entry_price * tr.qty
        amt_sell = tr.exit_price * tr.qty
        pnl = (amt_sell - tr.sell_fee) - (amt_buy + tr.buy_fee)
        tr.pnl_net = round(pnl, 2)
        tr.pnl_pct = round(pnl / (amt_buy + tr.buy_fee) * 100, 4) if amt_buy + tr.buy_fee else 0.0
        try:
            tr.holding_days = int((pd.Timestamp(tr.exit_date) - pd.Timestamp(tr.entry_date)).days)
        except Exception:
            tr.holding_days = 0

    def _mark_equity(self, D, hm, cash, positions):
        mv = sum(p["st"].total_qty * self._cur_price(c, D, hm) for c, p in positions.items())
        self.res.daily_equity.append({
            "date": D, "cash": round(cash, 2), "market_value": round(mv, 2),
            "equity": round(cash + mv, 2), "n_pos": len(positions),
            "exposure_pct": round(mv / (cash + mv) * 100, 3) if (cash + mv) > 0 else 0.0,
        })

    def _update_cooldown_close(self, D, cooldown, di):
        cal = self.data["_calendar"]
        for code, cd in cooldown.items():
            if cd["earliest_buy"] is not None or D <= cd["clear_date"]:
                continue
            row = self.data[code]["daily"].iloc[di]
            broken = False
            if not pd.isna(row["ma60"]) and row["close"] <= row["ma60"]:
                broken = True
            elif not pd.isna(row["ma60_lag5"]) and row["ma60"] <= row["ma60_lag5"]:
                broken = True
            if not (pd.isna(row["hh20"]) or pd.isna(row["atr14"])) and row["atr14"] > 0:
                k = (row["hh20"] - row["close"]) / row["atr14"]
                if not (ATR_K_MIN <= k <= ATR_K_MAX):
                    broken = True
            if not pd.isna(row["vol_ma5_prev"]) and row["vol_ma5_prev"] > 0:
                if row["volume"] / row["vol_ma5_prev"] >= VOL_RATIO_MAX:
                    broken = True
            if broken:
                cd["reset_date"] = D
                cd["earliest_buy"] = cal[di + 1] if di + 1 < len(cal) else None

    def _finalize(self, cash, positions):
        for c, p in positions.items():
            st = p["st"]
            px = self.data[c].get("last_close", st.cost)
            self.res.open_positions.append({
                "stock": c, "name": STOCKS[c][0], "qty": st.total_qty, "cost": st.cost,
                "last_price": round(px, 2),
                "unrealized_pnl": round((px - st.cost) * st.total_qty, 2),
                "unrealized_pct": round((px / st.cost - 1) * 100, 3),
                "peak_h": st.peak_h, "protection_active": st.protection_active,
                "exit_line": st.effective_exit_line(),
            })
        self.res.extra["end_cash"] = round(cash, 2)


def build_daily_indicators(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["ma60"] = d["close"].rolling(MA_LEN).mean()
    d["ma60_lag5"] = d["ma60"].shift(MA_LAG)
    d["hh20"] = d["high"].rolling(HH_LOOKBACK).max()
    d["atr14"] = wilder_atr14(d["high"].to_numpy(float), d["low"].to_numpy(float),
                              d["close"].to_numpy(float))
    d["vol_ma5_prev"] = d["volume"].shift(1).rolling(VOL_REF_DAYS).mean()
    for c in ("ma60", "ma60_lag5", "hh20", "atr14"):
        d[f"sig_{c}"] = d[c].shift(1)          # 当日信号取 T-1 完成值 -> 无未来函数
    d["sig_ma60_chg"] = d["sig_ma60"] / d["sig_ma60_lag5"] - 1.0
    return d
