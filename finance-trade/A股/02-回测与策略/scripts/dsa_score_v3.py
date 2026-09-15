"""
DSA 评分 v3 —— 只保留 IC 验证有效的成分 (2026-09-08)
===================================================
v2 成分诊断发现真正有效的只有3类:
  mom 温和动量   3日IC +0.010 (9/11股正)
  over 透支惩罚  +0.014 (过滤连涨过热/涨停/暴量)
  vol 温和量能   +0.012 (放量有弱正, 非缩量)
无效/负贡献的已砍: pos位置(-0.014) fresh新鲜突破(-0.009)
  trend站MA60(-0.003) struct骨架(-0.006)

v3 设计 (满分100, 简洁):
  ① 动量 40分  —— 温和动量reward, 负动量/暴涨逐级降
  ② 透支惩罚(减) —— 扣到 -40: 过滤涨停/单日暴涨/5日暴涨/暴量/加速末端
  ③ 温和量能 20分 —— 放量(1~2x)reward
  ④ 趋势方向 20分 —— 仅"站上MA60且MA20向上"给(趋势确认, 权重小防拖累)
  ⑤ 位置 0 —— 不用(已证无效/反直觉)
"""
from __future__ import annotations
import glob
import numpy as np, pandas as pd

DATA="/Users/omi/workspace/quant-backtest/data"
def _rankdata(a):
    a=np.asarray(a,float);order=np.argsort(a,kind="mergesort");r=np.empty(len(a),float);i=0
    while i<len(a):
        j=i
        while j+1<len(a) and a[order[j+1]]==a[order[i]]:j+=1
        r[order[i:j+1]]=(i+j)/2.0+1;i=j+1
    return r
def spearman(a,b):
    a=np.asarray(a,float).ravel();b=np.asarray(b,float).ravel()
    if len(a)<10:return 0.0
    ra,rb=_rankdata(a),_rankdata(b);ma,mb=ra.mean(),rb.mean()
    cov=np.sum((ra-ma)*(rb-mb));va=np.sqrt(np.sum((ra-ma)**2)*np.sum((rb-mb)**2))
    return cov/va if va>0 else 0.0
def load(c):
    fs=glob.glob(f"{DATA}/{c}*.csv")
    if not fs:return None
    df=pd.read_csv(fs[0]);df["date"]=pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)
def _prep(df):
    c=df["close"].astype(float);h=df["high"].astype(float);l=df["low"].astype(float);v=df["volume"].astype(float);o=df["open"].astype(float)
    df=df.copy()
    for k in [5,10,20,60]: df[f"ma{k}"]=c.rolling(k).mean()
    df["vm20"]=v.rolling(20).mean()
    df["ret1"]=c.pct_change()*100;df["ret3"]=c.pct_change(3)*100;df["ret5"]=c.pct_change(5)*100
    df["ret10"]=c.pct_change(10)*100;df["ret20"]=c.pct_change(20)*100
    df["vol_ratio"]=v/df["vm20"]
    df["hi5"]=c.rolling(5).max();df["hi3"]=c.rolling(3).max()
    df["fwd1"]=(c.shift(-1)/o.shift(-1)-1)*100
    df["fwd3"]=(c.shift(-3)/o.shift(-1)-1)*100
    df["fwd5"]=(c.shift(-5)/o.shift(-1)-1)*100
    return df

def score_v3(df):
    c=df["close"];ret1=df["ret1"].fillna(0);ret3=df["ret3"].fillna(0)
    ret5=df["ret5"].fillna(0);ret10=df["ret10"].fillna(0)
    vr=df["vol_ratio"].fillna(1); ma20=df["ma20"]; ma60=df["ma60"]
    s=pd.Series(0.0,index=df.index)
    # ① 动量 40 (温和reward, 阶梯降)
    mom=pd.Series(0.0,index=df.index)
    mom+=40*((ret10>0)&(ret10<=6))            # 10日涨0-6%: 健康满
    mom+=25*((ret10>6)&(ret10<=10))           # 6-10: 较强
    mom+=12*((ret10>10)&(ret10<=15))          # 10-15: 减弱
    mom+=4 *((ret10>15)&(ret10<=25))          # 15-25: 透支前兆
    mom+=0 *(ret10>25)                         # >25 过热
    mom+=12*((ret10>-4)&(ret10<=0))           # 小幅回踩蓄势
    mom+=0 *(ret10<=-4)                        # 弱
    s+=mom
    # ② 透支惩罚 (减最多40)
    over=pd.Series(0.0,index=df.index)
    over+=12*((ret1>9.5)|(ret3>15))            # 涨停/3日暴涨
    over+=12*((ret5>12)|(ret10>25))            # 5日暴涨/10日过热
    over+=10*((vr>2.5))                        # 暴量
    over+=6 *((ret5>8)&(ret10>12))             # 加速末端(短期追过快)
    s-=over
    # ③ 温和量能 20 (放量reward — 实证弱正)
    s+=np.where((vr>=1.0)&(vr<=2.0),20,np.where((vr>=0.8)&(vr<1.0),12,np.where((vr>2.0)&(vr<=3.0),10,4)))
    # ④ 趋势方向 20: 站上MA60 且 MA20向上 (小权重趋势确认)
    ma20_up=ma20>ma20.shift(5)
    s+=((c>ma60)&ma20_up)*20
    return s.clip(lower=0)

