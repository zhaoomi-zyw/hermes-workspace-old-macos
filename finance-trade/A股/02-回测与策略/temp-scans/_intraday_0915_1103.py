#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘中监控: 用注入的实时价 + 本地日线CSV 当场算 DSA/四条件 (2026-09-15 11:03)"""
import os, sys, json, csv

DATA = "/Users/omi/workspace/quant-backtest/data"
STATE = os.path.expanduser("~/.hermes/state/sell-policy-state.json")

# 注入的腾讯实时行情 09-15 11:03
LIVE = {
    "600988": ("赤峰黄金", 44.54, 0.13, 45.00, 43.81, 132750),
    "000878": ("云南铜业", 16.60, -1.37, 16.76, 16.44, 218090),
    "601138": ("工业富联", 61.46, -0.18, 62.49, 61.21, 293198),
    "002156": ("通富微电", 57.67, 1.57, 58.58, 56.45, 283093),
    "600487": ("亨通光电", 63.20, 0.00, 64.26, 61.88, 779794),
    "600522": ("中天科技", 34.67, 2.27, 35.18, 33.22, 1549663),
    "603380": ("易德龙", 33.58, -1.00, 34.28, 33.32, 12110),
    "600460": ("士兰微", 30.10, 0.84, 30.46, 29.51, 291475),
    "002396": ("星网锐捷", 35.52, 2.01, 36.11, 34.36, 428967),
    "000938": ("紫光股份", 33.10, 1.13, 33.48, 32.40, 586034),
    "600219": ("南山铝业", 4.76, -1.04, 4.81, 4.68, 892295),
    "600760": ("中航沈飞", 45.33, -0.37, 45.77, 45.20, 52676),
}

def load_csv(code, name):
    p = os.path.join(DATA, f"{code}_{name}.csv")
    rows = []
    with open(p) as f:
        for r in csv.DictReader(f):
            try:
                rows.append({
                    "date": r["date"][:10],
                    "open": float(r["open"]), "close": float(r["close"]),
                    "high": float(r["high"]), "low": float(r["low"]),
                    "volume": float(r["volume"]),
                })
            except (ValueError, KeyError):
                continue
    return rows

def sma(v, k):
    return sum(v[-k:]) / k if len(v) >= k else None

def dsa(closes, highs, lows, vols):
    if len(closes) < 60:
        return None
    c = closes[-1]
    ma5, ma10, ma20, ma60 = sma(closes,5), sma(closes,10), sma(closes,20), sma(closes,60)
    if None in (ma5, ma10, ma20, ma60):
        return None
    s = 0.0
    s += 15 if c > ma5 else 0
    s += 10 if ma5 > ma10 else 0
    s += 10 if ma10 > ma20 else 0
    s += 10 if c > ma20 else 0
    s += 15 if c > ma60 else 0
    if c > ma5 and ma5 > ma10 and ma10 > ma20 and ma20 > ma60:
        s += 15
    lo60, hi60 = min(lows[-60:]), max(highs[-60:])
    rng = hi60 - lo60
    s += ((c - lo60) / rng * 15) if rng > 0 else 7.5
    vm20 = sum(vols[-21:-1]) / 20 if len(vols) >= 21 else sum(vols[:-1]) / max(1, len(vols)-1)
    v = vols[-1]
    s += 10 if v < vm20 else (5 if v < vm20*1.5 else 2)
    c20 = closes[-21] if len(closes) >= 21 else None
    c10 = closes[-11] if len(closes) >= 11 else None
    if c20 is not None and c > c20:
        s += 15
    elif c10 is not None and c > c10:
        s += 7
    else:
        s += 3
    return s

def grade(s):
    if s is None: return "?"
    return "S" if s >= 90 else "A" if s >= 80 else "B" if s >= 65 else "C" if s >= 50 else "D"

