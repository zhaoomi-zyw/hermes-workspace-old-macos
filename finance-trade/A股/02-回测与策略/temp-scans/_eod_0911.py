# -*- coding: utf-8 -*-
import pandas as pd, numpy as np, os, datetime

# injected Tencent close data 09-11
data = {
"600988":("赤峰黄金",44.39,0.20,518463),
"000878":("云南铜业",17.18,-8.18,1117490),
"601138":("工业富联",64.07,0.25,758983),
"002156":("通富微电",58.00,-0.58,550131),
"600487":("亨通光电",65.24,2.08,1700286),
"600522":("中天科技",34.49,3.57,2655209),
"603380":("易德龙",32.26,-1.41,25608),
"600460":("士兰微",30.07,-0.56,616405),
"002396":("星网锐捷",34.59,-3.89,774579),
"000938":("紫光股份",32.84,-0.79,1233422),
"600219":("南山铝业",4.82,-3.60,1841199),
"600760":("中航沈飞",48.02,-1.19,147660),
}

def load(code):
    for f in os.listdir('data'):
        if f.startswith(code):
            df = pd.read_csv('data/'+f)
            df.columns = [c.lower() for c in df.columns]
            return df
    return None

print(f"{'名称':<6}{'现价':>7}{'涨跌%':>7}{'MA5':>7}{'MA10':>7}{'MA20':>7}{'MA60':>7}{'10日高':>8}{'回撤%':>7}{'DSA':>5}{'级':>3}{'60日位%':>8}{'量比':>6}")
for code,(name,px,chg,vol) in data.items():
    df = load(code)
    if df is None:
        print(name, "NO DATA"); continue
    df = df[['date','open','high','low','close','volume']].copy()
    df['date']=pd.to_datetime(df['date'])
    df=df.sort_values('date')
    # append today (use close px, approximate open/high/low = px for MA purposes)
    # force-replace today's bar with actual Tencent close (CSV may hold intraday snapshot)
    df=df[df['date']!=pd.Timestamp('2026-09-11')]
    today=pd.DataFrame([{'date':pd.Timestamp('2026-09-11'),'open':px,'high':px,'low':px,'close':px,'volume':vol*100}])
    df=pd.concat([df,today],ignore_index=True)
    c=df['close']
    ma5=c.rolling(5).mean().iloc[-1]; ma10=c.rolling(10).mean().iloc[-1]
    ma20=c.rolling(20).mean().iloc[-1]; ma60=c.rolling(60).mean().iloc[-1]
    hi10=df['high'].iloc[-11:-1].max()
    dd=(px-hi10)/hi10*100
    lo60=df['low'].iloc[-60:].min(); hi60=df['high'].iloc[-60:].max()
    pos=(px-lo60)/(hi60-lo60)*100 if hi60>lo60 else 0
    v=df['volume']; vma5=v.rolling(5).mean().iloc[-2] if len(v)>6 else v.mean()
    volr=v.iloc[-1]/vma5 if vma5>0 else 0
    # DSA 5 dim (per main file): 均线结构60 + 趋势排列15 + 60日位置15 + 量能10 + 20日趋势15
    s=0
    if px>ma5: s+=15
    if ma5>ma10: s+=10
    if ma10>ma20: s+=10
    if px>ma20: s+=10
    if px>ma60: s+=15
    if ma5>ma10>ma20: s+=15
    # position: lower better? per file "60日位置15" - use pos scoring (lower better to avoid chasing)
    s+= max(0,15*(1-pos/100))
    # 量能10: 缩量加分 (health) -> lower volr better
    if volr<0.8: s+=10
    elif volr<1.0: s+=7
    elif volr<1.2: s+=4
    # 20日趋势15
    c20=c.iloc[-21]
    if px>c20: s+=15
    elif px>c20*0.95: s+=8
    s=int(round(s))
    g='S' if s>=90 else 'A' if s>=80 else 'B' if s>=65 else 'C' if s>=50 else 'D'
    print(f"{name:<6}{px:>7.2f}{chg:>7.2f}{ma5:>7.2f}{ma10:>7.2f}{ma20:>7.2f}{ma60:>7.2f}{hi10:>8.2f}{dd:>7.1f}{s:>5}{g:>3}{pos:>8.1f}{volr:>6.2f}")
