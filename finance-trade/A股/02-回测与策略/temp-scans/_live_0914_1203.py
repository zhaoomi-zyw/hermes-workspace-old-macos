"""盘中实时DSA + 四条件低吸检查 (2026-09-14 12:03 腾讯行情注入, 午间休市)"""
from __future__ import annotations
import sys, os
sys.path.insert(0, "/Users/omi/workspace/quant-backtest")
import pandas as pd, numpy as np
from dsa_scores import score_v1_series

DATA = "/Users/omi/workspace/quant-backtest/data"
TODAY = "2026-09-14"

# code -> (name, price, prev_close, open, high, low, vol_hand)
RT = {
    "600988": ("赤峰黄金", 44.59, 44.39, 43.51, 45.60, 43.30, 251941),
    "000878": ("云南铜业", 16.93, 17.18, 16.77, 17.09, 16.57, 279886),
    "601138": ("工业富联", 62.12, 64.07, 62.99, 63.01, 61.70, 467927),
    "002156": ("通富微电", 57.35, 58.00, 57.30, 57.88, 56.33, 222722),
    "600487": ("亨通光电", 63.93, 65.24, 63.01, 64.93, 62.22, 770161),
    "600522": ("中天科技", 34.06, 34.49, 33.84, 34.78, 32.82, 1388788),
    "603380": ("易德龙", 33.99, 32.26, 32.05, 34.33, 31.65, 34991),
    "600460": ("士兰微", 30.06, 30.07, 29.65, 30.20, 29.31, 234378),
    "002396": ("星网锐捷", 35.28, 34.59, 33.95, 35.93, 33.01, 466147),
    "000938": ("紫光股份", 32.85, 32.84, 32.36, 33.21, 31.91, 543723),
    "600219": ("南山铝业", 4.80, 4.82, 4.78, 4.82, 4.75, 516742),
    "600760": ("中航沈飞", 46.19, 48.02, 47.90, 48.25, 45.70, 165395),
}

HOLD = {"600988": (44.735, 200), "002396": (35.880, 100)}

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
    last_hist = df["date"].max()
    df = df[df["date"] < TODAY].sort_values("date").reset_index(drop=True)
    today = pd.DataFrame([{"date": pd.Timestamp(TODAY), "open": op, "high": hi,
                           "low": lo, "close": px, "volume": volh*100}])
    dfx = pd.concat([df, today], ignore_index=True)
    s = score_v1_series(dfx).iloc[-1]
    c = dfx["close"]
    ma5 = c.rolling(5).mean().iloc[-1]; ma10 = c.rolling(10).mean().iloc[-1]
    ma20 = c.rolling(20).mean().iloc[-1]; ma60 = c.rolling(60).mean().iloc[-1]
    h10 = dfx["high"].iloc[-11:-1].max()
    pullback = (h10 - px)/h10*100
    near5 = abs(px-ma5)/ma5*100
    near10 = abs(px-ma10)/ma10*100
    nearMA = min(near5, near10)
    pct = (px-prev)/prev*100
    pos = (px-lo)/(hi-lo)*100 if hi > lo else 50.0
    cond1 = pullback >= 5
    cond2 = px > ma60
    cond3 = s >= 65
    cond4 = nearMA <= 2.0
    all4 = cond1 and cond2 and cond3 and cond4
    rows.append(dict(code=code, name=name, px=px, pct=pct, last_hist=str(last_hist)[:10],
                     dsa=round(s,1), lv=level(s), ma5=ma5, ma10=ma10, ma20=ma20, ma60=ma60,
                     pullback=pullback, nearMA=nearMA, h10=h10, pos=pos,
                     c1=cond1, c2=cond2, c3=cond3, c4=cond4, all4=all4,
                     hold=(code in HOLD)))

out = pd.DataFrame(rows)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 50)
print(out[["code","name","px","pct","last_hist","dsa","lv","ma5","ma10","ma60","pullback","nearMA","h10","pos","c1","c2","c3","c4","all4"]].to_string(index=False))

print("\n--- 持仓 ---")
for code,(cost,sh) in HOLD.items():
    r = out[out.code==code].iloc[0]
    pnl = (r.px-cost)/cost*100
    print(f"{r.name} {code}: 现价{r.px} 成本{cost} 浮动{pnl:+.2f}% ({sh}股, 市值{r.px*sh:.0f}元) 日内位置{r.pos:.0f}% 昨收{r.pct:+.2f}%")
print("\n--- 四条件缺口 ---")
for _,r in out.iterrows():
    miss = [n for n,v in [("回撤≥5%",r.c1),("站上MA60",r.c2),("DSA≥65",r.c3),("近MA5/10≤2%",r.c4)] if not v]
    print(f"{r.name}: {'ALL4 ✅' if r.all4 else '缺 ' + ','.join(miss)}")
