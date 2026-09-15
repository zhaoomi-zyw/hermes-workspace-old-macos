"""盘中实时 DSA + 低吸条件检查 (2026-09-11 10:03)"""
import urllib.request, json

codes = {
 "600988":"赤峰黄金","000878":"云南铜业","601138":"工业富联","002156":"通富微电",
 "600487":"亨通光电","600522":"中天科技","603380":"易德龙","600460":"士兰微",
 "002396":"星网锐捷","000938":"紫光股份","600219":"南山铝业","600760":"中航沈飞",
}
HOLD = {"600988": (100, 44.96, 42.26), "002396": (100, 35.96, 33.80)}
TODAY = "2026-09-11"

def c2(s): return ("sh" if s.startswith("6") else "sz") + s

def rt(codelist):
    url = "http://qt.gtimg.cn/q=" + ",".join(c2(s) for s in codelist)
    req = urllib.request.Request(url, headers={"Referer":"http://finance.qq.com"})
    txt = urllib.request.urlopen(req, timeout=10).read().decode("gbk")
    out = {}
    for line in txt.strip().split("\n"):
        if "=" not in line: continue
        head, val = line.split("=", 1)
        code = head.replace("v_", "")
        f = val.strip('";').split("~")
        out[code] = dict(name=f[1], price=float(f[3]), prev=float(f[4]),
                         high=float(f[33]), low=float(f[34]), vol=float(f[36]),
                         pct=float(f[32]), vr=float(f[49]) if f[49] else 0.0)
    return out

def kline(s, n=90):
    u = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={c2(s)},day,,,{n},qfq"
    req = urllib.request.Request(u, headers={"Referer":"http://finance.qq.com"})
    j = json.loads(urllib.request.urlopen(req, timeout=15).read().decode("utf-8"))
    d = j.get("data", {}).get(c2(s), {})
    return d.get("qfqday") or d.get("day") or []

q = rt(list(codes.keys()))
print("=== 盘中实时 DSA (10:03, 价含当日实时) ===")
for s, name in codes.items():
    try:
        rows = kline(s)
        closes = [float(r[2]) for r in rows]
        highs = [float(r[3]) for r in rows]
        lows = [float(r[4]) for r in rows]
        vols = [float(r[5]) for r in rows]
        info = q.get(c2(s), {})
        p = info.get("price", closes[-1])
        if rows[-1][0] != TODAY:
            c = closes + [p]; h = highs + [info.get("high", p)]
        else:
            c = closes[:-1] + [p]; h = highs[:-1] + [info.get("high", p)]
        ma5 = sum(c[-5:])/5; ma10 = sum(c[-10:])/10; ma20 = sum(c[-20:])/20; ma60 = sum(c[-60:])/60
        hi10 = max(h[-10:])
        dd = (p - hi10)/hi10*100
        d60 = (p - ma60)/ma60*100
        sc = 0
        sc += 15*(p>ma5); sc += 10*(ma5>ma10); sc += 10*(ma10>ma20); sc += 10*(p>ma20); sc += 15*(p>ma60)
        sc += 15*(p>ma5 and ma5>ma10 and ma10>ma20 and ma20>ma60)
        lo60 = min(lows[-60:]); hi60 = max(highs[-60:])
        sc += (p-lo60)/(hi60-lo60)*15 if hi60>lo60 else 7.5
        vma20 = sum(vols[-21:-1])/20
        vtoday = info.get("vol", 0)
        vratio = vtoday/vma20/0.85 if vma20 else 1   # 10:03约1小时/4小时≈0.25; 已含大致折算
        sc += 10 if vratio<1 else (5 if vratio<1.5 else 2)
        c10 = c[-11]; c20 = c[-21]
        sc += 15 if p>c20 else (7 if p>c10 else 3)
        grade = "S" if sc>=80 else "A" if sc>=65 else "B" if sc>=50 else "C" if sc>=35 else "D"
        tag = ""
        if s in HOLD:
            sh, cost, stop = HOLD[s]
            pl = (p-cost)/cost*100
            dist = (p-stop)/stop*100
            tag = f" | 持仓{sh}股@{cost} 浮盈{pl:+.1f}% 距止损{dist:+.1f}%"
        print(f"{name}({s}) {p:.2f} {info.get('pct',0):+.2f}% | MA5={ma5:.2f} MA10={ma10:.2f} MA60={ma60:.2f} 距MA60={d60:+.1f}% | "
              f"10日高{hi10:.2f} 回撤{dd:.1f}% | 量比{info.get('vr',0):.2f} | DSA={sc:.0f} {grade}{tag}")
    except Exception as e:
        print(name, s, "ERR", e)
