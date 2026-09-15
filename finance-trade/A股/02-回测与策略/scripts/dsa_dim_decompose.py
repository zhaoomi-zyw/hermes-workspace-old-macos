"""
DSA 评分子项拆解推演
==================
把 ①均线结构65分 拆成5个子项、把量能机制单独验证，逐个测对未来1/3/5日收益的IC，
回答推演问题：
  - 均线结构里到底哪几项有用/哪几项是噪音?
  - "量能反向"是数据真实还是我算法造出来的?
  - 位置维度的高分(接近60日高)到底该不该当坏事?
"""
import glob, os
import numpy as np, pandas as pd
DATA="/Users/omi/workspace/quant-backtest/data"
CODES=["601138","002156","600487","603380","600988","600460","600522","002396","600219","000878","600760"]

def _rankdata(a):
    a=np.asarray(a,float); order=np.argsort(a,kind="mergesort"); ranks=np.empty(len(a),float); i=0
    while i<len(a):
        j=i
        while j+1<len(a) and a[order[j+1]]==a[order[i]]: j+=1
        ranks[order[i:j+1]]=(i+j)/2.0+1; i=j+1
    return ranks
def spearman(a,b):
    a=np.asarray(a,float).ravel(); b=np.asarray(b,float).ravel()
    if len(a)<10: return 0.0
    ra,rb=_rankdata(a),_rankdata(b); ma,mb=ra.mean(),rb.mean()
    cov=np.sum((ra-ma)*(rb-mb)); va=np.sqrt(np.sum((ra-ma)**2)*np.sum((rb-mb)**2))
    return cov/va if va>0 else 0.0

def load(c):
    fs=glob.glob(f"{DATA}/{c}*.csv")
    if not fs: return None
    df=pd.read_csv(fs[0]); df["date"]=pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)

def feats(df):
    c=df["close"].values.astype(float); h=df["high"].values.astype(float)
    l=df["low"].values.astype(float); v=df["volume"].values.astype(float); o=df["open"].values.astype(float)
    n=len(c)
    def ma(k,i): return c[i-k+1:i+1].mean() if i>=k-1 else np.nan
    F={k:[] for k in ["gt_ma5","ma5gt10","ma10gt20","gt_ma60","perfect","pos_pct","ret20","vol_ratio","accel","ret5","ret10","fwd1","fwd3","fwd5"]}
    for i in range(60,n-5):
        c5,c10,c20,c60=ma(5,i),ma(10,i),ma(20,i),ma(60,i)
        lo60,hi60=l[i-59:i+1].min(),h[i-59:i+1].max()
        F["gt_ma5"].append(1.0 if c[i]>c5 else 0.0)
        F["ma5gt10"].append(1.0 if c5>c10 else 0.0)
        F["ma10gt20"].append(1.0 if c10>c20 else 0.0)
        F["gt_ma60"].append(1.0 if c[i]>c60 else 0.0)
        F["perfect"].append(1.0 if c[i]>c5>c10>c20>c60 else 0.0)
        F["pos_pct"].append((c[i]-lo60)/(hi60-lo60) if hi60>lo60 else 0.5)
        F["ret20"].append((c[i]/c[i-20]-1)*100 if i>=20 else np.nan)
        F["vol_ratio"].append(v[i]/(v[i-59:i+1].mean()) if i>=59 else np.nan)
        # 动量: 过去5/10日涨幅
        F["ret5"].append((c[i]/c[i-5]-1)*100 if i>=5 else np.nan)
        F["ret10"].append((c[i]/c[i-10]-1)*100 if i>=10 else np.nan)
        # 加速: 最近5日 vs 前一个5日
        F["accel"].append((c[i]/c[i-5]-c[i-5]/c[i-10])*100 if i>=10 else np.nan)
        F["fwd1"].append((c[i+1]/o[i+1]-1)*100 if o[i+1]>0 else np.nan)
        F["fwd3"].append((c[i+3]/o[i+1]-1)*100 if i+3<n and o[i+1]>0 else np.nan)
        F["fwd5"].append((c[i+5]/o[i+1]-1)*100 if i+5<n and o[i+1]>0 else np.nan)
    return {k:np.array(x,dtype=float) for k,x in F.items()}

HK={"fwd1":"1日","fwd3":"3日","fwd5":"5日"}
# 待测特征 (名称, 对应原评分项)
TESTS=[
    ("gt_ma5",  "现价>MA5 (+20分)"),
    ("ma5gt10", "MA5>MA10 (+15分)"),
    ("ma10gt20","MA10>MA20 (+15分)"),
    ("gt_ma60", "现价>MA60 (+15分)"),
    ("perfect", "完美多头排列 (+15分)"),
    ("pos_pct", "位置=接近60日高 (②位置 15分)"),
    ("ret20",   "过去20日涨幅(动量)"),
    ("ret5",    "过去5日涨幅(短动量)"),
    ("ret10",   "过去10日涨幅(中动量)"),
    ("accel",   "动量加速度"),
    ("vol_ratio","量比(原始, 非我量化)"),
]
print("="*78)
print("均线结构65分 子项拆解 + 替代特征对比 —— 跨11股, 均IC(正值=有预测力)")
print("="*78)
for feat,label in TESTS:
    ics3=[];ics5=[]
    pos3=0;neg3=0
    for code in CODES:
        df=load(code)
        if df is None: continue
        F=feats(df)
        for hk,fkey in [("fwd3","fwd3"),("fwd5","fwd5")]:
            v=~np.isnan(F[feat])&~np.isnan(F[hk])
            ic=spearman(F[feat][v],F[hk][v]) if v.sum()>10 else 0.0
            (ics3 if hk=="fwd3" else ics5).append(ic)
        v3=~np.isnan(F[feat])&~np.isnan(F["fwd3"])
    a3=np.mean(ics3); a5=np.mean(ics5)
    pos=(np.array(ics3)>0).sum(); neg=(np.array(ics3)<0).sum()
    tag=""
    if a3>0.03: tag="✅3日有效"
    elif a5>0.03: tag="~5日才见"
    elif a3<-0.02: tag="⚠️反向"
    else: tag="✗无效"
    print(f"  {label:<28} 3日IC:{a3:>+6.3f}  5日IC:{a5:>+6.3f}  3日IC>0:{pos:>2}股/{neg:<2} {tag}")

# 位置维度关键推演: 高分位置未来表现
print("\n"+"="*78)
print("位置维度推演: 把个股按60日位置分5档(0-20..80-100%), 看各档未来3日/5日均收益")
print("回答: 位置高(接近60日高)到底是好事还是追高风险?")
print("="*78)
buckets={b:[] for b in ["0-20","20-40","40-60","60-80","80-100"]}
for code in CODES:
    df=load(code)
    if df is None: continue
    F=feats(df)
    v=~np.isnan(F["pos_pct"])&~np.isnan(F["fwd3"])&~np.isnan(F["fwd5"])
    for i in np.where(v)[0]:
        p=F["pos_pct"][i]
        b="0-20" if p<.2 else "20-40" if p<.4 else "40-60" if p<.6 else "60-80" if p<.8 else "80-100"
        buckets[b].append(F["fwd3"][i])
for b in buckets.keys():
    arr=np.array(buckets[b])
    if len(arr):
        print(f"  60日位置 {b:<8}: 样本{len(arr):>6}  未来3日均收益 {arr.mean():>+6.2f}%")
