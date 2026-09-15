"""盘中/竞价即时 DSA + 支撑压力 + 低吸四条件 (2026-09-11)
数据: data/{code}_{name}.csv (同花顺, 到最近收盘) + 腾讯实时价 appended as today's bar
"""
import urllib.request, json, csv, os, glob

DATA = "/Users/omi/workspace/quant-backtest/data"
codes = {
 "600988":"赤峰黄金","000878":"云南铜业","601138":"工业富联","002156":"通富微电",
 "600487":"亨通光电","600522":"中天科技","603380":"易德龙","600460":"士兰微",
 "002396":"星网锐捷","000938":"紫光股份","600219":"南山铝业","600760":"中航沈飞",
}
HOLD = {"600988": (200, 44.685, 42.00)}

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
                         pct=float(f[32]), vr=float(f[49]) if f[49] else 0.0,
                         t=f[30])
    return out

def load(code):
    g = glob.glob(os.path.join(DATA, f"{code}_*.csv"))
    if not g: return []
    rows = []
    with open(g[0]) as fh:
        r = csv.DictReader(fh)
        for d in r:
            try:
                rows.append(dict(date=str(d["date"])[:10], o=float(d["open"]), c=float(d["close"]),
                                 h=float(d["high"]), l=float(d["low"]), v=float(d["volume"])))
            except Exception:
                pass
    return rows

q = rt(list(codes.keys()))
print("=== 即时 DSA (日线到最近收盘 + 今日实时价) ===")
for s, name in codes.items():
    try:
        rows = load(s)
        info = q.get(c2(s), {})
        p = info.get("price")
        if not rows or not p:
            print(name, s, "无数据"); continue
        lastdate = rows[-1]["date"]
        if lastdate == "2026-09-11":
            rows = rows[:-1] + [dict(rows[-1], c=p, h=max(p, info.get("high", p)), l=min(p, info.get("low", p)))]
        else:
            rows = rows + [dict(date="2026-09-11", o=p, c=p, h=info.get("high", p), l=info.get("low", p), v=0)]
        c = [r["c"] for r in rows]; h = [r["h"] for r in rows]; v = [r["v"] for r in rows]
        ma5 = sum(c[-5:])/5; ma10 = sum(c[-10:])/10; ma20 = sum(c[-20:])/20; ma60 = sum(c[-60:])/60
        hi10 = max(h[-10:]); dd = (hi10 - p)/hi10*100
        lo60 = min(r["l"] for r in rows[-60:]); hi60 = max(r["h"] for r in rows[-60:])
        pos60 = (p-lo60)/(hi60-lo60)*100 if hi60>lo60 else 50
        # 支撑/压力 (昨日之前20日, shift1)
        sup20 = min(r["l"] for r in rows[-21:-1]); res20 = max(r["h"] for r in rows[-21:-1])
        # DSA v1
        sc = 0
        sc += 15*(p>ma5); sc += 10*(ma5>ma10); sc += 10*(ma10>ma20); sc += 10*(p>ma20); sc += 15*(p>ma60)
        sc += 15*(p>ma5 and ma5>ma10 and ma10>ma20 and ma20>ma60)
        sc += pos60*0.15
        vma20 = sum(v[-21:-1])/20
        vr = info.get("vr", 0)
        vratio = vr if vr and vr > 0 else 1.0
        sc += 10 if vratio<1 else (5 if vratio<1.5 else 2)
        c10 = c[-11]; c20 = c[-21]
        sc += 15 if p>c20 else (7 if p>c10 else 3)
        grade = "S" if sc>=90 else "A" if sc>=80 else "B" if sc>=65 else "C" if sc>=50 else "D"
        # 四条件
        k1 = dd >= 5
        k2 = p > ma60
        k3 = sc >= 65
        k4 = abs(p-ma5)/ma5*100 <= 2 or abs(p-ma10)/ma10*100 <= 2
        n_ok = sum([k1,k2,k3,k4])
        tag = ""
        if s in HOLD:
            sh, cost, stop = HOLD[s]
            tag = f" [持仓{sh}股@{cost} 浮盈{(p-cost)/cost*100:+.2f}% 止损{stop} 距止损{(p-stop)/stop*100:+.2f}% 浮盈线{cost*1.08:.2f}]"
        print(f"{name}({s}) {p:.2f} {info.get('pct',0):+.2f}% @{info.get('t','')} | MA5={ma5:.2f} MA10={ma10:.2f} MA20={ma20:.2f} MA60={ma60:.2f} 距MA60={(p-ma60)/ma60*100:+.1f}% | "
              f"10日高{hi10:.2f}回撤{dd:.1f}% 60位{pos60:.0f}% | 支撑20日{sup20:.2f} 压力20日{res20:.2f} | 量比{vr:.2f} | "
              f"DSA={sc:.0f}{grade} | 四条件{k1}{k2}{k3}{k4}={n_ok}/4{tag}")
    except Exception as e:
        print(name, s, "ERR", repr(e))
