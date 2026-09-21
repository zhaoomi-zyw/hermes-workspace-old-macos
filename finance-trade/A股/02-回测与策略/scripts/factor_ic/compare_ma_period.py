#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""条件① 均线周期对比：MA20 vs MA30 vs MA60

回答 Omi 的问题：「为什么定的是60日均线而不是20日？」

方法（复用 validate_buylow.py / validate_buylow_12.py 已有框架，不引入新东西）：
  变量 —— 条件① 的均线周期 N ∈ {20, 30, 60}（其余条件形式完全不变）
    ① 价 > MA_N 且 MA_N > 5日前 MA_N
    ② (H20 − 价)/ATR14(Wilder) ∈ [2.5, 4.5]
    ③ 当日量 / 前5日均量 < 0.80
  样本 —— A. 沪深300 可买成分（280只）  B. 自选12只
  指标 —— 触发后 H1/H3/H5/H10/H20 超额收益（相对全样本同期均值）+ t值 + 胜率

重点关注：MA20 是否只是「更多信号但更差」→ 若如此，MA60 的保守就有实证依据。

⚠️ 与 line 上的差异（沿用既有脚本的同样近似，不新增）：
   · ③ 用日线全天量比近似「同刻量比」（缺分钟数据）
   · 时段限制（09:45–11:30）对日线回测不适用，用收盘口径
   · 基准 = 全样本同期等权平均（不是指数）

