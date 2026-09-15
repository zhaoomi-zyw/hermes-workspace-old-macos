import pandas as pd, numpy as np, urllib.request, datetime
DATA="/Users/omi/workspace/quant-backtest/data"
WATCH=[('600988','赤峰黄金'),('000878','云南铜业'),('601138','工业富联'),('002156','通富微电'),
       ('600487','亨通光电'),('600522','中天科技'),('603380','易德龙'),('600460','士兰微'),
       ('002396','星网锐捷'),('000938','紫光股份'),('600219','南山铝业'),('600760','中航沈飞')]
def tq(codes):
    syms=[('sh' if c.startswith('6') else 'sz')+c for c in codes]
    url="http://qt.gtimg.cn/q="+",".join(syms)
    req=urllib.request.Request(url,headers={"Referer":"http://finance.qq.com"})
    txt=urllib.request.urlopen(req,timeout=10).read().decode("gbk")
    out={}
    for line in txt.strip().split(";"):
        if "=" not in line: continue
        k,val=line.split("=",1); f=val.strip().strip('"').split("~")
        if len(f)<40: continue
        out[f[2]]=dict(name=f[1],px=float(f[3]),pc=float(f[4]),op=float(f[5]),t=f[30],hi=float(f[33]),lo=float(f[34]),vol=float(f[36])*100)
    return out
def load(code,name):
    df=pd.read_csv(f"{DATA}/{code}_{name}.csv"); df.columns=[c.lower() for c in df.columns]
    dc='date' if 'date' in df.columns else df.columns[0]
    df[dc]=pd.to_datetime(df[dc]); df=df.rename(columns={dc:'date'}).sort_values('date').reset_index(drop=True)
    return df
def dsa(df,price,vol_today,elapsed):
    c=df['close'].astype(float); v=df['volume'].astype(float)
    ma5,ma10,ma20,ma60=[c.rolling(n).mean().iloc[-1] for n in (5,10,20,60)]
    vm=v.rolling(20).mean().shift(1).iloc[-1]; est=vol_today/elapsed; s=0
    s+=15 if price>ma5 else 0; s+=10 if ma5>ma10 else 0; s+=10 if ma10>ma20 else 0
    s+=10 if price>ma20 else 0; s+=15 if price>ma60 else 0
    if price>ma5>ma10>ma20>ma60: s+=15
    lo60=df['low'].astype(float).rolling(60).min().iloc[-1]; hi60=df['high'].astype(float).rolling(60).max().iloc[-1]
    s+=(price-lo60)/(hi60-lo60)*15 if hi60>lo60 else 7.5
    s+=10 if est<vm else (5 if est<vm*1.5 else 2)
    prev=c.iloc[-1]; s+=15 if prev>c.iloc[-21] else (7 if prev>c.iloc[-11] else 3)
    g='S' if s>=90 else 'A' if s>=80 else 'B' if s>=65 else 'C' if s>=50 else 'D'
    return s,g,ma5,ma10,ma20,ma60,vm,est
now=datetime.datetime.now(); elapsed=0.4 if 11<=now.hour<12 else (0.5 if now.hour>=13 and now.hour<14 else 0.6)
q=tq([c for c,_ in WATCH])
print(f"【{now:%H:%M}】elapsed={elapsed}")
res={}
for code,name in WATCH:
    d=q.get(code)
    if not d: print(f"{name} NOQUOTE"); continue
    df=load(code,name); px=d['px']; s,g,ma5,ma10,ma20,ma60,vm,est=dsa(df,px,d['vol'],elapsed)
    hi10=max(df['high'].astype(float).iloc[-10:].max(),d['hi']); dd=(px/hi10-1)*100
    h60=df['high'].astype(float).rolling(60).max().iloc[-1]; l60=df['low'].astype(float).rolling(60).min().iloc[-1]
    pos=(px-l60)/(h60-l60)*100 if h60>l60 else 0
    res[name]=dict(px=px,pc=d['pc'],hi=d['hi'],lo=d['lo'],dsa=s,grade=g,ma5=ma5,ma10=ma10,ma60=ma60,dd=dd,pos=pos,vr=est/vm)
    print(f"{name:<8} 现{px:>7.2f} 涨{(px/d['pc']-1)*100:>+6.2f}% 日高{d['hi']:>6.2f} 日低{d['lo']:>6.2f} DSA{s:>3.0f}{g} MA5{ma5:>7.2f} MA10{ma10:>7.2f} MA60{ma60:>7.2f} 回撤{dd:>+6.1f}% 60位{pos:>4.0f}% 量比{est/vm:>4.2f} 距MA5{(px/ma5-1)*100:>+5.1f}% 距MA10{(px/ma10-1)*100:>+5.1f}%")
print("\n--- 四条件 ---")
for code,name in WATCH:
    r=res.get(name)
    if not r: continue
    c1=r['dd']<=-5; c2=r['px']>r['ma60']; c3=r['dsa']>=65
    near=min(abs(r['px']/r['ma5']-1),abs(r['px']/r['ma10']-1))<=0.02
    n_ok=sum([c1,c2,c3,near])
    daypos=(r['px']-r['lo'])/(r['hi']-r['lo'])*100 if r['hi']>r['lo'] else 50
    print(f"{name:<8} ①回撤{r['dd']:>+6.1f}%{'OK' if c1 else '×'} ②站MA60{'OK' if c2 else '×'} ③DSA{r['dsa']:.0f}{r['grade']}{'OK' if c3 else '×'} ④近MA5/10{'OK' if near else '×'} [{n_ok}/4] 日内位置{daypos:>3.0f}%")
print("\n--- 持仓 ---")
POS=[('600988','赤峰黄金',44.735,200,42.05),('002396','星网锐捷',35.880,100,33.73)]
for code,name,cost,sh,stop in POS:
    d=q.get(code)
    if not d: continue
    px=d['px']
    print(f"{name} {sh}股@{cost} 现{px:.2f} 浮盈{(px/cost-1)*100:+.2f}%({(px-cost)*sh:+.0f}元) 止损{stop} 距止损{(px/stop-1)*100:+.2f}% 日高{d['hi']:.2f} 日低{d['lo']:.2f}")