out = []
for code, (name, price, pct, high, low, vol_lots) in LIVE.items():
    rows = load_csv(code, name)
    if not rows:
        out.append((code, name, None)); continue
    # 今日 bar 用实时价; 量按 11:03 (约2小时/4小时) 年化估算日量
    today = "2026-09-15"
    vols_hist = [r["volume"] for r in rows]
    vm20v = sum(vols_hist[-20:]) / 20
    est_vol = vol_lots * 100 * 2.0   # 11:03 ≈ 半日 → 全日估算
    if rows[-1]["date"] == today:
        rows[-1]["close"] = price; rows[-1]["high"] = max(rows[-1]["high"], high)
        rows[-1]["low"] = min(rows[-1]["low"], low); rows[-1]["volume"] = est_vol
    else:
        rows.append({"date": today, "open": price, "close": price, "high": high,
                     "low": low, "volume": est_vol})
    closes = [r["close"] for r in rows]; highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]; vols = [r["volume"] for r in rows]
    ma5, ma10, ma20, ma60 = sma(closes,5), sma(closes,10), sma(closes,20), sma(closes,60)
    hi10 = max(highs[-10:])
    dd = (hi10 - price) / hi10 * 100
    sc = dsa(closes, highs, lows, vols)
    d5 = abs(price/ma5 - 1) * 100
    d10 = abs(price/ma10 - 1) * 100
    c1 = dd >= 5.0; c2 = price > ma60; c3 = sc is not None and sc >= 65
    c4 = (d5 <= 2.0) or (d10 <= 2.0)
    out.append({
        "code": code, "name": name, "price": price, "pct": pct, "dsa": round(sc,1) if sc else None,
        "grade": grade(sc), "dd": round(dd,1), "ma5": round(ma5,2), "ma10": round(ma10,2),
        "ma20": round(ma20,2), "ma60": round(ma60,2), "d5": round(d5,1), "d10": round(d10,1),
        "hi10": round(hi10,2), "c1": c1, "c2": c2, "c3": c3, "c4": c4,
        "all4": c1 and c2 and c3 and c4,
        "dist_ma60": round((price/ma60 - 1)*100, 1),
        "hi60": round(max(highs[-60:]),2), "pos60": round((price-min(lows[-60:]))/(max(highs[-60:])-min(lows[-60:]))*100,0),
    })

print("=== 四条件扫描 (实时价 11:03) ===")
for o in out:
    if not isinstance(o, dict):
        print("NO DATA", o); continue
    print(f"{o['name']}({o['code']}) {o['price']:.2f} {o['pct']:+.2f}% DSA {o['dsa']}({o['grade']}) "
          f"| ①回撤{o['dd']}% {'✓' if o['c1'] else '✗'} ②{'>MA60✓' if o['c2'] else '<MA60✗'}(MA60 {o['ma60']}, 距{o['dist_ma60']}%) "
          f"③{'DSA✓' if o['c3'] else 'DSA✗'} ④MA5 {o['ma5']}({o['d5']}%)/MA10 {o['ma10']}({o['d10']}%) {'✓' if o['c4'] else '✗'} "
          f"| 10日高{o['hi10']} 60日位{o['pos60']}% {'★四条件全满足★' if o['all4'] else ''}")

st = json.load(open(STATE))
print("\n=== 持仓退出线 (SELL-POLICY-v1.0-20260914) ===")
for k, p in st["positions"].items():
    code = k[2:]
    live = LIVE.get(code)
    if not live: continue
    name, price = live[0], live[1]
    hs = p["hard_stop"]; p["cost"]
    print(f"{name}({code}) 成本{p['cost']} 现价{price} 盈亏{(price/p['cost']-1)*100:+.2f}% | 硬止损{hs} 距{(price/hs-1)*100:+.2f}% "
          f"| 保护线{p['profit_line']} 开保护{p['protection_active']} | peak_H {p['peak_h']} ({p['peak_h_time']}) 可卖{p['sellable_qty']}")
