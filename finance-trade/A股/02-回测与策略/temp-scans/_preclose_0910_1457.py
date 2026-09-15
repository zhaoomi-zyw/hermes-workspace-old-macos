# -*- coding: utf-8 -*-
"""收盘前(14:57)实时DSA：日线(至09-09) + 今日实时价拼接，当场算v1 DSA五维"""
import pandas as pd, numpy as np
from dsa_scores import score_v1_series

WATCH = {
 "600988": ("赤峰黄金", 44.35, 43.52, 44.63, 43.07, 403750),
 "000878": ("云南铜业", 18.71, 19.00, 19.06, 18.54, 665109),
 "601138": ("工业富联", 63.91, 64.50, 64.66, 63.79, 559751),
 "002156": ("通富微电", 58.34, 57.65, 59.23, 57.51, 410228),
 "600487": ("亨通光电", 63.91, 65.01, 65.68, 63.80, 1445291),
 "600522": ("中天科技", 33.30, 33.70, 33.90, 33.24, 1265205),
 "603380": ("易德龙", 32.68, 33.48, 33.51, 32.45, 29057),
 "600460": ("士兰微", 30.24, 30.00, 30.63, 29.80, 441466),
 "002396": ("星网锐捷", 35.99, 35.80, 36.58, 35.20, 666469),
 "000938": ("紫光股份", 33.10, 33.18, 33.65, 32.98, 768458),
 "600219": ("南山铝业", 5.00, 5.05, 5.08, 4.98, 1254882),
 "600760": ("中航沈飞", 48.61, 48.70, 49.38, 48.57, 136412),
}
rows = []
for code, (name, px, op, hi, lo, vol_hand) in WATCH.items():
    df = pd.read_csv(f"data/{code}_{name}.csv", parse_dates=["date"])
    df = df[df["date"] <= "2026-09-09"].copy()
    live = pd.DataFrame([{"date": pd.Timestamp("2026-09-10"), "open": op, "high": hi,
                          "low": lo, "close": px, "volume": vol_hand*100, "code": code, "name": name}])
    d = pd.concat([df, live], ignore_index=True)
    s = score_v1_series(d)
    dsa = round(float(s.iloc[-1]), 1)
    grade = "S" if dsa>=90 else "A" if dsa>=80 else "B" if dsa>=65 else "C" if dsa>=50 else "D"
    c = d["close"]
    ma5, ma10, ma20, ma60 = [c.rolling(n).mean().iloc[-1] for n in (5,10,20,60)]
    hi10 = d["high"].iloc[-11:-1].max()
    dd = (hi10 - px)/hi10*100
    lo60, hi60 = d["low"].iloc[-60:].min(), d["high"].iloc[-60:].max()
    pos60 = (px-lo60)/(hi60-lo60)*100
    chg = (px/d["close"].iloc[-2]-1)*100
    near_ma = min(abs(px/ma5-1), abs(px/ma10-1))*100
    cond = [dd>=5, px>ma60, dsa>=65, near_ma<=3]
    rows.append(dict(code=code,name=name,px=px,chg=round(chg,2),dsa=dsa,grade=grade,
        ma5=round(ma5,2),ma10=round(ma10,2),ma60=round(ma60,2),dd=round(dd,1),
        pos60=round(pos60,1),near=round(near_ma,2),n=sum(cond),cond=cond))
out = pd.DataFrame(rows)
pd.set_option("display.width", 250, "display.max_columns", 50)
print(out.to_string(index=False))
