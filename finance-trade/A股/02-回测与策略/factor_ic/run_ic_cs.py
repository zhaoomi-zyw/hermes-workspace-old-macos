#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""因子 IC 检验 · 正确版：截面 IC + 中性化

⚠️ 与前一版的根本区别：
  旧版 = 「时序 IC」（同一只股票的过去 vs 未来）→ 不能做中性化，也回答不了"能否选股"
  本版 = 「截面 IC」（每个交易日跨股票比较）→ 这才是标准因子检验方法

方法：
  每个交易日 t：
    1) 取全部股票在 t 的因子值 x
    2) 行业中性化：x_res = x - mean(x | 同行业)          （严格）
    3) 市值中性化：x_res2 = x_res 对 log(规模) 回归取残差  （规模用当日成交额代理，标注近似）
    4) 未来收益 y = close[t+N] / open[t+1] - 1
    5) IC_t = Spearman(x_final, y)   ← 截面秩相关
  时序聚合：mean(IC_t)、std、IR、t 统计量、胜率（IC_t>0 占比）

规模代理说明：腾讯日K 无成交额/换手率字段，用 volume×close 近似成交额作为规模代理；
             东财 push2his 被限流，无法取历史真实市值 → 该维度为近似，结论需留余量。

输出：universe/ic_cross_sectional.txt + ic_cs_summary.csv
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
FIN_DELAY_DAYS = 45
MIN_STOCKS_PER_DAY = 30   # 截面至少这么多只才算 IC


# ---------- 秩相关（复用 ic_eval.py 手写实现） ----------
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
    if len(a) < MIN_STOCKS_PER_DAY:
        return None
    ra, rb = _rankdata(a), _rankdata(b)
    ma, mb = ra.mean(), rb.mean()
    cov = np.sum((ra - ma) * (rb - mb))
    va = math.sqrt(float(np.sum((ra - ma) ** 2) * np.sum((rb - mb) ** 2)))
    return (cov / va if va > 0 else 0.0)


# ---------- 载入面板 ----------
def load_panel():
    ddir = os.path.join(BASE, "daily")
    fdir = os.path.join(BASE, "fin")
    ind = json.load(open(os.path.join(BASE, "industry_map.json"), encoding="utf-8"))
    codes = [f[:-4] for f in sorted(os.listdir(ddir)) if f.endswith(".csv")]

    # 先确定统一交易日网格
    all_dates = set()
    raw = {}
    for c in codes:
        rows = list(csv.DictReader(open(os.path.join(ddir, f"{c}.csv"), encoding="utf-8")))
        raw[c] = rows
        all_dates |= {r["date"] for r in rows}
    dates = sorted(all_dates)
    di = {d: i for i, d in enumerate(dates)}
    T, N = len(dates), len(codes)

    P = {k: np.full((T, N), np.nan) for k in ("open", "close", "high", "low", "volume")}
    for j, c in enumerate(codes):
        for r in raw[c]:
            i = di[r["date"]]
            for k in P:
                try:
                    P[k][i, j] = float(r[k])
                except (TypeError, ValueError):
                    pass

    # 财务 → 按公告日（报告期+45天）写入，前向填充
    FINCOLS = ("gross_margin", "net_margin", "rev_yoy", "np_yoy", "ocf_to_income")
    F = {k: np.full((T, N), np.nan) for k in FINCOLS}
    for j, c in enumerate(codes):
        fp = os.path.join(fdir, f"{c}.csv")
        if not os.path.exists(fp):
            continue
        recs = []
        for r in csv.DictReader(open(fp, encoding="utf-8")):
            rep = (r.get("report") or "").strip()
            if not rep or "-" not in rep:
                continue
            try:
                y, q = rep.split("-")
                q = int(q)
                end = {1: 3, 2: 6, 3: 9, 4: 12}[q]
                ann = (date(int(y), end, 28) + timedelta(days=FIN_DELAY_DAYS)).strftime("%Y-%m-%d")
            except Exception:
                continue
            recs.append((ann, r))
        recs.sort()
        for i, d in enumerate(dates):
            last = None
            for ann, r in recs:
                if d >= ann:
                    last = r
                else:
                    break
            if last:
                for k in FINCOLS:
                    try:
                        F[k][i, j] = float(last[k])
                    except (TypeError, ValueError):
                        pass

    # 行业分组
    grp = np.array([ind.get(c, {}).get("industry", "UNKNOWN") for c in codes])
    return dates, codes, P, F, grp