def grade(s):
    return pd.Series(np.where(s>=75,"S",np.where(s>=60,"A",np.where(s>=45,"B",np.where(s>=30,"C","D")))),index=s.index)

CODES=["601138","002156","600487","603380","600988","600460","600522","002396","600219","000878","600760"]
HK={"fwd1":"1日","fwd3":"3日","fwd5":"5日"};HV=list(HK)
i1={h:[] for h in HV};i2={h:[] for h in HV};i3={h:[] for h in HV}
t2={h:[] for h in HV};t3={h:[] for h in HV}
for code in CODES:
    df=load(code)
    if df is None or len(df)<70:continue
    d=_prep(df)
    # v1 复用 backtest 逻辑
    c=d["close"];ma5=d["ma5"];ma10=d["ma10"];ma20=d["ma20"];ma60=d["ma60"]
    vm=d["vm20"].shift(1);lv=d["volume"]
    s1=pd.Series(0.0,index=d.index);s1+=(c>ma5)*15;s1+=(ma5>ma10)*10;s1+=(ma10>ma20)*10;s1+=(c>ma20)*10;s1+=(c>ma60)*15
    perf=(c>ma5)&(ma5>ma10)&(ma10>ma20)&(ma20>ma60);s1+=perf*15
    rng=d["high"].rolling(60).max()-d["low"].rolling(60).min();s1+=(((c-d["low"].rolling(60).min())/rng)*15).fillna(7.5)
    vs=np.where(lv<vm,10,np.where(lv<vm*1.5,5,2));s1+=pd.Series(vs,index=d.index)
    s1+=np.where(c>c.shift(20),15,np.where(c>c.shift(10),7,3))
    s3=score_v3(d)
    for h in HV:
        vv=(d.index>=60)&~np.isnan(s1)&~np.isnan(s3)&~np.isnan(d[h])
        if vv.sum()<30:continue
        a=s1[vv].values;b=s3[vv].values;y=d[h][vv].values
        i1[h].append(spearman(a,y));i3[h].append(spearman(b,y))
        t3[h].append(y[b>=np.percentile(b,66.67)].mean())

print("="*72)
print("v1(旧) vs v3(精简重构) — IC + 顶1/3未来收益")
print("="*72)
print(f"{'收益':<5}{'v1均IC':>9}{'v3均IC':>9}{'v1顶1/3':>11}{'v3顶1/3':>11}")
for h in HV:
    print(f"{HK[h]:<5}{np.mean(i1[h]):>+9.3f}{np.mean(i3[h]):>+9.3f}{'':>11}{np.mean(t3[h]):>+10.2f}%")
print("\n逐股 3日IC (v3>v1=提升):")
impr=0
for code in CODES:
    df=load(code)
    if df is None or len(df)<70:continue
    d=_prep(df)
    c=d["close"];ma5=d["ma5"];ma10=d["ma10"];ma20=d["ma20"];ma60=d["ma60"]
    vm=d["vm20"].shift(1);lv=d["volume"]
    s1=pd.Series(0.0,index=d.index);s1+=(c>ma5)*15;s1+=(ma5>ma10)*10;s1+=(ma10>ma20)*10;s1+=(c>ma20)*10;s1+=(c>ma60)*15
    perf=(c>ma5)&(ma5>ma10)&(ma10>ma20)&(ma20>ma60);s1+=perf*15
    rng=d["high"].rolling(60).max()-d["low"].rolling(60).min();s1+=(((c-d["low"].rolling(60).min())/rng)*15).fillna(7.5)
    vs=np.where(lv<vm,10,np.where(lv<vm*1.5,5,2));s1+=pd.Series(vs,index=d.index)
    s1+=np.where(c>c.shift(20),15,np.where(c>c.shift(10),7,3))
    s3=score_v3(d)
    vv=(d.index>=60)&~np.isnan(s1)&~np.isnan(s3)&~np.isnan(d["fwd3"])
    if vv.sum()<30:continue
    a=s1[vv].values;b=s3[vv].values;y=d["fwd3"][vv].values
    ic1=spearman(a,y);ic3=spearman(b,y)
    mark="✓提升" if ic3>ic1 else "✗下降"
    if ic3>ic1:impr+=1
    print(f"  {code}: v1 {ic1:+.3f} → v3 {ic3:+.3f} {mark}")
print(f"\n3日IC v3提升的股票: {impr}/{len(CODES)}")
