#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证「第⑤条 日内位置约束」是否能提升四条件低吸策略
====================================================
背景 (2026-09-14):
  星网锐捷 9/26 DSA 60 C、距MA5 -4.46% (不达标) → 10:03 涨到 35.83 后
  DSA 71 B、距MA5 +0.5% (达标4/4)。37分钟涨5.5%把条件"涨"成了满足,
  实际买在日内97%位置 (距当日最高仅0.28%)。
  根因: 四条件全是日线级指标+当日实时价参与计算, 无法区分"回踩到位"与"暴涨到位"。

代理指标 (日K可算, 对应实盘"买入时的日内位置"):
  intraday_pos = (close - low) / (high - low)     # 0=收在最低, 1=收在最高
  day_pct      = close / prev_close - 1           # 当日涨幅

验证设计:
  1. 历史扫描全部四条件信号 (现有四条件, 不加⑤)
  2. 对每个信号记录 intraday_pos / day_pct
  3. 按 intraday_pos 分档统计后续 N 日收益
  4. 结论: 高 pos 档若显著劣于低 pos 档 → ⑤条有价值
"""
import os, csv, glob, statistics

DATA_DIR = "/Users/omi/workspace/quant-backtest/data"
HOLD_DAYS = [5, 10, 20]


def sma(vals, n):
    if len(vals) < n:
        return None
    return sum(vals[-n:]) / n


def dsa_score(cl, hi, lo, vo, i):
    """DSA v1 评分 (与 lowbuy-watch.py 保持一致), 索引 i 为当日"""
    if i < 60:
        return None
    c = cl[i]
    ma5, ma10, ma20, ma60 = (sma(cl[:i + 1], n) for n in (5, 10, 20, 60))
    if None in (ma5, ma10, ma20, ma60):
        return None

    score = 0
    # ① 均线结构 (65分)
    if c > ma5:
        score += 15
    if ma5 > ma10:
        score += 15
    if ma10 > ma20:
        score += 15
    if ma20 > ma60:
        score += 10
    if c > ma60:
        score += 10
    # ② 位置 (10分): 20日区间位置 (偏低更优)
    hi20, lo20 = max(hi[i - 19:i + 1]), min(lo[i - 19:i + 1])
    if hi20 > lo20:
        pos20 = (c - lo20) / (hi20 - lo20)
        score += 10 if pos20 <= 0.5 else 5
    # ③ 量能 (10分): 缩量加分
    if i >= 20:
        v5 = sma(vo[:i + 1], 5)
        v20 = sma(vo[:i + 1], 20)
        if v5 and v20 and v5 < v20:
            score += 10
    # ④ 趋势/动量 (15分)
    if i >= 5 and c > cl[i - 5]:
        score += 15
    elif i >= 5:
        score += 5
    return score


def load_csv(path):
    rows = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "date": r["date"],
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r["volume"]),
                })
            except (KeyError, ValueError):
                continue
    return rows


def scan(files):
    signals = []
    for path in files:
        name = os.path.basename(path).rsplit(".", 1)[0]
        rows = load_csv(path)
        if len(rows) < 120:
            continue
        cl = [r["close"] for r in rows]
        hi = [r["high"] for r in rows]
        lo = [r["low"] for r in rows]
        vo = [r["volume"] for r in rows]
        op = [r["open"] for r in rows]

        for i in range(60, len(rows) - max(HOLD_DAYS) - 1):
            c = cl[i]
            ma5, ma10, ma60 = sma(cl[:i + 1], 5), sma(cl[:i + 1], 10), sma(cl[:i + 1], 60)
            if None in (ma5, ma10, ma60):
                continue
            # 四条件
            hi10 = max(hi[i - 9:i + 1])
            dd = (hi10 - c) / hi10 * 100
            d5 = abs(c / ma5 - 1) * 100
            d10 = abs(c / ma10 - 1) * 100
            dsa = dsa_score(cl, hi, lo, vo, i)
            if dsa is None:
                continue
            c1 = dd >= 5.0
            c2 = c > ma60
            c3 = dsa >= 65
            c4 = (d5 <= 2.0 or d10 <= 2.0)
            if not (c1 and c2 and c3 and c4):
                continue
            # 日内位置 / 当日涨幅
            rng = hi[i] - lo[i]
            pos = (c - lo[i]) / rng if rng > 0 else 0.5
            day_pct = (c / cl[i - 1] - 1) * 100 if i > 0 else 0.0
            # 后续收益
            rets = {}
            for h in HOLD_DAYS:
                j = i + h
                if j < len(cl):
                    rets[h] = (cl[j] / c - 1) * 100
            signals.append({
                "name": name, "date": rows[i]["date"], "close": c,
                "dsa": dsa, "dd": dd, "pos": pos, "day_pct": day_pct,
                "rets": rets,
            })
    return signals


def describe(label, sigs):
    if not sigs:
        print(f"{label}: 无样本")
        return
    print(f"\n{label}  (n={len(sigs)})")
    for h in HOLD_DAYS:
        v = [s["rets"][h] for s in sigs if h in s["rets"]]
        if not v:
            continue
        wins = sum(1 for x in v if x > 0)
        print(f"   {h:>2}日: 平均 {statistics.mean(v):+6.2f}%  "
              f"中位 {statistics.median(v):+6.2f}%  胜率 {wins/len(v)*100:4.1f}%")


def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    if not files:
        print("未找到数据文件:", DATA_DIR)
        return
    print(f"数据文件 {len(files)} 个: {[os.path.basename(f) for f in files]}")
    sigs = scan(files)
    print(f"\n四条件信号总数: {len(sigs)}")
    if not sigs:
        return

    describe("【基准】全部四条件信号", sigs)

    # 按日内位置分档
    print("\n" + "=" * 62)
    print("按【日内位置 (close-low)/(high-low)】分档")
    print("=" * 62)
    buckets = [("低位 0.0-0.3 (真低吸)", 0.0, 0.3),
               ("中位 0.3-0.7", 0.3, 0.7),
               ("高位 0.7-0.9", 0.7, 0.9),
               ("极高 0.9-1.0 (≈你这次97%)", 0.9, 1.01)]
    for label, a, b in buckets:
        sel = [s for s in sigs if a <= s["pos"] < b]
        describe(f"{label}", sel)

    # 按当日涨幅分档
    print("\n" + "=" * 62)
    print("按【当日涨幅】分档")
    print("=" * 62)
    for label, a, b in [("下跌/平 ≤0%", -99, 0.01), ("小涨 0-2%", 0.01, 2), ("中涨 2-5%", 2, 5), ("大涨 >5%", 5, 99)]:
        sel = [s for s in sigs if a <= s["day_pct"] < b]
        describe(label, sel)

    # 组合过滤: 加⑤条 (pos<=0.7 且 day_pct<=2%) vs 基准
    print("\n" + "=" * 62)
    print("★ 加第⑤条后的组合对比")
    print("=" * 62)
    describe("基准 (原四条件)", sigs)
    filtered = [s for s in sigs if s["pos"] <= 0.7 and s["day_pct"] <= 2.0]
    describe("⑤-A: pos≤0.7 且 当日涨幅≤2%", filtered)
    filtered2 = [s for s in sigs if s["pos"] <= 0.9]
    describe("⑤-B: pos≤0.9 (仅剔除极端追高)", filtered2)
    filtered3 = [s for s in sigs if s["day_pct"] <= 3.0]
    describe("⑤-C: 当日涨幅≤3% (仅剔暴涨)", filtered3)

    print(f"\n过滤率: ⑤-A 剔除 {len(sigs)-len(filtered)}/{len(sigs)} = "
          f"{(len(sigs)-len(filtered))/len(sigs)*100:.1f}%")


if __name__ == "__main__":
    main()
