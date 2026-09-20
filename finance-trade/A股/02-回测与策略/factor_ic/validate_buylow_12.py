#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""BUY-LOW-v1 三条件 · 在【自选12只】上做事件研究

为什么单独做这版：
  上一版用沪深300（197只大盘股）→ 得出"三条件负 alpha"
  但你的实盘标的是【12只中小盘科技股】→ 标的不同，结论不能直接套用
  12 只无法做截面 IC（样本不足），但【事件研究】可行且更贴合你的实际

方法：
  逐只股票找出三条件同时满足的交易日
  统计触发后 N 日收益，与【同一只股票的全样本平均】对比（超额）
  汇总 12 只的加权结果 + 逐只明细（看是否被少数股票主导）

口径：与 strategies/buy_policy.py 一致
  MA60=60/MA60上行5日, H20=20, ATR14(Wilder), 偏离2.5~4.5, 量比<0.80(全天近似)
⚠️ ③ 用全天量比近似同刻量比（原策略为分钟级同刻量比）

输出：universe/buylow_12stocks.txt
"""
from __future__ import annotations

import os
import csv
import math
import numpy as np

BASE = "/Users/omi/workspace/quant-backtest/results/factor_ic_20260918"
HORIZONS = (1, 3, 5, 10)
MA60_N, MA60_LOOKBACK = 60, 5
H20_N, ATR_N = 20, 14
ATR_LOW, ATR_HIGH = 2.5, 4.5
VOL_RATIO_MAX, VOL_LOOKBACK_DAYS = 0.80, 5

WATCH = {
    "601138": "工业富联", "002156": "通富微电", "600460": "士兰微", "603380": "易德龙",
    "002396": "星网锐捷", "600487": "亨通光电", "600522": "中天科技", "600988": "赤峰黄金",
    "600219": "南山铝业", "000878": "云南铜业", "600760": "中航沈飞", "000938": "紫光股份",
}


def load(code):
    p = os.path.join(BASE, "daily", f"{code}.csv")
    if not os.path.exists(p):
        return None
    rows = list(csv.DictReader(open(p, encoding="utf-8")))
    d = {"date": [r["date"] for r in rows]}
    for k in ("open", "close", "high", "low", "volume"):
        d[k] = np.array([float(r[k]) if r[k] not in ("", "None") else np.nan for r in rows])
    return d


def atr_wilder(high, low, close, n=ATR_N):
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


def analyze(code):
    d = load(code)
    if d is None or len(d["close"]) < 200:
        return None
    close, high, low, vol, op = d["close"], d["high"], d["low"], d["volume"], d["open"]
    T = len(close)

    ma60 = np.full(T, np.nan)
    for i in range(MA60_N - 1, T):
        ma60[i] = np.nanmean(close[i - MA60_N + 1:i + 1])
    ma60_5 = np.full(T, np.nan)
    ma60_5[MA60_LOOKBACK:] = ma60[:-MA60_LOOKBACK]
    h20 = np.full(T, np.nan)
    for i in range(H20_N, T):
        h20[i] = np.nanmax(high[i - H20_N:i])
    atr = atr_wilder(high, low, close)

    # 日线全天量比
    vma = np.full(T, np.nan)
    for i in range(VOL_LOOKBACK_DAYS - 1, T):
        vma[i] = np.nanmean(vol[i - VOL_LOOKBACK_DAYS + 1:i + 1])
    with np.errstate(invalid="ignore", divide="ignore"):
        depth = (h20 - close) / atr
        vratio = vol / vma

    c1 = (close > ma60) & (ma60 > ma60_5) & ~np.isnan(ma60_5)
    c2 = (depth >= ATR_LOW) & (depth <= ATR_HIGH) & (close > ma60)
    c3 = (vratio < VOL_RATIO_MAX)
    sig = c1 & c2 & c3

    # 未来收益（次日开盘 → N日后收盘）
    no = np.full(T, np.nan); no[:-1] = op[1:]
    fwd = {}
    for h in HORIZONS:
        fc = np.full(T, np.nan)
        if h < T: fc[:-h] = close[h:]
        fwd[h] = fc / no - 1

    res = {"code": code, "name": WATCH[code], "T": T, "n_sig": int(np.nansum(sig))}
    for h in HORIZONS:
        m = ~np.isnan(fwd[h])
        base = float(np.nanmean(fwd[h][m])) if m.sum() > 30 else np.nan
        s = sig & m
        if s.sum() >= 3:
            ev = fwd[h][s]
            res[h] = {"n": int(s.sum()), "mean": float(np.mean(ev)), "base": base,
                      "exc": float(np.mean(ev)) - base,
                      "win": float(np.mean(ev > base))}
        else:
            res[h] = {"n": int(s.sum()), "mean": np.nan, "base": base, "exc": np.nan, "win": np.nan}
    # 各条件单独触发率
    res["rates"] = {"c1": float(np.nanmean(c1)), "c2": float(np.nanmean(c2)),
                    "c3": float(np.nanmean(c3)), "all": float(np.nanmean(sig))}
    return res


def main():
    L = []
    L.append("BUY-LOW-v1 三条件 · 自选12只 事件研究")
    L.append("=" * 112)
    L.append("口径与 strategies/buy_policy.py 一致 (MA60=60/上行5日, H20=20, ATR14 Wilder, 偏离2.5~4.5, 量比<0.80)")
    L.append("⚠️ ③ 用日线全天量比近似同刻量比（原策略为分钟级）")
    L.append("")

    rows = []
    for code in WATCH:
        r = analyze(code)
        if r: rows.append(r)
        else: print(f"  [{code}] 数据缺失")

    L.append("【各条件触发率】（占交易日比例）")
    L.append("-" * 112)
    L.append(f"{'股票':<10}{'交易日':>8}{'①趋势':>9}{'②位置':>9}{'③缩量':>9}{'三条件同时':>11}{'触发次数':>9}")
    L.append("-" * 112)
    for r in rows:
        t = r["rates"]
        L.append(f"{r['name']:<10}{r['T']:>8}{t['c1']*100:>8.1f}%{t['c2']*100:>8.1f}%"
                 f"{t['c3']*100:>8.1f}%{t['all']*100:>10.1f}%{r['n_sig']:>9}")

    L.append("")
    L.append("【触发后收益 vs 该股全样本平均】")
    L.append("-" * 112)
    hdr = f"{'股票':<10}"
    for h in HORIZONS:
        hdr += f"{'H'+str(h)+'触发':>11}{'H'+str(h)+'超额':>11}"
    L.append(hdr)
    L.append("-" * 112)
    for r in rows:
        line = f"{r['name']:<10}"
        for h in HORIZONS:
            v = r[h]
            if np.isnan(v["exc"]):
                line += f"{'—':>11}{'—':>11}"
            else:
                line += f"{v['mean']*100:>10.2f}%{v['exc']*100:>+10.2f}%"
        L.append(line)

    # ---- 汇总 ----
    L.append("")
    L.append("【汇总：12只加权（按触发次数加权）】")
    L.append("-" * 112)
    L.append(f"{'未来N日':>8}{'总触发次数':>12}{'触发后平均':>13}{'基准平均':>11}{'超额':>10}{'胜率':>9}{'t值':>9}")
    L.append("-" * 112)
    for h in HORIZONS:
        evs, bases, ns = [], [], []
        for r in rows:
            v = r[h]
            if not np.isnan(v["exc"]) and v["n"] > 0:
                evs.append(v["mean"]); bases.append(v["base"]); ns.append(v["n"])
        if len(evs) < 3:
            L.append(f"{h:>8}{'样本不足':>12}")
            continue
        ns = np.array(ns, dtype=float)
        wmean = float(np.average(evs, weights=ns))
        wbase = float(np.average(bases, weights=ns))
        exc = wmean - wbase
        # 逐股超额的 t 检验（股票层面，n=股票数）
        excs = np.array([e - b for e, b in zip(evs, bases)])
        t = float(excs.mean() / (excs.std(ddof=1) / math.sqrt(len(excs)))) if excs.std(ddof=1) > 0 else float("nan")
        win = float((excs > 0).mean())
        L.append(f"{h:>8}{int(ns.sum()):>12}{wmean*100:>12.3f}%{wbase*100:>10.3f}%{exc*100:>+9.3f}%{win*100:>8.0f}%{t:>9.2f}")

    L.append("")
    L.append("【判读】")
    L.append("-" * 112)
    L.append("· 超额 > 0 且 |t| >= 2 → 三条件在你的标的上有效")
    L.append("· 超额 ≈ 0 → 三条件不构成 alpha（但可能仍是有效的'纪律约束'）")
    L.append("· 超额 < 0 且 |t| >= 2 → 三条件在该样本上为负")
    L.append("⚠️ 12只样本量小，t 检验功效有限；逐只明细比汇总结论更可靠")
    L.append("⚠️ 样本期 2023-09 ~ 2026-09，单一市场环境")

    txt = "\n".join(L)
    print("\n" + txt)
    open(os.path.join(BASE, "universe", "buylow_12stocks.txt"), "w", encoding="utf-8").write(txt)
    print(f"\n✅ {BASE}/universe/buylow_12stocks.txt")


if __name__ == "__main__":
    main()
