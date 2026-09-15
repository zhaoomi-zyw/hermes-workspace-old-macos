"""Intraday DSA level check - computes support/resistance from recent daily bars (Sina, fast)."""
from __future__ import annotations
import sys, time
import numpy as np
import pandas as pd
import akshare as ak

STOCKS = {
    "603380": "易德龙", "600988": "赤峰黄金", "600460": "士兰微", "600522": "中天科技",
    "002156": "通富微电", "601138": "工业富联", "000938": "紫光股份", "600487": "亨通光电",
    "002396": "星网锐捷",
}
# DSA default config: lookback/vol_window/shrink/expand/trend_exit_ma/stop/trailing
# industrial-fuyuan override: trend MA30
OVERRIDE = {"601138": 30}

def sina_df(code, name, days=200):
    sym = ("sh" if code.startswith("6") else "sz") + code
    start = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    df = ak.stock_zh_a_daily(symbol=sym, start_date=start, adjust="qfq")
    df = df.rename(columns={"date":"date","open":"open","high":"high","low":"low","close":"close","volume":"volume"})
    df["date"] = pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)

def levels(df, tma_win):
    df = df.copy()
    lb = 20
    support = df["low"].rolling(lb).min().shift(1)
    resistance = df["high"].rolling(lb).max().shift(1)
    vol_ma = df["volume"].rolling(20).mean()
    trend = df["close"].rolling(tma_win).mean()
    last = df.iloc[-1]
    return {
        "date": last["date"].strftime("%Y-%m-%d"),
        "close": float(last["close"]),
        "support": float(support.iloc[-1]) if not np.isnan(support.iloc[-1]) else None,
        "resistance": float(resistance.iloc[-1]) if not np.isnan(resistance.iloc[-1]) else None,
        "trend": float(trend.iloc[-1]) if not np.isnan(trend.iloc[-1]) else None,
        "vol_ratio": float(last["volume"]/vol_ma.iloc[-1]) if vol_ma.iloc[-1]>0 else None,
    }

for code, name in STOCKS.items():
    tma = OVERRIDE.get(code, 60)
    try:
        df = sina_df(code, name)
        lv = levels(df, tma)
        print(f"{code} {name} 收盘:{lv['close']:.2f} 支撑:{lv['support']:.2f} 压力:{lv['resistance']:.2f} 趋势MA{tma}:{lv['trend']:.2f} 量比:{lv['vol_ratio']} 截至:{lv['date']}")
    except Exception as e:
        print(f"{code} {name} ERR: {e}")
    time.sleep(0.4)
