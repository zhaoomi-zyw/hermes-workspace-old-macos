#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""盘中快照 2026-09-15 13:03 — 12自选 DSA + 四条件 + 持仓退出线距离 (只读, 不动低吸dedup)"""
import sys, datetime, importlib.util, json

sys.path.insert(0, "/Users/omi/.hermes/profiles/main/scripts")
spec = importlib.util.spec_from_file_location(
    "lowbuy_watch", "/Users/omi/.hermes/profiles/main/scripts/lowbuy-watch.py")
m = importlib.util.module_from_spec(spec)
sys.modules["lowbuy_watch"] = m
spec.loader.exec_module(m)

st = json.load(open("/Users/omi/.hermes/state/sell-policy-state.json"))
pos = st.get("positions", {})

WATCH = m.WATCHLIST
rt = m.fetch_realtime(list(WATCH.keys()))
today = datetime.datetime.now().strftime("%Y-%m-%d")

rows_out = []
for code in WATCH:
    if code not in rt:
        rows_out.append((code, WATCH[code], None, "无行情"))
        continue
    q = rt[code]
    price = q["price"]
    rows = m.fetch_kline(code)
    if len(rows) < 65:
        rows_out.append((code, WATCH[code], None, "K线不足"))
        continue
    if rows[-1]["date"] == today:
        rows[-1]["close"] = price
        rows[-1]["high"] = max(rows[-1]["high"], q["high"])
        if q["low"] > 0:
            rows[-1]["low"] = min(rows[-1]["low"], q["low"])
    closes = [r["close"] for r in rows]
    highs = [r["high"] for r in rows]
    lows = [r["low"] for r in rows]
    vols = [r["volume"] for r in rows]
    ma5, ma10, ma20, ma60 = m.sma(closes, 5), m.sma(closes, 10), m.sma(closes, 20), m.sma(closes, 60)
    hi10 = max(highs[-10:])
    dd = (hi10 - price) / hi10 * 100
    dsa = m.dsa_score(closes, highs, lows, vols)
    d5 = abs(price / ma5 - 1) * 100
    d10 = abs(price / ma10 - 1) * 100
    c1 = dd >= m.DD_MIN
    c2 = price > ma60
    c3 = dsa is not None and dsa >= m.DSA_MIN
    c4 = (d5 <= m.NEAR_MA_PCT) or (d10 <= m.NEAR_MA_PCT)
    vm20 = sum(vols[-21:-1]) / 20
    vr = vols[-1] / vm20 if vm20 else 0
    rows_out.append((code, WATCH[code], {
        "price": price, "pct": q["pct"], "ma5": ma5, "ma10": ma10, "ma20": ma20, "ma60": ma60,
        "dd": dd, "dsa": dsa, "grade": m.grade(dsa), "d5": d5, "d10": d10,
        "c1": c1, "c2": c2, "c3": c3, "c4": c4, "vr": vr, "vv": sum(1 for x in (c1, c2, c3, c4) if x),
    }, None))

print("=== 快照", datetime.datetime.now().strftime("%H:%M:%S"), "===")
for code, name, d, err in sorted(rows_out, key=lambda x: -(x[2]["dsa"] if x[2] else -1)):
    if d is None:
        print(f"{name}({code[2:]}) {err}")
        continue
    mark = "★四条件全满足" if d["vv"] == 4 else f"满足{d['vv']}/4"
    print(f"{name}({code[2:]}) 现价{d['price']:.2f} ({d['pct']:+.2f}%) DSA {d['dsa']:.0f}{d['grade']} | "
          f"①回撤{d['dd']:.1f}%{'✓' if d['c1'] else '✗'} ②MA60 {d['ma60']:.2f}{'✓' if d['c2'] else '✗'} "
          f"③DSA{'✓' if d['c3'] else '✗'} ④MA5 {d['ma5']:.2f}(距{d['d5']:.1f}%)/MA10 {d['ma10']:.2f}(距{d['d10']:.1f}%){'✓' if d['c4'] else '✗'} "
          f"| 量比{d['vr']:.2f} {mark}")

print()
print("=== 持仓退出线(来自 sell-policy-state.json + 实时价) ===")
for code, p in pos.items():
    q = rt.get(code)
    if not q:
        continue
    eff = max([p["hard_stop"]] + ([p["profit_line"]] if p.get("protection_active") else []))
    gap = (q["price"] / eff - 1) * 100
    print(f"{p['name']} 现价{q['price']:.2f} 成本{p['cost']:.3f} 浮盈{(q['price']/p['cost']-1)*100:+.2f}% | "
          f"硬止损{p['hard_stop']:.2f} 保护{'ON P=%.2f' % p['profit_line'] if p.get('protection_active') else 'OFF'} | "
          f"距退出线{gap:+.2f}% | 峰值H {p['peak_h']:.2f}(H/成本={p['peak_h']/p['cost']:.4f}) "
          f"| 保护触发需H≥{p['cost']*1.08:.2f}")
