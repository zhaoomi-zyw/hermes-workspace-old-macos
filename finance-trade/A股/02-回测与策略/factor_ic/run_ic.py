#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""因子 IC 检验 · 第2步：因子计算 + IC 评估

方法论复用 quant-backtest/ic_eval.py：
  · 手写 Spearman Rank IC（不依赖 scipy）
  · 分块 IR（每21交易日一块 → 平均IC/IC标准差）
  · 未来收益用「次日开盘 → 未来N日收盘」，避免与信号同源
  · 全部 shift 防未来函数

⚠️ 财务数据的可用日：按「报告期结束后 +45 天」近似公告日，避免前视偏差。

因子清单（12只 × 3年）：
  价格类   : 反转20日 / 动量60日 / 波动率20日 / 量比(换手代理) / 额比(流动性)
  财务类   : ROE / 毛利率 / 净利率 / 净利增速 / 营收增速 / 资产负债率 / 资产周转率
  质量类   : ⭐ 应计(经营现金流÷净利润) / 盈利现金含量
输出：results/factor_ic_20260918/ic_report.txt + ic_summary.csv
⚠️ 纯研究，不写任何实盘链路。
"""
from __future__ import annotations

import os
import csv
import json
import math
import numpy as np

import sys
_D = None
if "--dir" in sys.argv:
    _i = sys.argv.index("--dir")
    _D = sys.argv[_i + 1]
OUT = _D or "/Users/omi/workspace/quant-backtest/results/factor_ic_20260918"
HORIZONS = (1, 3, 5, 10)
FIN_DELAY_DAYS = 45   # 报告期结束后这么多天视为已公告


# ---------------- 手写秩相关（复用 ic_eval.py 方法） ----------------
def _rankdata(a):
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2.0 + 1
        i = j + 1
    return ranks


def spearman(a, b):
    a = np.asarray(a, dtype=float).flatten()
    b = np.asarray(b, dtype=float).flatten()
    m = ~(np.isnan(a) | np.isnan(b))
    a, b = a[m], b[m]
    n = len(a)
    if n < 10:
        return None, n
    ra, rb = _rankdata(a), _rankdata(b)
    ma, mb = ra.mean(), rb.mean()
    cov = np.sum((ra - ma) * (rb - mb))
    va = math.sqrt(float(np.sum((ra - ma) ** 2) * np.sum((rb - mb) ** 2)))
    return (cov / va if va > 0 else 0.0), n


def load_daily(code):
    p = os.path.join(OUT, "daily", f"{code}.csv")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    d = {}
    for k in ("open", "close", "high", "low", "volume"):
        d[k] = np.array([float(r[k]) if r[k] not in ("", "None") else np.nan for r in rows])
    # 成交额近似（腾讯日K无成交额字段）：量(手) × 100 × 收盘价
    d["turnover"] = d["volume"] * 100.0 * d["close"]
    d["date"] = [r["date"] for r in rows]
    return d


def load_fin(code):
    p = os.path.join(OUT, "fin", f"{code}.csv")
    if not os.path.exists(p):
        return []
    with open(p, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def build_factors(code):
    """返回 {factor_name: np.array} 与 未来收益矩阵"""
    d = load_daily(code)
    if d is None or len(d["close"]) < 120:
        return None, None
    close, openp = d["close"], d["open"]
    vol, amt = d["volume"], d["turnover"]
    n = len(close)

    ret = np.concatenate([[np.nan], close[1:] / close[:-1] - 1])
    f = {}
    # ---- 价格类 ----
    f["反转20日"] = -((close / _shift(close, 20) - 1))
    f["动量60日"] = (close / _shift(close, 60) - 1)
    f["波动率20日"] = _roll_std(ret, 20)
    f["量比(60日)"] = vol / _roll_mean(vol, 60)          # 换手率代理（时序可比）
    f["额比(60日)"] = amt / _roll_mean(amt, 60)          # 流动性/关注度代理
    f["振幅"] = (d["high"] - d["low"]) / _shift(close, 1)

    # ---- 财务类（按公告日对齐）----
    fin = load_fin(code)
    for fname in ("roe", "gross_margin", "net_margin", "np_yoy", "rev_yoy",
                  "debt_ratio", "asset_turnover", "ocf_to_income", "np_cash_content"):
        arr = np.full(n, np.nan)
        for rec in fin:
            rep = rec.get("report") or ""
            v = rec.get(fname)
            if not rep or v in (None, ""):
                continue
            try:
                y, q = rep.split("-")
                q = int(q)
                # 报告期结束日
                end = {1: 3, 2: 6, 3: 9, 4: 12}[q]
                import datetime as _dt
                ann = _dt.date(int(y), end, 28) + _dt.timedelta(days=FIN_DELAY_DAYS)
                ann_s = ann.strftime("%Y-%m-%d")
            except Exception:
                continue
            try:
                val = float(v)
            except (TypeError, ValueError):
                continue
            for i, ds in enumerate(d["date"]):
                if ds >= ann_s:
                    arr[i] = val          # 用最近一次已公告值（前向填充）
        f[fname] = arr

    # ---- 未来收益：次日开盘 → 未来 h 日收盘 ----
    fwd = {}
    next_open = _shift_fwd(openp, 1)
    for h in HORIZONS:
        fwd[h] = _shift_fwd(close, h) / next_open - 1
    return f, fwd


def _shift(a, k):
    out = np.full_like(a, np.nan, dtype=float)
    if k < len(a):
        out[k:] = a[:-k]
    return out


def _shift_fwd(a, k):
    out = np.full_like(a, np.nan, dtype=float)
    if k < len(a):
        out[:-k] = a[k:]
    return out


def _roll_mean(a, w):
    out = np.full_like(a, np.nan, dtype=float)
    for i in range(w - 1, len(a)):
        out[i] = np.nanmean(a[i - w + 1:i + 1])
    return out


def _roll_std(a, w):
    out = np.full_like(a, np.nan, dtype=float)
    for i in range(w - 1, len(a)):
        out[i] = np.nanstd(a[i - w + 1:i + 1])
    return out


def block_ir(fac, fwd, blk=21):
    """分块 IC → IR（平均/标准差）"""
    ics = []
    for s in range(0, len(fac) - blk + 1, blk):
        r, n = spearman(fac[s:s + blk], fwd[s:s + blk])
        if r is not None and not np.isnan(r):
            ics.append(r)
    if len(ics) < 3:
        return None, 0
    return float(np.mean(ics) / np.std(ics)) if np.std(ics) > 0 else None, len(ics)


def main():
    codes = [f[:-4] for f in sorted(os.listdir(os.path.join(OUT, "daily"))) if f.endswith(".csv")]
    print(f"因子 IC 检验 · 样本 {len(codes)} 只 × 3年\n" + "=" * 100)

    agg = {}   # factor -> {h: [ic,...]}
    for code in codes:
        try:
            f, fwd = build_factors(code)
        except Exception as e:
            print(f"  {code} 计算失败: {type(e).__name__} {e}")
            continue
        if f is None:
            print(f"  {code} 数据不足")
            continue
        for fname, arr in f.items():
            agg.setdefault(fname, {h: [] for h in HORIZONS})
            for h in HORIZONS:
                r, n = spearman(arr, fwd[h])
                if r is not None:
                    agg[fname][h].append(r)
        print(f"  {code} ✓ ({len(f)} 个因子)")

    # ---- 汇总 ----
    lines = []
    lines.append("因子 IC 汇总（Spearman Rank IC，跨12只取均值；A股3年样本）")
    lines.append("=" * 100)
    hdr = (f"{'因子':<20}" + "".join(f"{'H'+str(h):>9}" for h in HORIZONS)
           + f"{'|IC|均值':>10}{'方向':>6}{'样本':>6}{'IC中位':>9}{'正占比':>9}")
    lines.append(hdr)
    lines.append("-" * 100)

    rows_csv = []
    rank = []
    for fname, d in agg.items():
        ics = {h: (np.nanmean(d[h]) if d[h] else np.nan) for h in HORIZONS}
        absmean = np.nanmean([abs(ics[h]) for h in HORIZONS if not np.isnan(ics[h])])
        ns = len(d[HORIZONS[0]])
        direction = "正" if (not np.isnan(ics[HORIZONS[1]] if len(HORIZONS) > 1 else ics[HORIZONS[0]])) and \
                            (ics[HORIZONS[1]] if len(HORIZONS) > 1 else ics[HORIZONS[0]]) > 0 else "负"
        # 股票间分布：IC 的中位数 / 正值占比（判断是否被少数股票主导）
        hh = HORIZONS[1] if len(HORIZONS) > 1 else HORIZONS[0]
        lst = d[hh]
        med = float(np.median(lst)) if lst else float("nan")
        posr = float(np.mean([1 if x > 0 else 0 for x in lst])) if lst else float("nan")
        lines.append(f"{fname:<20}" + "".join(
            f"{ics[h]:>+9.4f}" if not np.isnan(ics[h]) else f"{'—':>9}" for h in HORIZONS) +
            f"{absmean:>10.4f}{direction:>6}{ns:>6}{med:>+9.4f}{posr*100:>8.0f}%")
        rows_csv.append({"factor": fname, **{f"IC_H{h}": ics[h] for h in HORIZONS},
                         "abs_ic_mean": absmean, "n_stocks": ns})
        rank.append((absmean, fname))

    lines.append("-" * 100)
    lines.append("")
    lines.append("按 |IC| 均值排序（预测力从强到弱）：")
    for i, (v, nm) in enumerate(sorted(rank, reverse=True), 1):
        tag = "★强" if v >= 0.05 else ("○弱" if v >= 0.03 else "△接近0")
        lines.append(f"  {i:>2}. {nm:<20} |IC|={v:.4f}  {tag}")
    lines.append("")
    lines.append("判断标准: |IC|<0.03 ≈ 无预测力 | 0.03-0.05 弱 | >0.05 较可靠")
    lines.append("「IC中位」「正占比」= 跨股票的分布 → 判断是否被少数股票主导（稳健性关键）")
    lines.append("⚠️ 这是「单因子、未中性化、未扣费」的原始 IC，仅作筛选，不等于可盈利。")

    txt = "\n".join(lines)
    print("\n" + txt)
    open(os.path.join(OUT, "ic_report.txt"), "w", encoding="utf-8").write(txt)
    with open(os.path.join(OUT, "ic_summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows_csv[0].keys()))
        w.writeheader()
        w.writerows(rows_csv)
    print(f"\n✅ 报告 → {OUT}/ic_report.txt")


if __name__ == "__main__":
    main()
