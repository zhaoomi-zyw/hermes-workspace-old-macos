"""
DSA 评分模块 (可复用)
====================
v1 = 旧版(backtest_planA_3y.py dsa_score_series): 均线结构主导
v3 = 重构版(2026-09-08, IC验证): 动量40+透支惩罚+温和量能20+趋势20
   3日IC 0.000→0.017, 9/11股提升

用法: from dsa_scores import score_v3_series
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def score_v1_series(df: pd.DataFrame) -> pd.Series:
    """旧版(与 backtest_planA_3y.dsa_score_series 一致)"""
    c = df["close"]
    ma5 = c.rolling(5).mean(); ma10 = c.rolling(10).mean()
    ma20 = c.rolling(20).mean(); ma60 = c.rolling(60).mean()
    vol_ma = df["volume"].rolling(20).mean().shift(1)
    score = pd.Series(0.0, index=df.index)
    score += (c > ma5) * 15
    score += (ma5 > ma10) * 10
    score += (ma10 > ma20) * 10
    score += (c > ma20) * 10
    score += (c > ma60) * 15
    perfect = (c > ma5) & (ma5 > ma10) & (ma10 > ma20) & (ma20 > ma60)
    score += perfect * 15
    lo60 = df["low"].rolling(60).min(); hi60 = df["high"].rolling(60).max()
    rng = (hi60 - lo60)
    score += ((c - lo60) / rng * 15).fillna(7.5).where(rng > 0, 7.5)
    last_v = df["volume"]; vm = vol_ma
    vol_score = pd.Series(2.0, index=df.index)
    vol_score = np.where(last_v < vm, 10, np.where(last_v < vm * 1.5, 5, 2))
    score += pd.Series(vol_score, index=df.index)
    c20 = c.shift(20)
    score += np.where(c > c20, 15, np.where(c > c.shift(10), 7, 3))
    return score


def _mom_score(ret10):
    """温和动量(阶梯): 10日涨0-6%满40, 逐级降, 微跌蓄势, 跌深0"""
    mom = pd.Series(0.0, index=ret10.index)
    mom += 40 * ((ret10 > 0) & (ret10 <= 6))
    mom += 25 * ((ret10 > 6) & (ret10 <= 10))
    mom += 12 * ((ret10 > 10) & (ret10 <= 15))
    mom += 4 * ((ret10 > 15) & (ret10 <= 25))
    mom += 12 * ((ret10 > -4) & (ret10 <= 0))
    return mom


def _overheat_penalty(df) -> pd.Series:
    """透支/过热惩罚分 (v3的成分②, 独立提取供混合版用)"""
    c = df["close"]; v = df["volume"]
    ret1 = c.pct_change() * 100
    ret3 = c.pct_change(3) * 100
    ret5 = c.pct_change(5) * 100
    ret10 = c.pct_change(10) * 100
    vm20 = v.rolling(20).mean()
    vr = (v / vm20).fillna(1.0)
    over = pd.Series(0.0, index=df.index)
    over += 12 * ((ret1 > 9.5) | (ret3 > 15))
    over += 12 * ((ret5 > 12) | (ret10 > 25))
    over += 10 * (vr > 2.5)
    over += 6 * ((ret5 > 8) & (ret10 > 12))
    return over


def score_v4_series(df: pd.DataFrame) -> pd.Series:
    """混合版 v4 = v1(均线趋势骨架) - 透支惩罚(过滤追高)
    保留 v1 拿住慢牛股的长处, 叠加 v3 的过热过滤规避实战追高套牢。
    v1满分~100, 透支惩罚最多-40, v4 落到 0~100 同尺度, A/B级阈值沿用 v1(>=65/80)。"""
    s1 = score_v1_series(df)
    penalty = _overheat_penalty(df)
    return (s1 - penalty).clip(lower=0)


def score_v3_series(df: pd.DataFrame) -> pd.Series:
    """重构版 v3: 动量40 + 温和量能20 + 趋势20 - 透支惩罚40"""
    c = df["close"]; v = df["volume"]
    # 动量/收益
    ret1 = c.pct_change() * 100
    ret3 = c.pct_change(3) * 100
    ret5 = c.pct_change(5) * 100
    ret10 = c.pct_change(10) * 100
    ma20 = c.rolling(20).mean(); ma60 = c.rolling(60).mean()
    vm20 = v.rolling(20).mean()
    vr = (v / vm20).fillna(1.0)

    s = pd.Series(0.0, index=df.index)
    # ① 动量 40
    s += _mom_score(ret10)
    # ② 透支惩罚 (减最多40)
    over = pd.Series(0.0, index=df.index)
    over += 12 * ((ret1 > 9.5) | (ret3 > 15))
    over += 12 * ((ret5 > 12) | (ret10 > 25))
    over += 10 * (vr > 2.5)
    over += 6 * ((ret5 > 8) & (ret10 > 12))
    s -= over
    # ③ 温和量能 20
    s += np.where((vr >= 1.0) & (vr <= 2.0), 20,
           np.where((vr >= 0.8) & (vr < 1.0), 12,
           np.where((vr > 2.0) & (vr <= 3.0), 10, 4)))
    # ④ 趋势方向 20: 站上MA60 且 MA20向上
    ma20_up = ma20 > ma20.shift(5)
    s += ((c > ma60) & ma20_up) * 20
    return pd.Series(s.values, index=df.index).clip(lower=0).fillna(0)


def grade_series(score: pd.Series, thr=(75, 60, 45, 30)) -> pd.Series:
    """S/A/B/C/D 分档 (v3用: S>=75/A60/B45/C30/D<30)"""
    s5, s4, s3, s2 = thr
    return pd.Series(np.where(score >= s5, "S",
                     np.where(score >= s4, "A",
                     np.where(score >= s3, "B",
                     np.where(score >= s2, "C", "D")))), index=score.index)
