"""盘中实时DSA + 四条件低吸检查 (2026-09-11 12:03 腾讯行情注入)"""
from __future__ import annotations
import sys, os
sys.path.insert(0, "/Users/omi/workspace/quant-backtest")
import pandas as pd, numpy as np
from dsa_scores import score_v1_series

DATA = "/Users/omi/workspace/quant-backtest/data"

# code -> (name, price, prev_close, open, high, low, vol_hand)
RT = {
    "600988": ("赤峰黄金", 42.99, 44.30, 42.90, 43.49, 42.32, 290958),
    "000878": ("云南铜业", 16.89, 18.71, 17.59, 17.70, 16.84, 842662),
    "601138": ("工业富联", 63.06, 63.91, 62.66, 64.49, 62.50, 474825),
    "002156": ("通富微电", 56.52, 58.34, 57.01, 57.65, 56.22, 344404),
    "600487": ("亨通光电", 62.62, 63.91, 62.00, 65.06, 61.80, 1032011),
    "600522": ("中天科技", 32.91, 33.30, 32.66, 34.15, 32.66, 1387746),
    "603380": ("易德龙", 31.73, 32.72, 32.49, 32.65, 31.52, 17023),
    "600460": ("士兰微", 29.20, 30.24, 29.75, 29.96, 29.00, 365240),
    "002396": ("星网锐捷", 33.43, 35.99, 35.01, 35.86, 33.32, 533654),
    "000938": ("紫光股份", 32.03, 33.10, 32.75, 33.18, 31.90, 836941),
    "600219": ("南山铝业", 4.79, 5.00, 4.90, 4.91, 4.76, 1304705),
    "600760": ("中航沈飞", 48.05, 48.60, 48.58, 48.90, 47.63, 107218),
}

def level(s):
    if s >= 90: return "S"
    if s >= 80: return "A"
    if s >= 65: return "B"
    if s >= 50: return "C"
    return "D"

rows = []
for code, (name, px, prev, op, hi, lo, volh) in RT.items():
    path = os.path.join(DATA, f"{code}_{name}.csv")
    df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]
    df = df[["date","open","high","low","close","volume"]].copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"] <= "2026-09-10"].sort_values("date").reset_index(drop=True)
    # append today's live bar (volume hand -> shares)
    today = pd.DataFrame([{"date": pd.Timestamp("2026-09-11"), "open": op, "high": hi,
                           "low": lo, "close": px, "volume": volh*100}])
    dfx = pd.concat([df, today], ignore_index=True)
    s = score_v1_series(dfx).iloc[-1]
    c = dfx["close"]
    ma5 = c.rolling(5).mean().iloc[-1]; ma10 = c.rolling(10).mean().iloc[-1]
    ma20 = c.rolling(20).mean().iloc[-1]; ma60 = c.rolling(60).mean().iloc[-1]
    h10 = dfx["high"].iloc[-11:-1].max()
    pullback = (h10 - px)/h10*100
    above60 = px > ma60
    near5 = abs(px-ma5)/ma5*100
    near10 = abs(px-ma10)/ma10*100
    nearMA = min(near5, near10)
    pct = (px-prev)/prev*100
    cond1 = pullback >= 5
    cond2 = above60
    cond3 = s >= 65
    cond4 = nearMA <= 2.0
    all4 = cond1 and cond2 and cond3 and cond4
    rows.append(dict(code=code, name=name, px=px, pct=round(pct,2), dsa=round(s,1), lvl=level(s),
                     ma5=round(ma5,2), ma10=round(ma10,2), ma20=round(ma20,2), ma60=round(ma60,2),
                     pullback=round(pullback,1), above60=above60, nearMA=round(nearMA,2),
                     c1=cond1, c2=cond2, c3=cond3, c4=cond4, LOW=all4))

out = pd.DataFrame(rows)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
print(out.to_string(index=False))
print("\n=== 四条件全满足(低吸信号) ===")
print(out[out.LOW][["code","name","px","dsa","lvl","pullback","nearMA"]].to_string(index=False) or "无")