def build_price_factors(P):
    close, openp, vol = P["close"], P["open"], P["volume"]
    T, N = close.shape
    f = {}
    f["反转20日"] = -_shift(close, 20) / close + 1   # 取负：过去20日跌的得分高
    f["动量60日"] = _shift(close, 60) / close - 1     # 取正：过去60日涨的得分高
    ret = np.full_like(close, np.nan)
    ret[1:] = close[1:] / close[:-1] - 1
    f["波动率20日"] = _roll_std(ret, 20)
    f["量比(60日)"] = vol / _roll_mean(vol, 60)
    f["额比(60日)"] = (vol * close) / _roll_mean(vol * close, 60)
    f["振幅"] = (P["high"] - P["low"]) / _shift(close, 1)
    f["规模(log成交额)"] = np.log(vol * close)   # 市值代理
    return f


def _shift(a, k):
    o = np.full_like(a, np.nan)
    if k < a.shape[0]:
        o[k:] = a[:-k]
    return o


def _roll_mean(a, w):
    o = np.full_like(a, np.nan)
    for i in range(w - 1, a.shape[0]):
        o[i] = np.nanmean(a[i - w + 1:i + 1], axis=0)
    return o


def _roll_std(a, w):
    o = np.full_like(a, np.nan)
    for i in range(w - 1, a.shape[0]):
        o[i] = np.nanstd(a[i - w + 1:i + 1], axis=0)
    return o


def fwd_returns(P):
    close, openp = P["close"], P["open"]
    T = close.shape[0]
    no = np.full_like(openp, np.nan)
    no[:-1] = openp[1:]
    out = {}
    for h in HORIZONS:
        fc = np.full_like(close, np.nan)
        if h < T:
            fc[:-h] = close[h:]
        out[h] = fc / no - 1
    return out


def neutralize(x, grp, size):
    """行业中性化（严格）+ 规模中性化（近似）"""
    y = x.copy()
    y = y - np.nanmean(y)
    # ① 行业去均值
    out = np.full_like(y, np.nan)
    for g in set(grp):
        m = grp == g
        seg = y[m]
        if np.sum(~np.isnan(seg)) >= 3:
            out[m] = seg - np.nanmean(seg)
        else:
            out[m] = seg
    # ② 对 log(规模) 回归取残差（逐日截面 OLS，一元）
    if size is not None:
        m = ~(np.isnan(out) | np.isnan(size))
        if m.sum() >= MIN_STOCKS_PER_DAY:
            xv = size[m]
            yv = out[m]
            xv2 = xv - xv.mean()
            denom = float(np.sum(xv2 * xv2))
            if denom > 0:
                beta = float(np.sum(xv2 * (yv - yv.mean()))) / denom
                out[m] = yv - (yv.mean() + beta * xv2)
    return out


