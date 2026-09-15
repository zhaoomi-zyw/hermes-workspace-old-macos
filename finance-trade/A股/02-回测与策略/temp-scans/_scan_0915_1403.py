import importlib.util, sys
p = "/Users/omi/.hermes/profiles/main/scripts/lowbuy-watch.py"
spec = importlib.util.spec_from_file_location("lbw", p)
m = importlib.util.module_from_spec(spec)
sys.modules["lbw"] = m
spec.loader.exec_module(m)

codes = list(m.WATCHLIST.keys())
q = m.fetch_realtime(codes)
print("name price pct MA5 MA10 MA60 dd10 dsa grade dist5 dist10")
for c in codes:
    d = q.get(c)
    if not d:
        print(c, "NODATA"); continue
    k = m.fetch_kline(c, 90)
    if not k:
        print(c, "NOKLINE"); continue
    closes = [x['close'] for x in k]; highs = [x['high'] for x in k]
    lows = [x['low'] for x in k]; vols = [x['volume'] for x in k]
    price = d['price']
    ma5 = m.sma(closes, 5); ma10 = m.sma(closes, 10); ma60 = m.sma(closes, 60)
    h10 = max(highs[-10:]); dd = (h10 - price) / h10 * 100
    dsa = m.dsa_score(closes, highs, lows, vols)
    print(f"{d['name']} {price:.2f} {d['pct']:+.2f} {ma5:.2f} {ma10:.2f} {ma60:.2f} "
          f"{dd:.1f} {dsa:.0f} {m.grade(dsa)} {(price-ma5)/ma5*100:+.1f}% {(price-ma10)/ma10*100:+.1f}%")
