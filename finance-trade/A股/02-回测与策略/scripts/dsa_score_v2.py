"""
DSA 评分重构 (v2) —— 基于 2026-09-08 逐维度IC推演
================================================
旧版问题(IC实测):
  ① 均线结构65/60分 = 滞后状态, IC≈0, 完美多头甚至反向(趋势末端顶部)
  ② 位置"高=高分"但数据反直觉(见下)
  ③ 量能"缩量加分"把弱正的量比扭曲成反向
  ④ 唯一有效的动量只给15分, 被噪音稀释

重构原则:
  A. 动量/趋势为主导 —— 但区分两种:
      健康动量(温和上涨) vs 情绪透支(短期暴涨/连涨) —— 后者惩罚
  B. 位置翻转: 突破新高/接近60日高的动量股未来更强(实测+0.52%),
     但叠加连涨过热惩罚来调和"追高被套"实战教训
  C. 均线结构降为辅助确认(小权重, 只在确认趋势不破时加分)
  D. 量能回归原始弱正(放量不惩罚, 缩量不强加分)

本文件: 定义新旧两版评分 + 逐日IC对比 + 位置/透支交叉检验, 验证v2是否真优于v1
"""
from __future__ import annotations
import glob, sys
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

def _prep(df):
    c=df["close"].astype(float); h=df["high"].astype(float); l=df["low"].astype(float); v=df["volume"].astype(float)
    o=df["open"].astype(float)
    df=df.copy()
    df["ma5"]=c.rolling(5).mean(); df["ma10"]=c.rolling(10).mean()
    df["ma20"]=c.rolling(20).mean(); df["ma60"]=c.rolling(60).mean()
    df["vm20"]=v.rolling(20).mean()
    df["lo60"]=l.rolling(60).min(); df["hi60"]=h.rolling(60).max()
    df["ret5"]=c.pct_change(5)*100; df["ret10"]=c.pct_change(10)*100
    df["ret20"]=c.pct_change(20)*100
    df["ret1"]=c.pct_change()*100
    df["vol_ratio"]=v/df["vm20"]
    df["pos60"]=(c-df["lo60"])/(df["hi60"]-df["lo60"])
    # 未来收益(次日开盘→第k日收盘)
    n=len(df)
    for k in [1,3,5]:
        fwd=np.full(n,np.nan); o_next=o.shift(-1)
        fwd[:n-k]=((c.shift(-k)/o_next)*100-100).iloc[:n-k].values
        # 用 shift 实现: fwd_k[t] = (c[t+k]/o[t+1]-1)*100
    f1=(c.shift(-1)/o.shift(-1)-1)*100
    f3=(c.shift(-3)/o.shift(-1)-1)*100
    f5=(c.shift(-5)/o.shift(-1)-1)*100
    df["fwd1"]=f1; df["fwd3"]=f3; df["fwd5"]=f5
    return df

def score_v1(df):
    """原版(backtest_planA 权威版)"""
    c=df["close"]; ma5=df["ma5"];ma10=df["ma10"];ma20=df["ma20"];ma60=df["ma60"]
    vm=df["vm20"].shift(1); last_v=df["volume"]
    s=pd.Series(0.0,index=df.index)
    s+=(c>ma5)*15; s+=(ma5>ma10)*10; s+=(ma10>ma20)*10; s+=(c>ma20)*10; s+=(c>ma60)*15
    perfect=(c>ma5)&(ma5>ma10)&(ma10>ma20)&(ma20>ma60); s+=perfect*15
    rng=df["hi60"]-df["lo60"]; s+=(((c-df["lo60"])/rng)*15).fillna(7.5).where(rng>0,7.5)
    vol_score=np.where(last_v<vm,10,np.where(last_v<vm*1.5,5,2)); s+=pd.Series(vol_score,index=df.index)
    c20=c.shift(20); s+=np.where(c>c20,15,np.where(c>c.shift(10),7,3))
    return s

