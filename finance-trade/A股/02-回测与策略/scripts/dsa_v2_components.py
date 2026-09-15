"""诊断 v2 各子成分独立IC, 判断重构哪些成分真正有效, 哪些可精简."""
import glob
import numpy as np, pandas as pd

# 独立实现, 不 import dsa_score_v2 (避免触发其顶层验证代码)
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
    df=df.copy();df["ma5"]=c.rolling(5).mean();df["ma10"]=c.rolling(10).mean();df["ma20"]=c.rolling(20).mean();df["ma60"]=c.rolling(60).mean()
    df["vm20"]=v.rolling(20).mean();df["ret1"]=c.pct_change()*100;df["ret5"]=c.pct_change(5)*100;df["ret10"]=c.pct_change(10)*100
    df["vol_ratio"]=v/df["vm20"];df["pos60"]=(c-df["low"].rolling(60).min())/(df["high"].rolling(60).max()-df["low"].rolling(60).min())
    f1=(c.shift(-1)/o.shift(-1)-1)*100;f3=(c.shift(-3)/o.shift(-1)-1)*100;f5=(c.shift(-5)/o.shift(-1)-1)*100
    df["fwd1"]=f1;df["fwd3"]=f3;df["fwd5"]=f5
    return df

CODES=["601138","002156","600487","603380","600988","600460","600522","002396","600219","000878","600760"]

def comps(df):
    c=df["close"]; ma5=df["ma5"];ma10=df["ma10"];ma20=df["ma20"];ma60=df["ma60"]
    ret1=df["ret1"].fillna(0);ret5=df["ret5"].fillna(0);ret10=df["ret10"].fillna(0)
    vr=df["vol_ratio"].fillna(1); pos60=df["pos60"].fillna(0.5)
    hi20=c.rolling(20).max()
    R={}
    mom=pd.Series(0.0,index=df.index)
    mom+=30*((ret10>0)&(ret10<=8));mom+=15*((ret10>8)&(ret10<=12));mom+=5*((ret10>12)&(ret10<=20));mom+=8*((ret10>-3)&(ret10<=0))
    R["mom_动量30"]=mom
    R["trend_站MA60_20"]=(c>ma60)*20
    struct=pd.Series(0.0,index=df.index);struct+=(ma5>ma20)*5;struct+=(c>ma10)*5;struct+=((ma10>ma20)&(ma20>ma60))*5
    R["struct_骨架15"]=struct
    R["pos_位置10"]=pos60*10
    near=((hi20-c)/hi20*100<=3).astype(float)
    R["fresh_新鲜突破10"]=near*10
    over=pd.Series(0.0,index=df.index);over+=10*((ret5>12)|(ret1>6)|(ret1>9.5));over+=10*((vr>2.5)|(ret10>25))
    R["over_透支-20"]=-over
    R["vol_温和量10"]=pd.Series(np.where((vr>=1.0)&(vr<=2.0),10,np.where((vr>2.0)&(vr<=3.0),6,2)),index=df.index)
    R["total_v2"]=sum(R.values()).clip(lower=0)
    return R

print("v2 子成分独立IC (3日/5日, 跨11股均) — 看哪些成分真贡献")
print(f"{'成分':<20}{'3日IC':>8}{'5日IC':>8}{'IC>0(3日)':>12}")
res={k:[] for k in ["mom_动量30","trend_站MA60_20","struct_骨架15","pos_位置10","fresh_新鲜突破10","over_透支-20","vol_温和量10","total_v2"]}
res5={k:[] for k in res}
for code in CODES:
    df=load(code)
    if df is None or len(df)<70:continue
    d=_prep(df); C=comps(d)
    for k in res:
        vv=(d.index>=60)&~np.isnan(C[k])&~np.isnan(d["fwd3"])&~np.isnan(d["fwd5"])
        if vv.sum()<30:continue
        res[k].append(spearman(C[k][vv].values,d["fwd3"][vv].values))
        res5[k].append(spearman(C[k][vv].values,d["fwd5"][vv].values))
for k in res:
    a=np.array(res[k]);a5=np.array(res5[k])
    print(f"{k:<20}{np.mean(a):>+8.3f}{np.mean(a5):>+8.3f}{int((a>0).sum()):>8}股/{len(a)}")
