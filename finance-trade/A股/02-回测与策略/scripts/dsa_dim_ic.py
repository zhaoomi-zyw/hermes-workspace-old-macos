"""
DSA 评分逐维度 IC 检验
====================
检验 DSA 总分的5个组成维度各自对未来 1/3/5 日收益的预测力(Spearman RankIC),
回答:"加权分里到底哪些维度真的有用, 哪些是噪音甚至反向?"

维度(与 dsa_recheck.py / 实际评分一致):
  D1 均线结构65分 = 20(>MA5) + 15(MA5>MA10) + 15(MA10>MA20) + 15(>MA60) + 15(完美多头)
  D2 位置15分     = (close-lo60)/(hi60-lo60)*15   (越高分=越接近60日高)
  D3 量能10分     = 10(缩量<volma) / 5(<1.5x) / 2(>=1.5x放量)
  D4 趋势15分     = 15(>21日前) / 7(>11日前) / 3
  D5 总评分        = 上述和 (等级: S>=90/A80/B65/C50/D)

方法: 对每只股每日, 用 t 日各维度值 与 t+1/t+3/t+5 开盘到收盘收益算秩相关。
  用"次日开盘价"算收益避免未来函数(不与当日信号同源)。每个维度跨11只汇总 IR。
  同时算"该维度能否分层筛选": 高分组(顶1/3) vs 低分组(底1/3) 未来收益差。

用法: .venv/bin/python dsa_dim_ic.py [--horizon 1 3 5] [--lookback 800]
"""
from __future__ import annotations
import sys, glob, os
import numpy as np
import pandas as pd

DATA = "/Users/omi/workspace/quant-backtest/data"
CODES = ["601138","002156","600487","603380","600988","600460",
         "600522","002396","600219","000878","600760"]

def _rankdata(a):
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), float)
    i = 0
    while i < len(a):
        j = i
        while j+1 < len(a) and a[order[j+1]] == a[order[i]]:
            j += 1
        avg = (i+j)/2.0 + 1
        ranks[order[i:j+1]] = avg
        i = j+1
    return ranks

def spearman(a, b):
    a=np.asarray(a,float).ravel(); b=np.asarray(b,float).ravel()
    n=len(a)
    if n<10: return 0.0
    ra=_rankdata(a); rb=_rankdata(b)
    ma,mb=ra.mean(),rb.mean()
    cov=np.sum((ra-ma)*(rb-mb))
    va=np.sqrt(np.sum((ra-ma)**2)*np.sum((rb-mb)**2))
    return cov/va if va>0 else 0.0

def load(code):
    fs=glob.glob(f"{DATA}/{code}*.csv")
    if not fs: return None
    df=pd.read_csv(fs[0])
    df["date"]=pd.to_datetime(df["date"])
    return df.sort_values("date").reset_index(drop=True)

def compute_dims(df):
    """返回 (date[], dims_dict). 每行t用t日收盘算各维度分量(当日值)."""
    c=df["close"].values.astype(float); h=df["high"].values.astype(float)
    l=df["low"].values.astype(float); v=df["volume"].values.astype(float)
    o=df["open"].values.astype(float)
    n=len(c); dates=df["date"].values
    def ma(k,i): return c[i-k+1:i+1].mean() if i>=k-1 else np.nan
    out={"d1_structure":[],"d2_pos":[],"d3_vol":[],"d4_trend":[],"total":[],"next_ret1":[],"next_ret3":[],"next_ret5":[],"open":[],"close":[]}
    for i in range(60, n-5):  # 需要60日均线 + 未来5日
        c5=ma(5,i); c10=ma(10,i); c20=ma(20,i); c60=ma(60,i)
        lo60=l[i-59:i+1].min(); hi60=h[i-59:i+1].max()
        # D1 均线结构 65
        d1=0
        if c[i]>c5: d1+=20
        if c5>c10: d1+=15
        if c10>c20: d1+=15
        if c[i]>c60: d1+=15
        if c[i]>c5>c10>c20>c60: d1+=15
        # D2 位置 15
        d2=(c[i]-lo60)/(hi60-lo60)*15 if hi60>lo60 else 7.5
        # D3 量能 10
        volma=v[i-59:i+1].mean()
        d3 = 10 if v[i]<volma else (5 if v[i]<volma*1.5 else 2)
        # D4 趋势 15
        d4 = 15 if i>=21 and c[i]>c[i-21] else (7 if i>=11 and c[i]>c[i-11] else 3)
        total=d1+d2+d3+d4
        # 未来收益(用次日开盘到第k日收盘, 避免当日信号同源)
        def fwd(k):
            if i+k>=n: return np.nan
            return o[i+1] and (c[i+k]/o[i+1]-1)*100 if o[i+1]>0 else np.nan
        r1=(c[i+1]/o[i+1]-1)*100 if i+1<n and o[i+1]>0 else np.nan
        r3=(c[i+3]/o[i+1]-1)*100 if i+3<n and o[i+1]>0 else np.nan
        r5=(c[i+5]/o[i+1]-1)*100 if i+5<n and o[i+1]>0 else np.nan
        out["d1_structure"].append(d1); out["d2_pos"].append(d2)
        out["d3_vol"].append(d3); out["d4_trend"].append(d4); out["total"].append(total)
        out["next_ret1"].append(r1); out["next_ret3"].append(r3); out["next_ret5"].append(r5)
    return {k:np.array(vv,dtype=float) for k,vv in out.items()}

