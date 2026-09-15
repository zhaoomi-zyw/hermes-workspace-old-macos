import urllib.request, json

codes = {
 "600988":"赤峰黄金","000878":"云南铜业","601138":"工业富联","002156":"通富微电",
 "600487":"亨通光电","600522":"中天科技","603380":"易德龙","600460":"士兰微",
 "002396":"星网锐捷","000938":"紫光股份","600219":"南山铝业","600760":"中航沈飞",
}

def code2(s):
    return ("sh" if s.startswith("6") else "sz") + s

def kline(s, n=70):
    u = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code2(s)},day,,,{n},qfq"
    req = urllib.request.Request(u, headers={"Referer":"http://finance.qq.com"})
    j = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
    d = j.get("data", {}).get(code2(s), {})
    return d.get("qfqday") or d.get("day") or []

for s, name in codes.items():
    try:
        rows = kline(s)
        closes = [float(r[2]) for r in rows]
        highs = [float(r[3]) for r in rows]
        last = closes[-1]
        ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else None
        hi10 = max(highs[-10:])
        dd = (last - hi10) / hi10 * 100
        d60 = (last - ma60) / ma60 * 100 if ma60 else float('nan')
        print(f"{name}({s}) 收{last:.2f} MA60={ma60:.2f} 距MA60={d60:+.1f}% 10日高{hi10:.2f} 回撤={dd:.1f}% 最近日={rows[-1][0]}")
    except Exception as e:
        print(name, s, "ERR", e)
