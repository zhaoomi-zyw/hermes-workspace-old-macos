# -*- coding: utf-8 -*-
"""
confirmed_policy_engine.py  (v4, 2026-09-15)
============================================
「已确认买卖策略」5 分钟近似验证引擎 —— 依第二轮独立复核意见修正。

v3 -> v4 修正 (仅这三项, 固定用户策略, 不做参数优化)
----------------------------------------------------
G1 T+1 语义: T+1 只阻止**成交**, 不阻止**触发**。v3 用 `entry_today` 跳过买入当
   整天的 H/保护/止损更新, 属严重错误。v4 恢复: 买入后即按有序价格事件更新 H /
   开保护 / 判触发; 当日可卖为 0 时 fire_exit 并保留 pending, 下一交易日即使反弹
   也在首个可成交时点退出。
G2 开盘成交不再用未来信息: 信号在 5 分钟 bar 收盘生成, 候选成交价是**下一根 bar 的
   开盘价**; 量比重验**只用开盘之前已完成 bar 的数据**; 当前 bar 最终的 low / volume
   不参与 "该开盘是否成交" 的判定。fill = open*(1+slip) 必须 <= 限价且落在 ATR 允许
   区间, 否则不成交并可等下一个 open 直到真实到期(含 14:45 / 午休按交易时钟)。
   整根零量 bar 用于过滤时, 作为**无法交易的数据缺口**独立披露。
   同一根 bar 内的次序: 先在开盘成交, 再处理该 bar 之后的 H/L/C 退出更新,
   因此买入当根的 T+1 触发事件也能被记录。
G3 稳健性: `_t1_continuation` 先判 blk 是否存在再取索引(停牌不 KeyError);
   卖出滑点不得越过已知跌停下限; 行情 last 状态为 Simulator 实例私有, 场景间不共享。

仍在的限制 (未解决, 明确保留)
------------------------------
* 5 分钟粒度: 无法恢复逐笔与排队; bar 内 H/L/C 先后顺序不可知, 只能给出两种路径。
* 仅前复权价, 无复权因子/分红明细 -> 100 股整手与现金账本为近似。
* 卖出用 bar 内价格点近似成交, 与真实挂单排队仍不同。
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
from strategies import buy_policy as BP   # noqa: E402  (买入口径唯一权威, 2026-09-15 接入)

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


def _bar_closes(sessions, bar_min=5) -> List[str]:
    """会话内的 bar 收盘时刻(与 BP.SESSIONS 单一来源)。
    上午首个收盘 = 会话起点(09:45); 下午首个 = 会话起点+bar_min(13:05,
    因 13:00 累计量与前收等价)。"""
    out = []
    for k, (a, b) in enumerate(sessions):
        t = a if k == 0 else a + bar_min
        while t <= b:
            out.append(f"{t // 100:02d}:{t % 100:02d}")
            h, m = t // 100, t % 100 + bar_min
            t = (h + m // 60) * 100 + (m % 60)
    return out


ALLOWED_TIMES = _bar_closes(BP.SESSIONS)

# ============ 策略参数：全部来自 strategies/buy_policy.py（不得在此复制） ============
MA_LEN, MA_LAG = BP.MA60_N, BP.MA60_LOOKBACK              # 60, 5
HH_LOOKBACK, ATR_LEN = BP.H20_N, BP.ATR_N                 # 20, 14
ATR_K_MIN, ATR_K_MAX = BP.ATR_LOW, BP.ATR_HIGH            # 2.5, 4.5
VOL_RATIO_MAX, VOL_REF_DAYS = BP.VOL_RATIO_MAX, BP.VOL_LOOKBACK_DAYS   # 0.8, 5
LOSS_BUDGET_PCT, PORTFOLIO_RISK_PCT, SINGLE_MV_PCT = (
    BP.RISK_SINGLE_PCT, BP.RISK_PORT_PCT, BP.POS_SINGLE_PCT)           # 2%, 4%, 35%
HARD_STOP_PCT, ORDER_VALID_MIN = BP.HARD_STOP_PCT, BP.ALERT_TTL_MIN    # 6%, 15

# ============ 费率：同样来自 buy_policy（⚠️ 该块 FEE_UNCALIBRATED, 见 evidence.md） ============
COMMISSION_RATE, COMMISSION_MIN = BP.FEE_BUY, BP.COMMISSION_MIN
STAMP_RATE_SELL, TRANSFER_RATE = BP.STAMP_RATE_SELL, BP.TRANSFER_RATE

# ============ 回测假设（非策略参数，仅数据/撮合近似） ============
BAR_MIN = 5
LIMIT_PCT_MAIN = 0.10
SLIPPAGE_BASE = 0.001


def buy_fees(amount: float) -> float:
    return max(COMMISSION_MIN, amount * COMMISSION_RATE) + amount * TRANSFER_RATE


def sell_fees(amount: float) -> float:
    return (max(COMMISSION_MIN, amount * COMMISSION_RATE)
            + amount * TRANSFER_RATE + amount * STAMP_RATE_SELL)


def clock_min(hm: str) -> int:
    """交易时钟分钟: 09:30->0, 11:30->120, 13:00->120(午休压缩), 14:45->225, 15:00->240."""
    h, m = int(hm[:2]), int(hm[3:5])
    t = h * 60 + m
    if t <= 11 * 60 + 30:
        return t - (9 * 60 + 30)
    return 120 + (t - 13 * 60)


CLK_1445 = clock_min("14:45")
CLK_FIRST_ALLOWED = clock_min("09:45")


def wilder_atr14(h, l, c) -> np.ndarray:
    n = len(c)
    tr = np.full(n, np.nan)
    for i in range(1, n):
        tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    atr = np.full(n, np.nan)
    if n <= ATR_LEN:
        return atr
    atr[ATR_LEN] = np.nanmean(tr[1:ATR_LEN + 1])
    for i in range(ATR_LEN + 1, n):
        atr[i] = (atr[i - 1] * (ATR_LEN - 1) + tr[i]) / ATR_LEN
    return atr


def build_daily_indicators(df: pd.DataFrame) -> pd.DataFrame:
    d = df.copy()
    d["ma60"] = d["close"].rolling(MA_LEN).mean()
    d["ma60_lag5"] = d["ma60"].shift(MA_LAG)
    d["hh20"] = d["high"].rolling(HH_LOOKBACK).max()
    d["atr14"] = wilder_atr14(d["high"].to_numpy(float), d["low"].to_numpy(float),
                              d["close"].to_numpy(float))
    d["vol_ma5_prev"] = d["volume"].shift(1).rolling(VOL_REF_DAYS).mean()
    # ── 2026-10-13 新增：20日涨幅（⑤ 相对强度的个股侧）─────────────────
    # 窗口取 HH_LOOKBACK(=20)，与条件②的 H20 同窗口；sig_ 前缀表示「最近已完成交易日」，
    # 与其它 sig_* 字段口径一致（均为 .shift(1)），保证不含未来函数。
    d["ret20"] = d["close"] / d["close"].shift(HH_LOOKBACK) - 1.0
    for c in ("ma60", "ma60_lag5", "hh20", "atr14"):
        d[f"sig_{c}"] = d[c].shift(1)
    d["sig_ret20"] = d["ret20"].shift(1)                                          # noqa: E501
    d["sig_ma60_chg"] = d["sig_ma60"] / d["sig_ma60_lag5"] - 1.0
    return d


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


def _open_hm_list(hm) -> List[str]:
    """每根 bar 的**开盘时刻** = 前一根 bar 的结束时刻; 当日首根为 09:30;
    午休后首根(13:05)的开盘时刻为 13:00 (不是 11:30)。"""
    out = []
    for i, x in enumerate(hm):
        if i == 0:
            out.append("09:30")
        elif x == "13:05":
            out.append("13:00")
        else:
            out.append(str(hm[i - 1]))
    return out


def _assemble(daily_dfs: Dict[str, pd.DataFrame],
              min5_dfs: Dict[str, pd.DataFrame]) -> Dict[str, dict]:
    """由日线/5分钟 DataFrame 组装引擎数据结构 (load_all 与合成测试共用)。"""
    data: Dict[str, dict] = {}
    codes = list(daily_dfs.keys())
    norm: Dict[str, pd.DataFrame] = {}
    for code in codes:
        df = daily_dfs[code].copy()
        df["date"] = df["date"].astype(str)
        for c in ("open", "high", "low", "close", "volume", "preclose"):
            df[c] = pd.to_numeric(df.get(c), errors="coerce")
        if "tradestatus" not in df.columns:
            df["tradestatus"] = 1
        df["tradestatus"] = pd.to_numeric(df["tradestatus"], errors="coerce").fillna(1).astype(int)
        df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
        norm[code] = df

    cal = sorted(set().union(*[set(d["date"]) for d in norm.values()]))
    data["_calendar"] = cal

    for code in codes:
        df = norm[code].set_index("date").reindex(cal)
        for c in ("open", "high", "low", "close", "volume", "preclose"):
            df[c] = df[c].astype(float)
        df["tradestatus"] = df["tradestatus"].fillna(0).astype(int)
        df = df.reset_index().rename(columns={"index": "date"})
        data[code] = {"daily": build_daily_indicators(df)}

    for code in codes:
        data[code]["min5"], data[code]["min5_index"] = {}, {}
        m5 = min5_dfs.get(code)
        if m5 is not None and len(m5):
            m5 = m5.copy()
            for c in ("open", "high", "low", "close", "volume"):
                m5[c] = pd.to_numeric(m5[c], errors="coerce")
            m5["date"] = m5["date"].astype(str)
            m5 = m5.drop_duplicates(subset=["date", "hm"]).sort_values(["date", "hm"])
            for dd, g in m5.groupby("date", sort=True):
                g = g.sort_values("hm")
                hm = g["hm"].astype(str).to_numpy()
                v = g["volume"].to_numpy(dtype=float)
                clk = np.array([clock_min(x) for x in hm], dtype=float)
                wstart = np.concatenate([[0.0], clk[:-1]])
                data[code]["min5"][str(dd)] = {
                    "hm": hm, "clk": clk, "wstart": wstart,
                    "open_hm": np.array(_open_hm_list(hm)),
                    "o": g["open"].to_numpy(float), "h": g["high"].to_numpy(float),
                    "l": g["low"].to_numpy(float), "c": g["close"].to_numpy(float),
                    "v": v, "cum": np.cumsum(v)}
                data[code]["min5_index"][str(dd)] = {h: i for i, h in enumerate(hm)}

    for code in codes:
        data[code]["volratio"] = build_volume_ratio(data[code]["min5"], cal)

    aidx = {hm: i for i, hm in enumerate(ALLOWED_TIMES)}
    for code in codes:
        d = data[code]["daily"]
        pre = d["preclose"].to_numpy(float)
        close_prev = d["close"].shift(1).to_numpy(float)
        base = np.where(np.isnan(pre) | (pre <= 0), close_prev, pre)
        data[code]["np"] = {
            "open": d["open"].to_numpy(float), "high": d["high"].to_numpy(float),
            "low": d["low"].to_numpy(float), "close": d["close"].to_numpy(float),
            "sig_ma60": d["sig_ma60"].to_numpy(float),
            "sig_ma60_lag5": d["sig_ma60_lag5"].to_numpy(float),
            "sig_hh20": d["sig_hh20"].to_numpy(float),
            "sig_atr14": d["sig_atr14"].to_numpy(float),
            "sig_ma60_chg": d["sig_ma60_chg"].to_numpy(float),
            "sig_ret20": d["sig_ret20"].to_numpy(float),
            "ma60": d["ma60"].to_numpy(float), "ma60_lag5": d["ma60_lag5"].to_numpy(float),
            "hh20": d["hh20"].to_numpy(float), "atr14": d["atr14"].to_numpy(float),
            "vol_ma5_prev": d["vol_ma5_prev"].to_numpy(float),
            "volume": d["volume"].to_numpy(float),
            "tradestatus": d["tradestatus"].to_numpy(int),
            "limit_up": np.round(base * (1 + LIMIT_PCT_MAIN), 2),
            "limit_down": np.round(base * (1 - LIMIT_PCT_MAIN), 2)}
        vr = np.full((len(cal), len(ALLOWED_TIMES)), np.nan)
        for di_, dt in enumerate(cal):
            for hm, v in data[code]["volratio"].get(dt, {}).items():
                if v is not None:
                    vr[di_, aidx[hm]] = v
        data[code]["vr_arr"] = vr

    data["_aidx"] = aidx
    for code in codes:
        data[code]["di_map"] = {d: i for i, d in enumerate(data[code]["daily"]["date"])}
    return data


def _load_bench_ret20(cache) -> Dict[str, float]:
    """沪深300 的 20 日涨幅（按日期索引），供条件⑤相对强度使用。

    与个股 `sig_ret20` 同为「上一已完成交易日」口径（.shift(HH_LOOKBACK) 后再 .shift(1)），
    保证两边同基准、且都不含未来函数。文件不存在时返回 {} ⇒ ⑤ 判为「不可判」而拒绝入场
    （按线上纪律：无法确认 ⇒ 不放行）。
    """
    p = Path(cache) / "idx_hs300.csv"
    if not p.exists():
        return {}
    b = pd.read_csv(p)
    b["date"] = b["date"].astype(str)
    b = b.sort_values("date").reset_index(drop=True)
    b["ret20"] = b["close"] / b["close"].shift(HH_LOOKBACK) - 1.0
    b["sig_ret20"] = b["ret20"].shift(1)
    return {str(d): (None if pd.isna(v) else float(v))
            for d, v in zip(b["date"], b["sig_ret20"])}


def load_all(codes: List[str]) -> Dict[str, dict]:
    daily_dfs, min5_dfs = {}, {}
    for code in codes:
        daily_dfs[code] = pd.read_csv(CACHE / f"daily_qfq_{code}.csv", dtype=str)
        p = CACHE / f"min5_qfq_{code}.csv"
        if p.exists():
            m5 = pd.read_csv(p, dtype=str)
            t = m5["time"].astype(str)
            m5["hm"] = t.str[8:10] + ":" + t.str[10:12]
            m5["date"] = t.str[:4] + "-" + t.str[4:6] + "-" + t.str[6:8]
            min5_dfs[code] = m5[["date", "hm", "open", "high", "low", "close", "volume"]]
    data = _assemble(daily_dfs, min5_dfs)
    data["_bench_ret20"] = _load_bench_ret20(CACHE)
    return data


@dataclass
class Trade:
    stock: str; name: str
    entry_date: str; entry_time: str          # entry_time = 成交所在 bar 的**开盘时刻**
    entry_bar_hm: str = ""                    # 成交所在 bar 的结束时刻
    limit_price: float = 0.0                  # 限价 L
    fill_price: float = 0.0                   # 实际成交价 (= bar 开盘价)
    qty: int = 0; buy_fee: float = 0.0
    cost_incl_fee: float = 0.0                # 全口径成本价 (含费含滑点) / 股
    hard_stop: float = 0.0
    slip_cost: float = 0.0
    cash_out: float = 0.0
    exit_date: str = ""; exit_time: str = ""; exit_point: str = ""
    exit_price: float = 0.0; exit_limit_price: float = 0.0
    exit_reason: str = ""; sell_fee: float = 0.0
    proceeds_net: float = 0.0; sold_qty: int = 0; exit_slip: float = 0.0
    pnl_net: float = 0.0; pnl_pct: float = 0.0
    holding_days: int = 0; partial: bool = False
    rank_score: float = 0.0
    placed_hm: str = ""; delay_min: int = 0
    t1_deferred: bool = False


@dataclass
class RunResult:
    label: str; scenario: str; init_cash: float
    daily_equity: List[dict] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)
    blocked: Dict[str, int] = field(default_factory=dict)
    open_positions: List[dict] = field(default_factory=list)
    risk_audit: List[dict] = field(default_factory=list)
    events: List[dict] = field(default_factory=list)
    fee_total: float = 0.0; slip_total: float = 0.0
    extra: Dict = field(default_factory=dict)

    def block(self, k: str, n: int = 1):
        self.blocked[k] = self.blocked.get(k, 0) + n

    def accrue(self, fee: float, slip: float):
        self.fee_total += fee
        self.slip_total += slip


class Simulator:
    def __init__(self, data, codes, *, init_cash, slippage=SLIPPAGE_BASE, delay_min=0,
                 label="", scenario="", vol_ratio_max=VOL_RATIO_MAX,
                 atr_k=(ATR_K_MIN, ATR_K_MAX), path="OHLC", sell_params=None,
                 rs_gate=False):
        """rs_gate: 条件⑤相对强度闸门。
            False(默认) = 关闭 ⇒ 与既有基线(BUY-LOW-v1 三条件)逐位一致；
            True        = 要求个股 20 日涨幅 ≥ 沪深300 20 日涨幅（无法确认则拒绝入场）。
            新增约束只收紧、不放宽：rs_gate=True 是基线条件的**子集**。
        """
        if path not in ("OHLC", "OLHC"):
            raise ValueError("path 必须为 OHLC 或 OLHC")
        self.data, self.codes, self.init_cash = data, codes, init_cash
        self.slippage, self.delay_min = slippage, delay_min
        self.vol_ratio_max, self.atr_k, self.path = vol_ratio_max, atr_k, path
        self.rs_gate = bool(rs_gate)
        self.params = sell_params or SP.DEFAULT_PARAMS
        self.res = RunResult(label=label, scenario=scenario, init_cash=init_cash)
        self._last_px: Dict[str, float] = {}      # G3: 实例私有, 场景间不共享

    # ==================== 主循环 ====================
    def run(self) -> RunResult:
        cal = self.data["_calendar"]
        s_i, e_i = cal.index(BACKTEST_START), cal.index(BACKTEST_END)
        holder = {"cash": self.init_cash}
        positions: Dict[str, dict] = {}
        cooldown: Dict[str, dict] = {}
        pending: Optional[dict] = None

        for di in range(s_i, e_i + 1):
            D = cal[di]
            for code in list(positions):
                SP.roll_trading_day(positions[code]["st"])

            if pending is not None and pending["placed_date"] != D:
                self.res.block("order_expired_released_at_day_open")
                pending = None

            self._t1_continuation(D, di, holder, positions, cooldown)   # G3

            gr = self._day_grid(D)
            if gr is None:
                self._mark_equity(D, holder["cash"], positions, di)
                self._update_cooldown_close(D, cooldown, di)
                continue
            hm_arr, wstart_arr, open_arr = gr

            for ti in range(len(hm_arr)):
                entered = set()
                # (1) 先在本根 bar 的开盘尝试成交 (G2: 只用开盘前已完成 bar 的数据)
                if pending is not None:
                    consumed, filled = self._try_fill_at_open(
                        pending, D, ti, hm_arr, wstart_arr, holder, positions, di)
                    if filled:
                        entered.add(pending["code"])
                    if consumed:
                        pending = None
                # (2) 再处理该 bar 之后的 H/L/C 退出事件 (含本根刚买入的仓位, 记录 T+1 触发)
                if len(hm_arr):
                    self._exit_step(D, ti, hm_arr, holder, positions, cooldown, entered)
                # (3) bar 收盘生成新推荐
                if pending is None:
                    pending = self._recommend(D, ti, hm_arr, holder["cash"], positions,
                                              cooldown, di)

            self._mark_equity(D, holder["cash"], positions, di)
            self._update_cooldown_close(D, cooldown, di)

        self._finalize(holder["cash"], positions)
        return self.res

    # ==================== T+1 次要退出 (G3) ====================
    def _t1_continuation(self, D, di, holder, positions, cooldown):
        for code in list(positions):
            p = positions[code]; st = p["st"]
            if st.total_qty <= 0 or not st.is_exit_pending():
                continue
            blk = self.data[code]["min5"].get(D)      # G3: 先判存在, 停牌不 KeyError
            if blk is None:
                self.res.block("t1_exit_wait_no_min_data_halted")
                continue
            ld = self.data[code]["np"]["limit_down"][di]
            for k in range(len(blk["hm"])):
                if float(blk["v"][k]) <= 0:
                    self.res.block("data_gap_zero_volume_bar_no_fill"); continue
                if not np.isnan(ld) and float(blk["h"][k]) <= ld + 1e-9:
                    self.res.block("no_fill_sealed_limit_down"); continue
                base = float(blk["o"][k])
                if not np.isnan(ld):
                    base = max(base, ld)
                fill = base * (1 - self.slippage)
                if not np.isnan(ld):
                    fill = max(fill, ld)              # G3: 滑点不得越过跌停下限
                amt = fill * st.total_qty; fee = sell_fees(amt)
                holder["cash"] += amt - fee
                tr = p["trade"]
                tr.exit_date, tr.exit_time, tr.exit_point = D, str(blk["hm"][k]), "T+1首笔"
                tr.exit_limit_price, tr.exit_price = base, fill
                tr.exit_reason = (tr.exit_reason or "退出") + "+T+1续退出"
                tr.sell_fee += fee; tr.partial = True; tr.t1_deferred = True
                tr.proceeds_net += amt - fee
                tr.sold_qty += st.total_qty
                tr.exit_slip += abs(base - fill) * st.total_qty
                self.res.accrue(fee, abs(base - fill) * st.total_qty)
                self.res.events.append({"date": D, "time": str(blk["hm"][k]), "code": code,
                                        "type": "T1_DEFERRED_EXIT", "price": fill,
                                        "qty": st.total_qty})
                self._close_trade(tr)
                cooldown[code] = {"clear_date": D, "earliest_buy": None, "reset_date": None}
                del positions[code]
                break

    # ==================== bar 内退出 (G1/G2) ====================
    def _exit_step(self, D, ti, hm_arr, holder, positions, cooldown, entered):
        hm = hm_arr[ti]
        for code in list(positions):
            p = positions[code]; st = p["st"]
            if st.total_qty <= 0:
                continue
            r = self._bar(code, D, hm)
            if r is None:
                continue
            blk, j = r
            v = float(blk["v"][j])
            o, h, l, c = (float(blk["o"][j]), float(blk["h"][j]),
                          float(blk["l"][j]), float(blk["c"][j]))
            ld = self.data[code]["np"]["limit_down"][self.data[code]["di_map"][D]]
            newly = code in entered

            hit = None
            if not newly:
                eff_prev = st.effective_exit_line()
                if o <= eff_prev:
                    hit = (o, "OPEN")                     # 开盘先对「本根之前的线」
            if hit is None:
                if self.path == "OHLC":
                    SP.update_quote(st, h, quote_time=f"{D} {hm}", intraday_high=h,
                                    params=self.params)
                    eff = st.effective_exit_line()
                    if l <= eff:
                        hit = (eff, "LOW")
                    elif c <= eff:
                        hit = (c, "CLOSE")
                else:
                    eff_prev = st.effective_exit_line()
                    if l <= eff_prev:
                        hit = (eff_prev, "LOW")
                    else:
                        SP.update_quote(st, h, quote_time=f"{D} {hm}", intraday_high=h,
                                        params=self.params)
                        eff = st.effective_exit_line()
                        if c <= eff:
                            hit = (c, "CLOSE")
            if hit is None:
                continue

            price_pt, pt_code = hit
            # --- 触发事件 (G1: 与能否成交分离; 买入当日也必须记录) ---
            ev = SP.evaluate_exit(st, price_pt, quote_time=f"{D} {hm}", params=self.params)
            if ev is None:
                ev = {"event_id": f"{st.lifecycle_id}:cont",
                      "reason": ("盈利保护" if st.protection_active and st.profit_line > 0
                                 and price_pt <= st.profit_line else "硬止损"),
                      "line": st.effective_exit_line(), "price": price_pt,
                      "qty_sellable": st.sellable_qty, "qty_pending": st.today_new_qty,
                      "at": f"{D} {hm}"}
            is_new = SP.fire_exit(st, ev)
            if is_new:
                self.res.events.append({"date": D, "time": hm, "code": code,
                                        "type": "EXIT_TRIGGER", "point": pt_code,
                                        "reason": ev["reason"], "line": ev.get("line"),
                                        "price": price_pt, "qty_sellable": st.sellable_qty})

            # --- 可执行性 ---
            if v <= 0:
                self.res.block("data_gap_zero_volume_bar_no_fill"); continue
            if not np.isnan(ld) and h <= ld + 1e-9:
                self.res.block("no_fill_sealed_limit_down"); continue
            qty = st.sellable_qty
            if qty <= 0:
                self.res.block("trigger_recorded_t1_blocked_fill")   # 留 pending
                continue
            base = price_pt if np.isnan(ld) else max(price_pt, ld)
            fill = base * (1 - self.slippage)
            if not np.isnan(ld):
                fill = max(fill, ld)
            amt = fill * qty; fee = sell_fees(amt)
            holder["cash"] += amt - fee
            self.res.accrue(fee, abs(base - fill) * qty)
            tr = p["trade"]
            tr.exit_date, tr.exit_time, tr.exit_point = D, hm, pt_code
            tr.exit_limit_price, tr.exit_price = base, fill
            tr.exit_reason = ev["reason"]
            tr.sell_fee += fee
            tr.proceeds_net += amt - fee
            tr.sold_qty += qty
            tr.exit_slip += abs(base - fill) * qty
            self.res.events.append({"date": D, "time": hm, "code": code,
                                    "type": "EXIT_FILL", "price": fill, "qty": qty})
            if qty >= st.total_qty:
                SP.confirm_clear(st); self._close_trade(tr)
                cooldown[code] = {"clear_date": D, "earliest_buy": None, "reset_date": None}
                del positions[code]
            else:
                tr.partial = True
                SP.confirm_sell(st, qty)

    # ==================== 开盘成交 (G2) ====================
    def _vr_at_open(self, code, D, ti, hm_arr, di) -> Optional[float]:
        """开盘成交前的量比重验: 使用**开盘之前已完成 bar** 的累计量同刻比。"""
        if ti <= 0:
            return None
        prev_hm = str(hm_arr[ti - 1])
        ai = self.data["_aidx"].get(prev_hm)
        if ai is None:
            return None
        v = self.data[code]["vr_arr"][di, ai]
        return None if np.isnan(v) else float(v)

    def _try_fill_at_open(self, pending, D, ti, hm_arr, wstart_arr, holder, positions, di):
        """返回 (consumed, filled)。"""
        code = pending["code"]
        ws = float(wstart_arr[ti])
        if ws > pending["expires_clk"] or ws > CLK_1445:
            self.res.block("order_expired_no_fill"); return True, False
        if ws < pending["eligible_clk"]:
            return False, False
        if not (CLK_FIRST_ALLOWED <= ws <= CLK_1445):
            return False, False                       # 开盘时刻不在允许买入时段
        r = self._bar(code, D, hm_arr[ti])
        if r is None:
            return False, False
        blk, j = r
        a = self.data[code]["np"]
        if a["tradestatus"][di] == 0:
            self.res.block("halted_no_fill"); return True, False
        if float(blk["v"][j]) <= 0:
            # 整根零量 bar: 无法判断该开盘是否可成交 -> 作为数据缺口披露, 本根不成交
            self.res.block("data_gap_zero_volume_bar_no_fill"); return False, False
        o = float(blk["o"][j])
        fill = o * (1 + self.slippage)
        L = pending["limit"]
        if fill > L + 1e-9:
            self.res.block("no_fill_open_above_limit"); return False, False
        lu = a["limit_up"][di]
        if not np.isnan(lu) and o > lu + 1e-9:
            self.res.block("no_fill_open_above_limit_up"); return False, False
        vr = self._vr_at_open(code, D, ti, hm_arr, di)
        if vr is None:
            self.res.block("no_fill_vol_ref_missing"); return False, False
        if not (vr < self.vol_ratio_max):
            self.res.block("no_fill_vol_ratio_at_open"); return False, False
        ma60, ma60l = a["sig_ma60"][di], a["sig_ma60_lag5"][di]
        if np.isnan(ma60) or np.isnan(ma60l) or not (fill > ma60 and ma60 > ma60l):
            self.res.block("no_fill_ma60"); return False, False
        hh, atr = a["sig_hh20"][di], a["sig_atr14"][di]
        if np.isnan(hh) or np.isnan(atr) or atr <= 0:
            self.res.block("no_fill_atr_missing"); return False, False
        k = (hh - fill) / atr
        if not (self.atr_k[0] <= k <= self.atr_k[1]):
            self.res.block("no_fill_atr_band"); return False, False
        got = self._try_buy(code, D, str(blk["open_hm"][j]), str(hm_arr[ti]), L, o,
                            holder["cash"], positions, di)
        if not got["ok"]:
            self.res.block("size_" + got["reason"]); return False, False
        tr = got["trade"]
        tr.placed_hm = pending["placed_hm"]
        tr.delay_min = self.delay_min
        self.res.trades.append(tr)
        self.res.events.append({"date": D, "time": tr.entry_time, "code": code,
                                "type": "ENTRY_FILL", "limit": L, "fill": o,
                                "qty": tr.qty, "vr_at_open": vr, "k": k})
        positions[code] = got["pos"]
        holder["cash"] -= got["cash_used"]
        return True, True

    # ==================== 推荐 ====================
    def _recommend(self, D, ti, hm_arr, cash, positions, cooldown, di) -> Optional[dict]:
        hm = str(hm_arr[ti])
        if hm not in ALLOWED_TIMES:
            return None
        placed_clk = clock_min(hm)
        cands = []
        for code in self.codes:
            if code in positions:
                continue
            cd = cooldown.get(code)
            if cd is not None and (cd["earliest_buy"] is None or D < cd["earliest_buy"]):
                self.res.block("cooldown_block"); continue
            r = self._bar(code, D, hm)
            if r is None:
                self.res.block("no_min_data"); continue
            blk, j = r
            if float(blk["v"][j]) <= 0:
                self.res.block("no_min_data_zero_volume"); continue
            if self.data[code]["np"]["tradestatus"][di] == 0:
                self.res.block("halted"); continue
            price = float(blk["c"][j])
            cond = self._entry_conditions(code, D, hm, price, di)
            if not cond["ok"]:
                self.res.block("cond_" + cond["reason"]); continue
            cands.append((float(self.data[code]["np"]["sig_ma60_chg"][di]), code, price))
        if not cands:
            return None
        cands.sort(key=lambda x: (-x[0], x[1]))
        for chg, code, price in cands:
            L = float(np.ceil(round(price, 6) * 100) / 100)
            probe = self._size(code, D, hm, L, cash, positions, di)
            if not probe["ok"]:
                self.res.block("size_" + probe["reason"]); continue
            self.res.block("recommended")
            return {"code": code, "limit": L, "placed_date": D, "placed_hm": hm,
                    "placed_clk": placed_clk,
                    "eligible_clk": placed_clk + self.delay_min,
                    "expires_clk": min(placed_clk + ORDER_VALID_MIN, CLK_1445),
                    "rank_score": chg}
        return None

    # ==================== 条件 / 定价 / 下单 ====================
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
        # ── 条件⑤ 相对强度（默认关闭；rs_gate=True 时才启用）──────────────
        # 判定顺序与线上一致：⑤ 排在最后一道（①②③之后）。
        # 无法确认（基准缺失/个股数据缺）⇒ 拒绝入场，不静默放行。
        if self.rs_gate:
            bench = self.data.get("_bench_ret20") or {}
            b = bench.get(D)
            s_ret = a["sig_ret20"][di]
            if b is None or np.isnan(s_ret):
                return {"ok": False, "reason": "rs20_unavailable"}
            if not (s_ret >= b):
                return {"ok": False, "reason": "rs20"}
        return {"ok": True, "reason": "", "vr": float(vr), "k": float(k)}

    def _order_math(self, fill: float, qty: int) -> dict:
        """fill = bar 开盘价 (实际成交价); 现金流出含买费与滑点。"""
        amount = fill * qty
        buy = buy_fees(amount)
        slip = fill * self.slippage * qty
        cash_out = amount + buy + slip
        cost = SP.round_cost(cash_out / qty)
        hs = (self.params.hard_stop_pct if self.params else HARD_STOP_PCT)
        hard = SP.round_price(cost * (1 - hs))
        risk = (cost - hard) * qty + sell_fees(max(cost, hard) * qty)
        return {"amount": amount, "buy_fee": buy, "slip_cost": slip, "cost": cost,
                "hard_stop": hard, "risk": risk, "cash_out": cash_out}

    def _size(self, code, D, hm, L, cash, positions, di, ref_price=None) -> dict:
        """纯计算探针 (不改 res / 不改状态)。ref_price 缺省用限价做上界估算。"""
        nav = self._nav(cash, positions, D, hm)
        port_risk = self._port_risk(positions, D, hm)
        px = L if ref_price is None else ref_price
        n_max = int(cash // max(px * 100, 1e-9)) + 2
        best, reasons = 0, []
        for k in range(max(1, n_max), 0, -1):
            qty = 100 * k
            m = self._order_math(px, qty)
            if m["cash_out"] > cash + 1e-9:
                reasons.append("cash"); continue
            if m["risk"] > LOSS_BUDGET_PCT * nav + 1e-9:
                reasons.append("single_risk"); continue
            if port_risk + m["risk"] > PORTFOLIO_RISK_PCT * nav + 1e-9:
                reasons.append("port_risk"); continue
            if m["amount"] > SINGLE_MV_PCT * nav + 1e-9:
                reasons.append("mv_cap"); continue
            best = k; break
        if best == 0:
            return {"ok": False, "reason": reasons[-1] if reasons else "lot_100"}
        qty = 100 * best
        m = self._order_math(px, qty)
        return {"ok": True, "qty": qty, "nav": nav, "port_risk_before": port_risk, **m}

    def _try_buy(self, code, D, entry_time, entry_bar_hm, L, fill, cash, positions, di) -> dict:
        s = self._size(code, D, entry_bar_hm, L, cash, positions, di, ref_price=fill)
        if not s["ok"]:
            return s
        st = SP.init_position(("sh" if code.startswith("6") else "sz") + code,
                              STOCKS[code][0], s["cost"], s["qty"],
                              sellable_qty=0, today_new_qty=s["qty"], entry_date=D,
                              params=self.params)
        tr = Trade(stock=code, name=STOCKS[code][0], entry_date=D, entry_time=entry_time,
                   entry_bar_hm=entry_bar_hm, limit_price=L, fill_price=fill, qty=s["qty"],
                   buy_fee=s["buy_fee"], cost_incl_fee=s["cost"], hard_stop=s["hard_stop"],
                   slip_cost=s["slip_cost"], cash_out=s["cash_out"])
        self.res.accrue(s["buy_fee"], s["slip_cost"])
        self.res.risk_audit.append({
            "date": D, "time": entry_time, "code": code, "qty": s["qty"],
            "limit_price": L, "fill_price": fill, "nav": round(s["nav"], 2),
            "port_risk_before": round(s["port_risk_before"], 2), "new_risk": round(s["risk"], 4),
            "amount": round(s["amount"], 2),
            "single_mv_cap_amt": round(SINGLE_MV_PCT * s["nav"], 2),
            "single_risk_cap_amt": round(LOSS_BUDGET_PCT * s["nav"], 2),
            "port_risk_cap_amt": round(PORTFOLIO_RISK_PCT * s["nav"], 2),
            "port_risk_after": round(s["port_risk_before"] + s["risk"], 2)})
        return {"ok": True, "cash_used": s["cash_out"],
                "pos": {"st": st, "trade": tr, "entry_i": di}, "trade": tr}

    # ==================== 估值 / 工具 ====================
    def _cur_price(self, code, D, hm) -> float:
        blk = self.data[code]["min5"].get(D)
        if blk is not None:
            j = self.data[code]["min5_index"][D].get(hm)
            if j is None:
                k = int(np.searchsorted(blk["hm"], hm, side="right")) - 1
                j = k if k >= 0 else None
            if j is not None:
                px = float(blk["c"][j]); self._last_px[code] = px; return px
        di = self.data[code]["di_map"].get(D)
        if di is not None and di > 0:
            px = self.data[code]["np"]["close"][di - 1]
            if not np.isnan(px):
                self._last_px[code] = px; return px
        return self._last_px.get(code, 0.0)

    def _bar(self, code, D, hm):
        blk = self.data[code]["min5"].get(D)
        if blk is None:
            return None
        j = self.data[code]["min5_index"][D].get(hm)
        if j is None:
            return None
        return blk, j

    def _day_grid(self, D):
        for code in self.codes:
            g = self.data[code]["min5"].get(D)
            if g is not None:
                return g["hm"], g["wstart"], g["open_hm"]
        return None

    def _nav(self, cash, positions, D, hm):
        return cash + sum(p["st"].total_qty * self._cur_price(c, D, hm)
                          for c, p in positions.items())

    def _port_risk(self, positions, D, hm):
        tot = 0.0
        for c, p in positions.items():
            st = p["st"]; px = self._cur_price(c, D, hm); line = st.effective_exit_line()
            if px > line:
                tot += (px - line) * st.total_qty + sell_fees(px * st.total_qty)
        return tot

    def _close_trade(self, tr: Trade):
        pnl = tr.proceeds_net - tr.cash_out
        tr.pnl_net = round(pnl, 2)
        tr.pnl_pct = round(pnl / tr.cash_out * 100, 4) if tr.cash_out else 0.0
        try:
            tr.holding_days = int((pd.Timestamp(tr.exit_date) - pd.Timestamp(tr.entry_date)).days)
        except Exception:
            tr.holding_days = 0

    def _mark_equity(self, D, cash, positions, di):
        mv = sum(p["st"].total_qty * self._cur_price(c, D, "15:00")
                 for c, p in positions.items())
        self.res.daily_equity.append({
            "date": D, "cash": round(cash, 2), "market_value": round(mv, 2),
            "equity": round(cash + mv, 2), "n_pos": len(positions),
            "exposure_pct": round(mv / (cash + mv) * 100, 3) if (cash + mv) > 0 else 0.0})

    def _update_cooldown_close(self, D, cooldown, di):
        cal = self.data["_calendar"]
        for code, cd in cooldown.items():
            if cd["earliest_buy"] is not None or D <= cd["clear_date"]:
                continue
            a = self.data[code]["np"]
            if a["tradestatus"][di] == 0:
                continue
            close = a["close"][di]
            ma60, ma60l = a["ma60"][di], a["ma60_lag5"][di]
            hh, atr, vol = a["hh20"][di], a["atr14"][di], a["volume"][di]
            vmp = a["vol_ma5_prev"][di]
            if np.isnan(close) or np.isnan(ma60) or np.isnan(ma60l):
                continue
            broken = False
            if close <= ma60 or ma60 <= ma60l:
                broken = True
            if not (np.isnan(hh) or np.isnan(atr)) and atr > 0:
                k = (hh - close) / atr
                if not (self.atr_k[0] <= k <= self.atr_k[1]):
                    broken = True
            if not np.isnan(vmp) and vmp > 0 and not np.isnan(vol):
                if vol / vmp >= self.vol_ratio_max:
                    broken = True
            if broken:
                cd["reset_date"] = D
                cd["earliest_buy"] = cal[di + 1] if di + 1 < len(cal) else None

    def _finalize(self, cash, positions):
        for c, p in positions.items():
            st = p["st"]
            px = self._last_px.get(c, st.cost)
            self.res.open_positions.append({
                "stock": c, "name": STOCKS[c][0], "qty": st.total_qty, "cost": st.cost,
                "last_price": round(px, 2),
                "unrealized_pnl": round((px - st.cost) * st.total_qty, 2),
                "unrealized_pct": round((px / st.cost - 1) * 100, 3),
                "peak_h": st.peak_h, "protection_active": st.protection_active,
                "exit_line": st.effective_exit_line(),
                "exit_pending": st.is_exit_pending()})
        self.res.extra["end_cash"] = round(cash, 2)