# horizon => key
HK={1:"next_ret1",3:"next_ret3",5:"next_ret5"}
HKVALS=["next_ret1","next_ret3","next_ret5"]
DIMS=[("d1_structure","①均线结构65"),("d2_pos","②位置15"),("d3_vol","③量能10"),("d4_trend","④趋势15"),("total","总分")]

horizons=[1,3,5]
if "--horizon" in sys.argv:
    i=sys.argv.index("--horizon"); horizons=[int(x) for x in sys.argv[i+1:i+4] if x.isdigit()] or [1,3,5]

# 汇总每个股票每维度的IC, 再跨股平均
results={hk: {dk:[] for dk,_ in DIMS} for hk in HKVALS}
stock_ics={}  # code -> {hk:{dim:ic}}
for code in CODES:
    df=load(code)
    if df is None or len(df)<70:
        print(f"[跳过] {code} 数据不足"); continue
    d=compute_dims(df)
    nm=len(d["total"])
    stock_ics[code]={hk:{} for hk in HKVALS}
    for hk in HKVALS:
        key=hk
        for dk,_ in DIMS:
            valid=~np.isnan(d[dk]) & ~np.isnan(d[key])
            ic=spearman(d[dk][valid], d[key][valid]) if valid.sum()>10 else 0.0
            results[hk][dk].append(ic)
            stock_ics[code][hk][dk]=ic

print("="*72)
print("DSA 维度 Spearman RankIC —— 跨 11 股汇总 (正=该维度高分对未来收益有预测力)")
print("收益口径: 次日开盘 → 第k日收盘")
print("="*72)
for hk in HKVALS:
    lab={"next_ret1":"1日","next_ret3":"3日","next_ret5":"5日"}[hk]
    print(f"\n【{lab}收益】")
    print(f"  {'维度':<12}{'均IC':>7}{'IC>0股':>8}{'IC<0股':>8}{'最强':>6}{'最弱':>6}")
    for dk,dn in DIMS:
        ics=np.array(results[hk][dk]); pos=(ics>0).sum(); neg=(ics<0).sum()
        mn=ics.mean(); mx=ics.max(); mnn=ics.min()
        # 定位最强/最弱个股
        best=max(stock_ics,key=lambda c:stock_ics[c][hk][dk])
        worst=min(stock_ics,key=lambda c:stock_ics[c][hk][dk])
        flag=""
        if mn>0.03: flag=" ✅有效"
        elif mn<-0.03: flag=" ⚠️反向"
        elif mn>0.01: flag=" 弱"
        else: flag=" ✗无效"
        print(f"  {dn:<12}{mn:>+7.3f}{pos:>7}只{neg:>7}只{best:>6}{worst:>6}{flag}")

# 分层检验: 高1/3 vs 低1/3 未来收益差(总分和各维度)
print("\n"+"="*72)
print("分层检验: 各维度 高分组(顶1/3) - 低分组(底1/3) 的未来平均收益差(pp)")
print("正差=高分组的未来收益确实更高")
print("="*72)
for dk,dn in DIMS:
    diffs={hk:[] for hk in HKVALS}
    for code in CODES:
        if code not in stock_ics: continue
        df=load(code); d=compute_dims(df)
        for hk in HKVALS:
            key=hk
            valid=~np.isnan(d[dk]) & ~np.isnan(d[key])
            if valid.sum()<30: continue
            x=d[dk][valid]; y=d[key][valid]
            thr=np.percentile(x,66.67); thrl=np.percentile(x,33.33)
            hi=y[x>=thr].mean(); lo=y[x<=thrl].mean()
            diffs[hk].append(hi-lo)
    for hk in HKVALS:
        lab={"next_ret1":"1日","next_ret3":"3日","next_ret5":"5日"}[hk]
        arr=np.array(diffs[hk])
        if len(arr):
            print(f"  {dn:<12} {lab}: 高-低 = {arr.mean():+.2f}pp  (11股中{int((arr>0).sum())}股为正)")