def score_v2(df):
    """
    重构版 v2 —— 满分约 100
    =====================
    动量主导(30): 温和动量 reward
      10日涨幅在 健康区间(0~8%) 给高, 负动量/暴涨透支 降分
    = 用 ret10 分段
    趋势方向(20): 现价>MA60(站上长期趋势) 给20; 否则 0 (破MA60不给分)
    多头结构确认(15): 均线非完美多头, 但 MA5>MA20 且 现价>MA10 给分(趋势未被破坏)
      完美多头只给少量加分(不重复给大权重)
    位置(20): 位置维度翻转 —— 但拆两半
      位置基础(10): 越接近60日高越高(实测高位动量强)
      新鲜突破(10): 现价在近20日新高附近(0~6%内) 给分 —— 捕捉"刚突破"
    透支惩罚(-20): 情绪过热过滤
      连续大涨: 3日中任一日涨>6% 或 5日累计>12% → 扣
      涨停次日: ret1>9.5% → 扣
      量比过热: vol_ratio>2.5 → 扣
    量能弱支持(10): 温和放量(1.0~2.0x)小加; 极度缩量不加 (回归原始弱正)
    """
    c=df["close"]; ma5=df["ma5"];ma10=df["ma10"];ma20=df["ma20"];ma60=df["ma60"]
    ret1=df["ret1"].fillna(0); ret5=df["ret5"].fillna(0); ret10=df["ret10"].fillna(0); ret20=df["ret20"].fillna(0)
    vr=df["vol_ratio"].fillna(1); pos60=df["pos60"].fillna(0.5)
    hi20=df["close"].rolling(20).max(); lo20=df["close"].rolling(20).min()
    s=pd.Series(0.0,index=df.index)
    # 1) 动量 30: 温和动量reward (核心预测力)
    mom=pd.Series(0.0,index=df.index)
    mom+=30 * ((ret10>0)&(ret10<=8))          # 10日涨0-8%: 健康动量满
    mom+=15 * ((ret10>8)&(ret10<=12))         # 10日涨8-12: 强但接近透支
    mom+=5  * ((ret10>12)&(ret10<=20))        # 10日涨12-20: 已透支大部分
    mom+=0  * (ret10>20)                      # >20: 过热0
    mom+=8  * ((ret10>-3)&(ret10<=0))         # 微跌: 蓄势
    mom+=0  * (ret10<=-3)                     # 跌>3%: 弱势0
    s+=mom
    # 2) 趋势方向 20: 站上MA60
    s+=(c>ma60)*20
    # 3) 多头结构确认 15: 趋势未破坏
    struct=pd.Series(0.0,index=df.index)
    struct+=(ma5>ma20)*5                       # 短均线在长均线上
    struct+=(c>ma10)*5                         # 价格守住MA10
    struct+=((ma10>ma20)&(ma20>ma60))*5        # 中长多头骨架
    s+=struct
    # 4) 位置 20 (翻转: 高位动量强, 但要新鲜)
    s+=pos60*10                                # 位置基础10分
    near_hi20=((hi20-c)/hi20*100<=3).astype(float)  # 距20日高3%内=新鲜突破
    s+=near_hi20*10
    # 5) 透支惩罚 -20
    over=pd.Series(0.0,index=df.index)
    over+=10*((ret5>12)|(ret1>6)|(ret1>9.5))    # 5日>12 或 单日>6% /涨停
    over+=10*((vr>2.5)|(ret10>25))             # 量能过热 或 10日暴涨
    s-=over
    # 6) 量能弱支持 10: 温和放量小加, 不惩罚放量
    s+=np.where((vr>=1.0)&(vr<=2.0),10,np.where((vr>2.0)&(vr<=3.0),6,2))
    return s.clip(lower=0)

def grade(s):
    return pd.Series(np.where(s>=85,"S",np.where(s>=70,"A",np.where(s>=55,"B",np.where(s>=40,"C","D")))),index=s.index)

# ========== 对比验证 ==========
HK={"fwd1":"1日","fwd3":"3日","fwd5":"5日"}
HKVALS=list(HK.keys())
v1ics={h:[] for h in HKVALS}; v2ics={h:[] for h in HKVALS}
v1tops={h:[] for h in HKVALS}; v2tops={h:[] for h in HKVALS}  # 顶部1/3分组未来均收益
for code in CODES:
    df=load(code)
    if df is None or len(df)<70: continue
    d=_prep(df)
    s1=score_v1(d); s2=score_v2(d)
    for fk in HKVALS:
        vv=(d.index>=60)&~np.isnan(s1)&~np.isnan(s2)&~np.isnan(d[fk])
        a=s1[vv].values; b=s2[vv].values; y=d[fk][vv].values
        if len(a)<30: continue
        v1ics[fk].append(spearman(a,y)); v2ics[fk].append(spearman(b,y))
        # 顶部1/3
        t1=np.percentile(a,66.67); t2=np.percentile(b,66.67)
        v1tops[fk].append(y[a>=t1].mean()); v2tops[fk].append(y[b>=t1].mean())

print("="*70)
print("旧版 v1 vs 重构 v2 —— 逐日Spearman IC(跨11股均) + 顶1/3分组未来收益")
print("="*70)
print(f"{'收益':<5}{'旧v1均IC':>10}{'新v2均IC':>10}{'v1顶1/3收益':>13}{'v2顶1/3收益':>13}")
for h in HKVALS:
    print(f"{HK[h]:<5}{np.mean(v1ics[h]):>+10.3f}{np.mean(v2ics[h]):>+10.3f}{np.mean(v1tops[h]):>+12.2f}%{np.mean(v2tops[h]):>+12.2f}%")

# 谁更好: 逐股比较
print("\n逐股比较 3日IC (v2-v1>0 = 重构提升):")
impr=0
for code in CODES:
    df=load(code)
    if df is None or len(df)<70: continue
    d=_prep(df); s1=score_v1(d); s2=score_v2(d)
    vv=(d.index>=60)&~np.isnan(s1)&~np.isnan(s2)&~np.isnan(d["fwd3"])
    if vv.sum()<30: continue
    ic1=spearman(s1[vv].values,d["fwd3"][vv].values); ic2=spearman(s2[vv].values,d["fwd3"][vv].values)
    mark="✓提升" if ic2>ic1 else "✗下降"
    if ic2>ic1: impr+=1
    print(f"  {code}: v1 {ic1:+.3f} → v2 {ic2:+.3f} {mark}")
print(f"\n3日IC 重构后提升的股票: {impr}/{len(CODES)}")
