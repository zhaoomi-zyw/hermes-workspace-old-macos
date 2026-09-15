import pandas as pd, os
D="/Users/omi/workspace/quant-backtest/data"
TODAY="2026-09-11"
live = {
 "600988":("赤峰黄金",43.02,-2.89,43.49,42.32),"000878":("云南铜业",16.99,-9.19,17.70,16.84),
 "601138":("工业富联",63.40,-0.80,64.49,62.50),"002156":("通富微电",56.55,-3.07,57.65,56.36),
 "600487":("亨通光电",62.91,-1.56,65.06,61.80),"600522":("中天科技",32.96,-1.02,34.15,32.66),
 "603380":("易德龙",31.79,-2.84,32.65,31.74),"600460":("士兰微",29.17,-3.54,29.96,29.05),
 "002396":("星网锐捷",33.62,-6.59,35.86,33.50),"000938":("紫光股份",32.11,-2.99,33.18,32.01),
 "600219":("南山铝业",4.80,-4.00,4.91,4.76),"600760":("中航沈飞",48.08,-1.07,48.90,47.63),
}
FRAC=0.39  # 11:03 elapsed fraction of full 4h session
for code,(name,p,pct,hi,lo) in live.items():
    df=pd.read_csv(os.path.join(D,f"{code}_{name}.csv"))
    df["date"]=df["date"].astype(str)
    if df.iloc[-1]["date"]==TODAY:
        df=df.iloc[:-1]
    c=df["close"].tolist()+[p]; h=df["high"].tolist()+[hi]
    l=df["low"].tolist()+[lo]; v=df["volume"].tolist()
    vfull=v[-1]/FRAC
    ma5=sum(c[-5:])/5;ma10=sum(c[-10:])/10;ma20=sum(c[-20:])/20;ma60=sum(c[-60:])/60
    hi10=max(h[-10:]); lo60=min(l[-60:]); hi60=max(h[-60:])
    dd=(p-hi10)/hi10*100
    d5=(p-ma5)/ma5*100; d10=(p-ma10)/ma10*100; d60=(p-ma60)/ma60*100
    sc=0
    sc+=15*(p>ma5); sc+=10*(ma5>ma10); sc+=10*(ma10>ma20); sc+=10*(p>ma20); sc+=15*(p>ma60)
    sc+=15*(p>ma5 and ma5>ma10 and ma10>ma20 and ma20>ma60)
    sc+=(p-lo60)/(hi60-lo60)*15 if hi60>lo60 else 7.5
    vma20=sum(v[-21:-1])/20
    vr=vfull/vma20 if vma20 else 1
    sc+= 10 if vr<1 else (5 if vr<1.5 else 2)
    c10=c[-11]; c20=c[-21]
    sc+= 15 if p>c20 else (7 if p>c10 else 3)
    grade="S" if sc>=90 else "A" if sc>=80 else "B" if sc>=65 else "C" if sc>=50 else "D"
    hit=[]
    if dd<=-5: hit.append("回撤≥5%")
    if p>ma60: hit.append("站上MA60")
    if sc>=65: hit.append("DSA A/B")
    if abs(d5)<=2 or abs(d10)<=2: hit.append("近MA5/10")
    print(f"{name}({code}) {p:.2f} {pct:+.2f}% | MA5={ma5:.2f} MA10={ma10:.2f} MA20={ma20:.2f} MA60={ma60:.2f} | 距MA5={d5:+.1f}% 距MA10={d10:+.1f}% 距MA60={d60:+.1f}% | 10日高{hi10:.2f} 回撤{dd:+.1f}% | 量比(折算){vr:.2f} | DSA={sc:.0f}{grade} | 低吸:{'/'.join(hit) if hit else '无'} ({len(hit)}/4)")
