#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BUY-LOW-v1 三条件 · 统计有效性检验

回答一个之前从没验证过的问题：
  「你每天在跑的那套买入规则，到底有没有统计依据？」

方法（布尔信号不能用 IC，故分两条路）：
  A. 三个条件【连续化】后做截面 IC + 行业/规模中性化
     · ① 趋势强度 = close/MA60 - 1
     · ② 回调深度 = (H20 - close)/ATR14     （越大 = 离20日高点越远）
     · ③ 量能      = 当日量 / 前5日均量      （越小 = 越缩量）
  B. 三条件【同时满足】的布尔信号 → 事件研究
     · 触发后 N 日收益 vs 全样本同期均值（超额）
     · 胜率、t 检验

口径与 strategies/buy_policy.py 严格一致：
  MA60_N=60, MA60_LOOKBACK=5, H20_N=20, ATR_N=14(Wilder), ATR低=2.5, ATR高=4.5,
  VOL_RATIO_MAX=0.8, VOL_LOOKBACK_DAYS=5
⚠️ ③ 用日线全天量比近似（原策略为同刻量比，需分钟数据）→ 该条为近似，结论留余量
⚠️ 时段限制（09:45-11:30）对日线回测不适用，此处用收盘口径

输出：universe/buylow_validation.txt
"""
from __future__ import annotations

import os
import csv
import json
import math
import numpy as np
from datetime import date, timedelta

BASE = "/Users/omi/workspace/quant-backtest/results/factor_ic_20260918/universe"
HORIZONS = (1, 3, 5, 10)
MIN_STOCKS_PER_DAY = 30

# ---- 与 buy_policy 一致的常量 ----
MA60_N, MA60_LOOKBACK = 60, 5
H20_N, ATR_N = 20, 14
ATR_LOW, ATR_HIGH = 2.5, 4.5
VOL_RATIO_MAX, VOL_LOOKBACK_DAYS = 0.80, 5


def _rankdata(a):
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    r = np.empty(len(a), dtype=float)
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
            j += 1
        r[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    return r


def spearman(a, b):
    a = np.asarray(a, float).flatten(); b = np.asarray(b, float).flatten()
    m = ~(np.isnan(a) | np.isnan(b)); a, b = a[m], b[m]
    if len(a) < MIN_STOCKS_PER_DAY: return None, 0
    ra, rb = _rankdata(a), _rankdata(b)
    ma, mb = ra.mean(), rb.mean()
    va = math.sqrt(float(np.sum((ra - ma) ** 2) * np.sum((rb - mb) ** 2)))
    return ((float(np.sum((ra - ma) * (rb - mb))) / va) if va > 0 else 0.0), len(a)


def load_panel():
    ddir = os.path.join(BASE, "daily")
    ind = json.load(open(os.path.join(BASE, "industry_map.json"), encoding="utf-8"))
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
    grp = np.array([ind.get(c, {}).get("industry", "UNKNOWN") for c in codes])
    return dates, codes, P, grp


def roll_mean(a, w):
    o = np.full_like(a, np.nan)
    for i in range(w - 1, a.shape[0]):
        o[i] = np.nanmean(a[i - w + 1:i + 1], axis=0)
    return o


def atr14_wilder(high, low, close):
    """Wilder ATR14，逐列（股票）递推"""
    T, N = close.shape
    tr = np.full_like(close, np.nan)
    tr[0] = high[0] - low[0]
    prev = close[:-1]
    tr[1:] = np.maximum.reduce([high[1:] - low[1:], np.abs(high[1:] - prev), np.abs(low[1:] - prev)])
    atr = np.full_like(close, np.nan)
    for j in range(N):
        col = tr[:, j]
        idx = np.where(~np.isnan(col))[0]
        if len(idx) < ATR_N: continue
        k0 = idx[0]
        # 初始 = 前14个TR简单平均
        vals = col[idx[:ATR_N]]
        a = float(np.mean(vals))
        atr[idx[ATR_N - 1], j] = a
        for t in idx[ATR_N:]:
            a = (a * (ATR_N - 1) + col[t]) / ATR_N
            atr[t, j] = a
    return atr


def main():
    dates, codes, P, grp = load_panel()
    T, N = P["close"].shape
    print(f"面板: {N} 只 × {T} 交易日 ({dates[0]} ~ {dates[-1]})")

    close, high, low, vol = P["close"], P["high"], P["low"], P["volume"]
    # MA60
    ma60 = np.full_like(close, np.nan)
    for i in range(MA60_N - 1, T):
        ma60[i] = np.nanmean(close[i - MA60_N + 1:i + 1], axis=0)
    ma60_5 = np.full_like(ma60, np.nan)
    ma60_5[MA60_LOOKBACK:] = ma60[:-MA60_LOOKBACK]
    # H20（前20日最高，shift 防未来函数）
    h20 = np.full_like(close, np.nan)
    for i in range(H20_N, T):
        h20[i] = np.nanmax(high[i - H20_N:i], axis=0)
    atr = atr14_wilder(high, low, close)
    vma = roll_mean(vol, VOL_LOOKBACK_DAYS)

    with np.errstate(invalid="ignore", divide="ignore"):
        trend = close / ma60 - 1.0                       # ① 趋势强度
        depth = (h20 - close) / atr                      # ② 离20日高点距离（ATR倍数）
        vratio = vol / vma                               # ③ 量能（全天量比）

    # 布尔三条件
    c1 = (close > ma60) & (ma60 > ma60_5) & ~np.isnan(ma60_5)
    c2 = (depth >= ATR_LOW) & (depth <= ATR_HIGH) & (close > ma60)
    c3 = (vratio < VOL_RATIO_MAX)
    sig = (c1 & c2 & c3)

    # 未来收益
    no = np.full_like(P["open"], np.nan); no[:-1] = P["open"][1:]
    fwd = {}
    for h in HORIZONS:
        fc = np.full_like(close, np.nan)
        if h < T: fc[:-h] = close[h:]
        fwd[h] = fc / no - 1

    def neutralize(x, size):
        y = x - np.nanmean(x)
        out = np.full_like(y, np.nan)
        for g in set(grp):
            m = grp == g; seg = y[m]
            out[m] = seg - np.nanmean(seg) if np.sum(~np.isnan(seg)) >= 3 else seg
        if size is not None:
            m = ~(np.isnan(out) | np.isnan(size))
            if m.sum() >= MIN_STOCKS_PER_DAY:
                xv, yv = size[m], out[m]
                xv2 = xv - xv.mean(); den = float(np.sum(xv2 * xv2))
                if den > 0:
                    beta = float(np.sum(xv2 * (yv - yv.mean()))) / den
                    out[m] = yv - (yv.mean() + beta * xv2)
        return out

    size = np.log(vol * close)
    L = []
    L.append("BUY-LOW-v1 三条件 · 统计有效性检验")
    L.append("=" * 118)
    L.append(f"样本: {N} 只 × {T} 交易日 ({dates[0]} ~ {dates[-1]})")
    L.append("口径: 与 strategies/buy_policy.py 一致 (MA60=60/上行5日, H20=20, ATR14 Wilder, 偏离2.5~4.5, 量比<0.80)")
    L.append("⚠️ ③ 用日线全天量比近似同刻量比（缺分钟数据）")
    L.append("")

    # ---------- A. 连续化因子截面 IC ----------
    L.append("【A】三条件连续化后的截面 IC（行业+规模中性化）")
    L.append("-" * 118)
    L.append(f"{'因子':<24}{'H':>4}{'IC均值':>10}{'IC原始':>10}{'IR':>8}{'t值':>9}{'IC>0':>8}{'天数':>7}")
    L.append("-" * 118)
    cont = {"①趋势强度 close/MA60-1": trend,
            "②回调深度 (H20-P)/ATR": depth,
            "③量能 当日量/5日均量": vratio}
    cont_res = {}
    for nm, M in cont.items():
        for h in HORIZONS:
            ics, raws = [], []
            for t in range(T):
                x, y = M[t, :], fwd[h][t, :]
                if np.sum(~np.isnan(x) & ~np.isnan(y)) < MIN_STOCKS_PER_DAY: continue
                r0, _ = spearman(x, y)
                if r0 is not None: raws.append(r0)
                xn = neutralize(x, size[t, :])
                r1, _ = spearman(xn, y)
                if r1 is not None: ics.append(r1)
            if len(ics) < 20:
                L.append(f"{nm:<24}{h:>4}{'—':>10}{'—':>10}{'—':>8}{'—':>9}{'—':>8}{len(ics):>7}")
                continue
            a = np.array(ics); raw = float(np.mean(raws)) if raws else float("nan")
            mic, sd = float(a.mean()), float(a.std())
            ir = mic / sd if sd > 0 else float("nan")
            ts = mic / (sd / math.sqrt(len(a))) if sd > 0 else float("nan")
            cont_res[(nm, h)] = (mic, ts, float((a > 0).mean()))
            L.append(f"{nm:<24}{h:>4}{mic:>+10.4f}{raw:>+10.4f}{ir:>8.2f}{ts:>9.2f}{float((a>0).mean())*100:>7.0f}%{len(a):>7}")

    # ---------- B. 布尔信号事件研究 ----------
    L.append("")
    L.append("【B】三条件同时满足（布尔信号）的事件研究")
    L.append("-" * 118)
    L.append(f"{'未来N日':>8}{'触发次数':>10}{'触发日均收益':>14}{'全样本日均收益':>16}{'超额':>10}{'胜率':>8}{'t值':>9}")
    L.append("-" * 118)
    for h in HORIZONS:
        ev, allr = [], []
        for t in range(T):
            y = fwd[h][t, :]
            m = ~np.isnan(y)
            if m.sum() < MIN_STOCKS_PER_DAY: continue
            allr.append(np.nanmean(y[m]))
            s = sig[t, :] & m
            if s.sum() >= 1:
                ev.append(np.nanmean(y[s]))
        if len(ev) < 10:
            L.append(f"{h:>8}{len(ev):>10}{'样本不足':>14}")
            continue
        e = np.array(ev); base = float(np.mean(allr))
        exc = float(e.mean()) - base
        win = float((e > base).mean())
        ts = (float(e.mean()) - base) / (float(e.std()) / math.sqrt(len(e))) if e.std() > 0 else float("nan")
        L.append(f"{h:>8}{len(ev):>10}{e.mean()*100:>13.3f}%{base*100:>15.3f}%{exc*100:>+9.3f}%{win*100:>7.0f}%{ts:>9.2f}")

    # ---------- 结论 ----------
    L.append("")
    L.append("【结论判读】")
    L.append("-" * 118)
    for (nm, h), (mic, ts, wr) in sorted(cont_res.items(), key=lambda x: -abs(x[1][1] or 0)):
        if h != 5: continue
        tag = "✅ 显著" if abs(ts) >= 2 else ("○ 弱" if abs(ts) >= 1 else "❌ 不显著")
        L.append(f"  {nm:<26} H5: IC={mic:+.4f} t={ts:+.2f} IC>0占比={wr*100:.0f}%  {tag}")
    L.append("")
    L.append("判断标准: |t|>=2 统计显著；|IC|>=0.03 有实际信息量")

    txt = "\n".join(L)
    print("\n" + txt)
    open(os.path.join(BASE, "buylow_validation.txt"), "w", encoding="utf-8").write(txt)
    print(f"\n✅ {BASE}/buylow_validation.txt")


if __name__ == "__main__":
    main()