def main():
    dates, codes, P, F, grp = load_panel()
    T, N = P["close"].shape
    print(f"面板: {N} 只 × {T} 个交易日  ({dates[0]} ~ {dates[-1]})")
    print(f"行业数: {len(set(grp))}   最大行业: {max(set(grp), key=lambda g: list(grp).count(g))}")

    pf = build_price_factors(P)
    fwd = fwd_returns(P)

    factors = {}
    factors.update(pf)
    for k, M in F.items():
        factors[k] = M

    results = []
    raw_ics = {}
    for fname, M in factors.items():
        if fname == "规模(log成交额)":
            continue   # 规模只作中性化变量，不当因子测
        size = pf["规模(log成交额)"]
        for h in HORIZONS:
            ics, ics_raw = [], []
            for t in range(T):
                x = M[t, :]
                y = fwd[h][t, :]
                if np.sum(~np.isnan(x) & ~np.isnan(y)) < MIN_STOCKS_PER_DAY:
                    continue
                ic_raw = spearman(x, y)
                if ic_raw is not None:
                    ics_raw.append(ic_raw)
                xn = neutralize(x, grp, size[t, :])
                ic = spearman(xn, y)
                if ic is not None:
                    ics.append(ic)
            if len(ics) < 20:
                results.append((fname, h, None, None, None, None, len(ics), None))
                continue
            arr = np.array(ics)
            arrn = np.array(ics_raw) if ics_raw else np.array([np.nan])
            mean_ic = float(arr.mean())
            std_ic = float(arr.std())
            ir = mean_ic / std_ic if std_ic > 0 else None
            tstat = mean_ic / (std_ic / math.sqrt(len(arr))) if std_ic > 0 else None
            win = float((arr > 0).mean())
            results.append((fname, h, mean_ic, ir, tstat, win, len(arr), float(arrn.mean())))

    # ---------- 输出 ----------
    L = []
    L.append("因子截面 IC（行业+规模中性化）· 沪深300 样本")
    L.append("=" * 120)
    L.append(f"样本: {N} 只 × {T} 交易日 ({dates[0]} ~ {dates[-1]})｜行业中性化=严格｜规模中性化=用成交额代理(近似)")
    L.append("")
    L.append(f"{'因子':<20}{'H':>4}{'IC均值':>10}{'IC原始':>10}{'IR':>8}{'t值':>9}{'IC>0占比':>10}{'交易日数':>10}")
    L.append("-" * 120)
    for fname in factors:
        if fname == "规模(log成交额)":
            continue
        for h in HORIZONS:
            r = [x for x in results if x[0] == fname and x[1] == h]
            if not r:
                continue
            _, _, mic, ir, tst, win, n, raw = r[0]
            if mic is None:
                L.append(f"{fname:<20}{h:>4}{'—':>10}{'—':>10}{'—':>8}{'—':>9}{'—':>10}{n:>10}")
            else:
                L.append(f"{fname:<20}{h:>4}{mic:>+10.4f}"
                         f"{(raw if raw is not None else float('nan')):>+10.4f}"
                         f"{(ir if ir is not None else float('nan')):>8.2f}"
                         f"{(tst if tst is not None else float('nan')):>9.2f}"
                         f"{win*100:>9.0f}%{n:>10}")
    L.append("-" * 120)
    L.append("")
    L.append("【H3→H5 排序（按中性化后 |IC均值|）】")
    rows3 = [x for x in results if x[1] == 5 and x[2] is not None]
    for i, x in enumerate(sorted(rows3, key=lambda z: -abs(z[2])), 1):
        tag = "★★" if abs(x[2]) >= 0.05 and abs(x[4] or 0) >= 2 else ("★" if abs(x[2]) >= 0.03 else "△")
        L.append(f"  {i}. {x[0]:<20} IC={x[2]:+.4f}  IR={x[3]:+.2f}  t={x[4]:+.2f}  胜率{x[5]*100:.0f}%  {tag}")
    L.append("")
    L.append("判断标准: |IC|>0.05 且 |t|>2 → 统计显著；|IC|<0.03 → 无预测力")
    L.append("⚠️ 规模中性化为近似（成交额代理），历史真实市值未能取得（东财限流）")

    txt = "\n".join(L)
    print("\n" + txt)
    open(os.path.join(BASE, "ic_cross_sectional.txt"), "w", encoding="utf-8").write(txt)
    with open(os.path.join(BASE, "ic_cs_summary.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["factor", "horizon", "ic_mean", "ic_raw", "ir", "t_stat", "ic_pos_ratio", "days"])
        for x in results:
            w.writerow(x)
    print(f"\n✅ {BASE}/ic_cross_sectional.txt")


if __name__ == "__main__":
    main()
