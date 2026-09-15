"""盘中实时DSA监控 (12只自选 + 2持仓) — 自动拉腾讯实时行情"""
import pandas as pd, numpy as np, urllib.request, sys, datetime

DATA = "/Users/omi/workspace/quant-backtest/data"
WATCH = [('600988','赤峰黄金'),('000878','云南铜业'),('601138','工业富联'),('002156','通富微电'),
         ('600487','亨通光电'),('600522','中天科技'),('603380','易德龙'),('600460','士兰微'),
         ('002396','星网锐捷'),('000938','紫光股份'),('600219','南山铝业'),('600760','中航沈飞')]

def tq(codes):
    syms = [('sh' if c.startswith('6') else 'sz') + c for c in codes]
    url = "http://qt.gtimg.cn/q=" + ",".join(syms)
    req = urllib.request.Request(url, headers={"Referer": "http://finance.qq.com"})
    txt = urllib.request.urlopen(req, timeout=10).read().decode("gbk")
    out = {}
    for line in txt.strip().split(";"):
        if "=" not in line: continue
        key, val = line.split("=", 1)
        f = val.strip().strip('"').split("~")
        if len(f) < 40: continue
        out[f[2]] = dict(name=f[1], px=float(f[3]), pc=float(f[4]), op=float(f[5]),
                         t=f[30], hi=float(f[33]), lo=float(f[34]), vol=float(f[36]) * 100)  # 手→股(CSV单位为股)
    return out

def load(code, name):
    df = pd.read_csv(f"{DATA}/{code}_{name}.csv")
    df.columns = [c.lower() for c in df.columns]
    dc = 'date' if 'date' in df.columns else df.columns[0]
    df[dc] = pd.to_datetime(df[dc])
    df = df.rename(columns={dc: 'date'}).sort_values('date').reset_index(drop=True)
    return df

def dsa(df, price, vol_today, elapsed):
    c = df['close'].astype(float); v = df['volume'].astype(float)
    ma5, ma10, ma20, ma60 = [c.rolling(n).mean().iloc[-1] for n in (5,10,20,60)]
    vm = v.rolling(20).mean().shift(1).iloc[-1]
    est = vol_today / elapsed
    s = 0
    s += 15 if price > ma5 else 0
    s += 10 if ma5 > ma10 else 0
    s += 10 if ma10 > ma20 else 0
    s += 10 if price > ma20 else 0
    s += 15 if price > ma60 else 0
    if price > ma5 > ma10 > ma20 > ma60: s += 15
    lo60 = df['low'].astype(float).rolling(60).min().iloc[-1]
    hi60 = df['high'].astype(float).rolling(60).max().iloc[-1]
    s += (price-lo60)/(hi60-lo60)*15 if hi60 > lo60 else 7.5
    s += 10 if est < vm else (5 if est < vm*1.5 else 2)
    prev = c.iloc[-1]
    s += 15 if prev > c.iloc[-21] else (7 if prev > c.iloc[-11] else 3)
    g = 'S' if s>=90 else 'A' if s>=80 else 'B' if s>=65 else 'C' if s>=50 else 'D'
    return s, g, ma5, ma10, ma20, ma60, vm, est

now = datetime.datetime.now()
elapsed = 0.5
if now.hour >= 14: elapsed = 0.75
if now.hour >= 15: elapsed = 1.0
if now.hour < 12 and now.hour >= 11: elapsed = 0.4
if now.hour < 11: elapsed = max(0.05, ((now.hour + now.minute/60) - 9.5) / 4.0)

q = tq([c for c, _ in WATCH])
print(f"【实时 {now:%m-%d %H:%M}】已交易比例≈{elapsed:.2f}")
hdr = f"{'股票':<9}{'现价':>7}{'涨跌%':>7}{'DSA':>5}{'级':>3}{'MA5':>8}{'MA10':>8}{'MA60':>8}{'距MA60':>7}{'距MA5':>7}{'10日回撤':>8}{'60位':>6}{'量比':>6}{'距20低':>7}"
print(hdr)
res = {}
for code, name in WATCH:
    d = q.get(code)
    if not d: print(f"{name:<9} NOQUOTE"); continue
    try:
        df = load(code, name)
        px = d['px']
        s, g, ma5, ma10, ma20, ma60, vm, est = dsa(df, px, d['vol'], elapsed)
        hi10 = max(df['high'].astype(float).iloc[-10:].max(), d['hi'])
        dd = (px/hi10 - 1)*100
        h60 = df['high'].astype(float).rolling(60).max().iloc[-1]
        l60 = df['low'].astype(float).rolling(60).min().iloc[-1]
        pos = (px-l60)/(h60-l60)*100 if h60 > l60 else 0
        sup20 = df['low'].astype(float).rolling(20).min().shift(1).iloc[-1]
        res[name] = dict(px=px, pc=d['pc'], dsa=s, grade=g, ma5=ma5, ma10=ma10, ma60=ma60,
                         dd=dd, pos=pos, l60=l60, sup20=sup20)
        print(f"{name:<9}{px:>7.2f}{(px/d['pc']-1)*100:>7.2f}{s:>5.0f}{g:>3}{ma5:>8.2f}{ma10:>8.2f}{ma60:>8.2f}"
              f"{(px/ma60-1)*100:>7.1f}{(px/ma5-1)*100:>7.1f}{dd:>8.1f}{pos:>6.0f}{est/vm:>6.2f}{(px/sup20-1)*100:>7.1f}")
    except Exception as e:
        print(f"{name:<9} FAIL {e}")

print("\n--- 左侧低吸四条件检查 (回撤≥5% + 站上MA60 + DSA≥B + 近MA5/MA10±2%) ---")
for code, name in WATCH:
    r = res.get(name)
    if not r: continue
    c1 = r['dd'] <= -5
    c2 = r['px'] > r['ma60']
    c3 = r['dsa'] >= 65
    near = min(abs(r['px']/r['ma5']-1), abs(r['px']/r['ma10']-1)) <= 0.02
    flag = "✅全满足" if (c1 and c2 and c3 and near) else ("近买点" if (c1 and c2 and c3) else "")
    print(f"{name:<9} 回撤{r['dd']:>6.1f}% {'OK' if c1 else '×':<3}站MA60 {'OK' if c2 else '×':<3}DSA {r['dsa']:.0f}{r['grade']} {'OK' if c3 else '×':<3}近MA5/10 {'OK' if near else '×':<3}{flag}")

print("\n--- 持仓 ---")
for code, name, cost, sh, stop in [('600988','赤峰黄金',44.96,100,41.81), ('000878','云南铜业',18.31,200,17.02)]:
    d = q.get(code)
    if not d: continue
    px = d['px']
    print(f"{name} {sh}股@{cost} 现{px:.2f} 盈亏{(px/cost-1)*100:+.2f}%({(px-cost)*sh:+.0f}元) 止损{stop} 距止损{(px/stop-1)*100:+.2f}%")
