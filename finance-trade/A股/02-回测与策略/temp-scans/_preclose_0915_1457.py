#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""收盘前检查 2026-09-15 14:57 —— 持仓退出线 + 自选12只实时DSA/四条件"""
import importlib.util, sys, json

p = "/Users/omi/.hermes/profiles/main/scripts/lowbuy-watch.py"
spec = importlib.util.spec_from_file_location("lbw", p)
m = importlib.util.module_from_spec(spec)
sys.modules["lbw"] = m
spec.loader.exec_module(m)

codes = list(m.WATCHLIST.keys())
q = m.fetch_realtime(codes)

st = json.load(open("/Users/omi/.hermes/state/sell-policy-state.json"))
pos = st["positions"]

print("=== 持仓退出线 ===")
for key, v in pos.items():
    code = key
    d = q.get(code)
    if not d:
        print(code, "NODATA"); continue
    price = d["price"]
    eff = v["hard_stop"]
    if v["protection_active"] and v["profit_line"] > 0:
        eff = max(v["hard_stop"], v["profit_line"])
    cost = v["cost"]
    pnl_pct = (price / cost - 1) * 100
    pnl = (price - cost) * v["total_qty"]
    dist = (price / eff - 1) * 100
    print(f"{v['name']}({code[2:]}) 现价{price:.2f} ({d['pct']:+.2f}%) 成本{cost:.3f} "
          f"浮盈亏{pnl_pct:+.2f}% ({pnl:+.0f}元) | 硬止损{v['hard_stop']:.2f} 保护线{v['profit_line']:.2f} "
          f"启用={v['protection_active']} 有效退出线{eff:.2f} 现价距退出线{dist:+.2f}% | peak_h={v['peak_h']}")

print()
print("=== 自选12只 ===")
print("name price pct MA5 MA10 MA20 MA60 dd10 dsa grade d5 d10 conds")
for c in codes:
    d = q.get(c)
    if not d:
        print(c, "NODATA"); continue
    k = m.fetch_kline(c, 90)
    if not k or len(k) < 65:
        print(c, "NOKLINE"); continue
    today = "2026-09-15"
    if k[-1]["date"] == today:
        k[-1]["close"] = d["price"]
        k[-1]["high"] = max(k[-1]["high"], d["high"])
        if d["low"] > 0:
            k[-1]["low"] = min(k[-1]["low"], d["low"])
    closes = [x['close'] for x in k]; highs = [x['high'] for x in k]
    lows = [x['low'] for x in k]; vols = [x['volume'] for x in k]
    price = d['price']
    ma5 = m.sma(closes, 5); ma10 = m.sma(closes, 10); ma20 = m.sma(closes, 20); ma60 = m.sma(closes, 60)
    h10 = max(highs[-10:]); dd = (h10 - price) / h10 * 100
    dsa = m.dsa_score(closes, highs, lows, vols)
    d5 = (price / ma5 - 1) * 100; d10 = (price / ma10 - 1) * 100
    c1 = dd >= 5.0; c2 = price > ma60; c3 = dsa is not None and dsa >= 65
    c4 = abs(d5) <= 2.0 or abs(d10) <= 2.0
    mark = "".join(["1" if x else "0" for x in (c1, c2, c3, c4)])
    held = " [持仓]" if c in m.HOLDINGS else ""
    print(f"{d['name']}{held} {price:.2f} {d['pct']:+.2f} {ma5:.2f} {ma10:.2f} {ma20:.2f} {ma60:.2f} "
          f"{dd:.1f} {dsa:.1f} {m.grade(dsa)} {d5:+.1f} {d10:+.1f} {mark}")

print()
print("MA5<MA10(空头):", [m.WATCHLIST[c] for c in codes if q.get(c)])
