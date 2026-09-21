#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""复盘：2026-09-01 ~ 09-21 实盘操作 vs BUY-LOW-v1 三条件

目的：回答「这段时间的操作，如果严格按 BUY-LOW-v1 三条件，会有什么不同？」
方法：
  对 12 只自选股，逐交易日回放 BUY-LOW-v1 三条件（用当时可见的数据，严格 .shift 防未来函数）
  ① 价 > MA60 且 MA60 > 5日前 MA60
  ② (H20 − 价)/ATR14(Wilder) ∈ [2.5, 4.5]
  ③ 当日量 / 前5日均量 < 0.80   （日线近似，线上为同刻量比）
  输出：9/1~9/21 期间每天满足三条件的股票 → 与实盘操作对照

⚠️ ③ 用日线全天量比近似；时段/同刻量比无法回放；结论留余量
"""
from __future__ import annotations
import os, csv, json
import numpy as np

BASE = "/Users/omi/workspace/quant-backtest/results/factor_ic_20260918"
START, END = "2026-09-01", "2026-09-21"
MA60_N, MA_LB = 60, 5
H20_N, ATR_N = 20, 14
ATR_LOW, ATR_HIGH = 2.5, 4.5
VOL_RATIO_MAX, VOL_LB = 0.80, 5

WATCH = {
    "601138": "工业富联", "002156": "通富微电", "600460": "士兰微", "603380": "易德龙",
    "002396": "星网锐捷", "600487": "亨通光电", "600522": "中天科技", "600988": "赤峰黄金",
    "600219": "南山铝业", "000878": "云南铜业", "600760": "中航沈飞", "000938": "紫光股份",
}


def atr_wilder(high, low, close, n=ATR_N):
    T = len(close); tr = np.full(T, np.nan); tr[0] = high[0] - low[0]
    for i in range(1, T):
        tr[i] = max(high[i]-low[i], abs(high[i]-close[i-1]), abs(low[i]-close[i-1]))
    atr = np.full(T, np.nan)
    if T < n: return atr
    a = float(np.nanmean(tr[:n])); atr[n-1] = a
    for i in range(n, T):
        a = (a*(n-1)+tr[i])/n; atr[i] = a
    return atr


def analyze(code):
    p = f"{BASE}/daily/{code}.csv"
    if not os.path.exists(p): return None
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    dt = [r["date"] for r in rows]
    close = np.array([float(r["close"]) for r in rows])
    high = np.array([float(r["high"]) for r in rows])
    low = np.array([float(r["low"]) for r in rows])
    vol = np.array([float(r["volume"]) for r in rows])
    T = len(close)
    ma60 = np.full(T, np.nan)
    for i in range(MA60_N-1, T): ma60[i] = np.nanmean(close[i-MA60_N+1:i+1])
    ma60_5 = np.full(T, np.nan); ma60_5[MA_LB:] = ma60[:-MA_LB]
    h20 = np.full(T, np.nan)
    for i in range(H20_N, T): h20[i] = np.nanmax(high[i-H20_N:i])   # shift(1) 防未来函数
    atr = atr_wilder(high, low, close)
    vma = np.full(T, np.nan)
    for i in range(VOL_LB-1, T): vma[i] = np.nanmean(vol[i-VOL_LB+1:i+1])
    with np.errstate(invalid="ignore", divide="ignore"):
        depth = (h20-close)/atr
        vr = vol/vma
    out = {}
    for i, d in enumerate(dt):
        if not (START <= d <= END): continue
        c1 = (not np.isnan(ma60_5[i])) and close[i] > ma60[i] and ma60[i] > ma60_5[i]
        c2 = (not np.isnan(depth[i])) and ATR_LOW <= depth[i] <= ATR_HIGH
        c3 = (not np.isnan(vr[i])) and vr[i] < VOL_RATIO_MAX
        out[d] = dict(close=close[i], c1=bool(c1), c2=bool(c2), c3=bool(c3),
                      all=bool(c1 and c2 and c3), depth=float(depth[i]) if not np.isnan(depth[i]) else None,
                      vr=float(vr[i]) if not np.isnan(vr[i]) else None,
                      ma60=float(ma60[i]) if not np.isnan(ma60[i]) else None)
    return out


def main():
    res = {c: analyze(c) for c in WATCH}
    dates = sorted({d for r in res.values() if r for d in r})
    L = []
    L.append("复盘：2026-09-01 ~ 2026-09-21 · 实盘操作 vs BUY-LOW-v1 三条件回放")
    L.append("=" * 118)
    L.append("口径：①价>MA60且MA60上行5日 ②(H20−价)/ATR14∈[2.5,4.5] ③日线量比<0.80")
    L.append("⚠️ ③为日线全天量比近似（线上为同刻量比）；H20 用 shift(1) 防未来函数")
    L.append("")
    L.append("【逐日三条件全满足名单】")
    L.append("-" * 118)
    for d in dates:
        hits = [WATCH[c] for c in WATCH if res[c] and d in res[c] and res[c][d]["all"]]
        near = [f"{WATCH[c]}(差{''.join([k for k,v in [('①',res[c][d]['c1']),('②',res[c][d]['c2']),('③',res[c][d]['c3'])] if not v])})"
                for c in WATCH if res[c] and d in res[c] and not res[c][d]["all"] and sum([res[c][d]['c1'],res[c][d]['c2'],res[c][d]['c3']])==2]
        L.append(f"  {d}  全满足: {'、'.join(hits) if hits else '（无）'}")
        if near: L.append(f"             差一项: {'、'.join(near)}")
    L.append("")
    L.append("【关键日期逐股明细】（实盘有操作的日子 + 三条件全满足的日子）")
    L.append("-" * 118)
    KEY = ["2026-09-01","2026-09-03","2026-09-04","2026-09-08","2026-09-10","2026-09-11",
           "2026-09-14","2026-09-16","2026-09-17","2026-09-21"]
    for d in KEY:
        if d not in dates: continue
        L.append(f"  ── {d} ──")
        for c, nm in WATCH.items():
            v = res[c].get(d) if res[c] else None
            if not v: continue
            mark = "✅全满足" if v["all"] else ("差" + "".join([k for k, ok in [("①",v['c1']),("②",v['c2']),("③",v['c3'])] if not ok]))
            L.append(f"     {nm:<8}{v['close']:>8.2f}  MA60={v['ma60'] if v['ma60'] else 0:>7.2f}  "
                     f"②值={v['depth'] if v['depth'] else 0:>5.2f}  量比={v['vr'] if v['vr'] else 0:>5.2f}   {mark}")
        L.append("")
    txt = "\n".join(L)
    print(txt)
    out = f"{BASE}/universe/replay_202609.txt"
    open(out, "w", encoding="utf-8").write(txt)
    print(f"\n✅ {out}")


if __name__ == "__main__":
    main()