输出：results/factor_ic_20260918/universe/ma_period_comparison.txt
"""
from __future__ import annotations

import os
import csv
import math
import json
import numpy as np

BASE = "/Users/omi/workspace/quant-backtest/results/factor_ic_20260918"
UNI = f"{BASE}/universe"
HORIZONS = (1, 3, 5, 10, 20)
PERIODS = (20, 30, 60)
MA_LOOKBACK = 5
H20_N, ATR_N = 20, 14
ATR_LOW, ATR_HIGH = 2.5, 4.5
VOL_RATIO_MAX, VOL_LOOKBACK_DAYS = 0.80, 5
MIN_STOCKS_PER_DAY = 30

WATCH = {
    "601138": "工业富联", "002156": "通富微电", "600460": "士兰微", "603380": "易德龙",
    "002396": "星网锐捷", "600487": "亨通光电", "600522": "中天科技", "600988": "赤峰黄金",
    "600219": "南山铝业", "000878": "云南铜业", "600760": "中航沈飞", "000938": "紫光股份",
}


def atr_wilder(high, low, close, n=ATR_N):
    """Wilder ATR14。支持 1D（单股）与 2D（面板 T×N，逐列递推）"""
    high = np.asarray(high, dtype=float); low = np.asarray(low, dtype=float)
    close = np.asarray(close, dtype=float)
    if close.ndim == 1:
        T = len(close)
        tr = np.full(T, np.nan)
        tr[0] = high[0] - low[0]
        for i in range(1, T):
            tr[i] = max(high[i] - low[i], abs(high[i] - close[i - 1]), abs(low[i] - close[i - 1]))
        atr = np.full(T, np.nan)
        if T < n:
            return atr
        a = float(np.nanmean(tr[:n]))
        atr[n - 1] = a
        for i in range(n, T):
            a = (a * (n - 1) + tr[i]) / n
            atr[i] = a
        return atr
    # ---- 2D 面板 ----
    with np.errstate(invalid="ignore"):
        prev = np.full_like(close, np.nan); prev[1:] = close[:-1]
        tr = np.maximum.reduce([high - low, np.abs(high - prev), np.abs(low - prev)])
    tr[0] = high[0] - low[0]
    atr = np.full_like(close, np.nan)
    for j in range(close.shape[1]):
        col = tr[:, j]
        idx = np.where(~np.isnan(col))[0]
        if len(idx) < n:
            continue
        k0 = idx[0]
        a = float(np.mean(col[idx[:n]]))
        atr[idx[n - 1], j] = a
        for t in idx[n:]:
            a = (a * (n - 1) + col[t]) / n
            atr[t, j] = a
    return atr


def signals(close, high, low, vol, op, N):
    """按均线周期 N 生成三条件布尔信号 + 未来收益（日线近似口径）
    支持 1D（单股）与 2D（面板 T×N）"""
    close = np.asarray(close, dtype=float)
    T = close.shape[0]
    ma = np.full_like(close, np.nan)
    for i in range(N - 1, T):
        ma[i] = np.nanmean(close[i - N + 1:i + 1], axis=0)
    ma_5 = np.full_like(close, np.nan)
    ma_5[MA_LOOKBACK:] = ma[:-MA_LOOKBACK]
    h20 = np.full_like(close, np.nan)
    for i in range(H20_N, T):
        h20[i] = np.nanmax(high[i - H20_N:i], axis=0)
    atr = atr_wilder(high, low, close)
    vma = np.full_like(close, np.nan)
    for i in range(VOL_LOOKBACK_DAYS - 1, T):
        vma[i] = np.nanmean(vol[i - VOL_LOOKBACK_DAYS + 1:i + 1], axis=0)
    with np.errstate(invalid="ignore", divide="ignore"):
        depth = (h20 - close) / atr
        vratio = vol / vma
    c1 = (close > ma) & (ma > ma_5) & ~np.isnan(ma_5)
    c2 = (depth >= ATR_LOW) & (depth <= ATR_HIGH)
    c3 = (vratio < VOL_RATIO_MAX)
    sig = c1 & c2 & c3
    no = np.full_like(close, np.nan); no[:-1] = op[1:]
    fwd = {}
    for h in HORIZONS:
        fc = np.full_like(close, np.nan)
        if h < T: fc[:-h] = close[h:]
        fwd[h] = fc / no - 1
    return sig, fwd, c1, c2, c3


def load_panel(ddir):
    codes = [f[:-4] for f in sorted(os.listdir(ddir)) if f.endswith(".csv")]
    all_dates, raw = set(), {}
    for c in codes:
        rows = list(csv.DictReader(open(os.path.join(ddir, f"{c}.csv"), encoding="utf-8")))
        raw[c] = rows; all_dates |= {r["date"] for r in rows}
    dates = sorted(all_dates); di = {d: i for i, d in enumerate(dates)}
    T, N = len(dates), len(codes)
    P = {k: np.full((T, N), np.nan) for k in ("open", "close", "high", "low", "volume")}
    for j, c in enumerate(codes):
        for r in raw[c]:
            i = di[r["date"]]
            for k in P:
                try: P[k][i, j] = float(r[k])
                except (TypeError, ValueError): pass
    return dates, codes, P


def event_study(dates, codes, P, label, L, min_n=MIN_STOCKS_PER_DAY):
    """对所有股票做：三个均线周期 × 5个持有期 的事件研究（面板合并口径）"""
    close, high, low, vol, op = P["close"], P["high"], P["low"], P["volume"], P["open"]
    T, N = close.shape
    out = {}
    for N_ in PERIODS:
        sig, fwd, c1, c2, c3 = signals(close, high, low, vol, op, N_)
        rate = dict(c1=float(np.nanmean(c1)), c2=float(np.nanmean(c2)),
                    c3=float(np.nanmean(c3)), all=float(np.nanmean(sig)))
        # 每日：触发组均值 vs 全样本均值 → 超额序列
        per_h = {}
        for h in HORIZONS:
            ev, base_seq = [], []
            for t in range(T):
                y = fwd[h][t, :]
                m = ~np.isnan(y)
                if m.sum() < min_n:
                    continue
                base_seq.append(float(np.nanmean(y[m])))
                s = sig[t, :] & m
                if s.sum() >= 1:
                    ev.append(float(np.nanmean(y[s])))
            if len(ev) < 10:
                per_h[h] = None; continue
            e = np.array(ev); b = np.array(base_seq)
            n = min(len(e), len(b))
            e, b = e[:n], b[:n]
            exc = e - b
            sd = exc.std(ddof=1) if len(exc) > 1 else float("nan")
            t_ = float(exc.mean() / (sd / math.sqrt(len(exc)))) if sd and sd > 0 else float("nan")
            per_h[h] = dict(n_days=len(e), n_trig=int(np.nansum(sig)),
                            mean=float(e.mean()), base=float(b.mean()),
                            exc=float(exc.mean()), win=float((e > b).mean()), t=t_)
        out[N_] = dict(rate=rate, h=per_h)
    return out


def fmt_block(L, title, res, periods=PERIODS):
    L.append("")
    L.append(f"【{title}】")
    L.append("-" * 120)
    L.append(f"{'均线周期':<10}{'①触发率':>9}{'②触发率':>9}{'③触发率':>9}{'三条件触发率':>13}{'总触发次数(股·日)':>18}")
    L.append("-" * 120)
    for N_ in periods:
        r = res[N_]["rate"]
        cnt = sum(v["n_trig"] for v in res[N_]["h"].values() if v) // len(HORIZONS) if res[N_]["h"] else 0
        L.append(f"MA{N_:<8}{r['c1']*100:>8.1f}%{r['c2']*100:>8.1f}%{r['c3']*100:>8.1f}%"
                 f"{r['all']*100:>12.2f}%{cnt:>18}")
    L.append("")
    for h in HORIZONS:
        L.append(f"  ── 持有 H{h} ──")
        L.append(f"  {'均线周期':<10}{'触发日数':>10}{'触发组均值':>12}{'基准均值':>11}{'超额':>10}{'胜率':>9}{'t值':>9}   判读")
        for N_ in periods:
            v = res[N_]["h"].get(h)
            if not v:
                L.append(f"  MA{N_:<8}{'样本不足':>10}"); continue
            tag = ("✅ 显著正" if (v["exc"] > 0 and abs(v["t"]) >= 2) else
                   "❌ 显著负" if (v["exc"] < 0 and abs(v["t"]) >= 2) else "○ 不显著")
            L.append(f"  MA{N_:<8}{v['n_days']:>10}{v['mean']*100:>11.3f}%{v['base']*100:>10.3f}%"
                     f"{v['exc']*100:>+9.3f}%{v['win']*100:>8.0f}%{v['t']:>9.2f}   {tag}")
        L.append("")


def main():
    L = []
    L.append("条件① 均线周期对比：MA20 / MA30 / MA60")
    L.append("=" * 120)
    L.append("问题：为什么是 MA60 而不是 MA20？（此前从未做过周期敏感性验证）")
    L.append("方法：仅改变条件①的均线周期，其余条件形式完全不变")
    L.append("  ① 价 > MA_N 且 MA_N > 5日前 MA_N")
    L.append("  ② (H20 − 价)/ATR14(Wilder) ∈ [2.5, 4.5]")
    L.append("  ③ 当日量 / 前5日均量 < 0.80")
    L.append("⚠️ ③ 用日线全天量比近似同刻量比；基准 = 全样本同期等权平均；收盘口径")
    L.append("")

    # ---------- A. 沪深300 可买成分 ----------
    dates, codes, P = load_panel(f"{UNI}/daily")
    L.append(f"【样本A】沪深300 可买成分：{len(codes)} 只 × {len(dates)} 交易日 ({dates[0]} ~ {dates[-1]})")
    resA = event_study(dates, codes, P, "沪深300", L)
    fmt_block(L, "样本A · 沪深300（280只）", resA)

    # ---------- B. 自选12只 ----------
    d12 = f"{BASE}/daily"
    codes12 = [c for c in WATCH if os.path.exists(f"{d12}/{c}.csv")]
    dates2, codes2, P2 = load_panel(d12)
    codes2 = [c for c in codes2 if c in WATCH]
    sel = [codes2.index(c) for c in codes2]
    P2s = {k: v[:, sel] for k, v in P2.items()}
    L.append(f"【样本B】自选12只：{len(codes2)} 只 × {len(dates2)} 交易日 ({dates2[0]} ~ {dates2[-1]})")
    resB = event_study(dates2, codes2, P2s, "12只", L, min_n=6)
    fmt_block(L, "样本B · 自选12只", resB)

    # ---------- 结论 ----------
    L.append("")
    L.append("=" * 120)
    L.append("【结论判读】")
    L.append("-" * 120)
    L.append("核心问题：MA20 是不是「更多信号但更差」？")
    L.append("")
    for nm, res in (("沪深300(280只)", resA), ("自选12只", resB)):
        L.append(f"  ── {nm} ──")
        for h in (5, 10, 20):
            row = []
            for N_ in PERIODS:
                v = res[N_]["h"].get(h)
                row.append(f"MA{N_}: {v['exc']*100:+.3f}%(t={v['t']:+.2f},触发{v['n_trig']}次)" if v else f"MA{N_}: —")
            L.append(f"    H{h:<3} " + "  |  ".join(row))
        L.append("")
    L.append("判读标准：|t| ≥ 2 统计显著；超额 > 0 才有正向价值")
    L.append("⚠️ 单一市场环境(2023-09~2026-09)；量比为日线近似；基准为等权平均而非指数")
    L.append("⚠️ 即便都显著，也只是统计相关性，不等于实盘可得收益（需扣双边成本 0.1~0.2%）")

    txt = "\n".join(L)
    print(txt)
    outp = f"{UNI}/ma_period_comparison.txt"
    open(outp, "w", encoding="utf-8").write(txt)
    print(f"\n✅ {outp}")


if __name__ == "__main__":
    main()
