"""盘中实时DSA + 四条件低吸检查 (2026-09-14 14:03 腾讯行情注入)"""
from __future__ import annotations
import sys, json, urllib.request
sys.path.insert(0, "/Users/omi/workspace/quant-backtest")
import pandas as pd, numpy as np
from dsa_scores import score_v1_series

RT = {
    "600988": ("赤峰黄金", "sh", 44.43, 44.39, 43.51, 45.60, 43.30, 303736),
    "000878": ("云南铜业", "sz", 16.80, 17.18, 16.77, 17.09, 16.57, 356635),
    "601138": ("工业富联", "sh", 61.56, 64.07, 62.99, 63.01, 61.37, 664165),
    "002156": ("通富微电", "sz", 56.78, 58.00, 57.30, 57.88, 56.33, 298832),
    "600487": ("亨通光电", "sh", 63.92, 65.24, 63.01, 64.93, 62.22, 925582),
    "600522": ("中天科技", "sh", 33.74, 34.49, 33.84, 34.78, 32.82, 1606841),
    "603380": ("易德龙", "sh", 33.84, 32.26, 32.05, 34.33, 31.65, 39508),
    "600460": ("士兰微", "sh", 29.82, 30.07, 29.65, 30.20, 29.31, 290905),
    "002396": ("星网锐捷", "sz", 34.88, 34.59, 33.95, 35.93, 33.01, 560270),
    "000938": ("紫光股份", "sz", 32.65, 32.84, 32.36, 33.21, 31.91, 647636),
    "600219": ("南山铝业", "sh", 4.80, 4.82, 4.78, 4.82, 4.75, 673385),
    "600760": ("中航沈飞", "sh", 45.54, 48.02, 47.90, 48.25, 45.53, 217340),
}
TODAY = "2026-09-14"


def fetch_kline(sym, n=130):
    url = ("https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param="
           f"{sym},day,,,{n},qfq")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        j = json.loads(r.read().decode())
    d = j["data"][sym]
    arr = d.get("qfqday") or d.get("day")
    rows = [dict(date=a[0], open=float(a[1]), close=float(a[2]),
                 high=float(a[3]), low=float(a[4]), volume=float(a[5])) for a in arr]
    return pd.DataFrame(rows)


def level(s):
    if s >= 90: return "S"
    if s >= 80: return "A"
    if s >= 65: return "B"
    if s >= 50: return "C"
    return "D"


rows = []
for code, (name, mk, px, prev, op, hi, lo, volh) in RT.items():
    sym = mk + code
    try:
        df = fetch_kline(sym)
    except Exception as e:
        rows.append(dict(code=code, name=name, px=px, err=str(e)[:40])); continue
    df = df[df["date"] < TODAY].copy()
    today = pd.DataFrame([dict(date=TODAY, open=op, close=px, high=hi, low=lo,
                               volume=volh * 100)])
    dfx = pd.concat([df, today], ignore_index=True).reset_index(drop=True)
    s = score_v1_series(dfx).iloc[-1]
    c = dfx["close"]
    ma5 = c.rolling(5).mean().iloc[-1]; ma10 = c.rolling(10).mean().iloc[-1]
    ma60 = c.rolling(60).mean().iloc[-1]
    h10 = dfx["high"].iloc[-11:-1].max()
    pullback = (h10 - px) / h10 * 100
    nearMA = min(abs(px - ma5) / ma5 * 100, abs(px - ma10) / ma10 * 100)
    pct = (px - prev) / prev * 100
    ipos = (px - lo) / (hi - lo) * 100 if hi > lo else 50
    c1 = pullback >= 5; c2 = px > ma60; c3 = s >= 65; c4 = nearMA <= 2.0
    rows.append(dict(code=code, name=name, px=px, pct=round(pct, 2), dsa=round(s, 1),
                     lvl=level(s), ma5=round(ma5, 2), ma10=round(ma10, 2),
                     ma60=round(ma60, 2), pullback=round(pullback, 1),
                     nearMA=round(nearMA, 2), ipos=round(ipos, 0),
                     c1=int(c1), c2=int(c2), c3=int(c3), c4=int(c4),
                     LOW=bool(c1 and c2 and c3 and c4)))
    print(f"{code} {name} done", file=sys.stderr)

out = pd.DataFrame(rows)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
print(out.to_string(index=False))
