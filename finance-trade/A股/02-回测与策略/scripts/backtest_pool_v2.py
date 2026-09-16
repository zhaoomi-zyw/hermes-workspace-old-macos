# -*- coding: utf-8 -*-
"""基准回测 v2 — 修正两处bug + SELL-POLICY-v1.0 真实规则"""
import os, csv, glob, statistics, json, re
DATA="/Users/omi/workspace/quant-backtest/data"
INIT_CASH=13866.52
COMM,STAMP,XFER,SLIP,MINC = 0.00025,0.0005,0.00001,0.0005,5.0   # 滑点降为万5
def bfee(a): return max(a*COMM,MINC)+a*XFER+a*SLIP
def sfee(a): return max(a*COMM,MINC)+a*STAMP+a*XFER+a*SLIP

src=open(os.path.expanduser("~/.hermes/profiles/main/scripts/lowbuy-watch.py"),encoding="utf-8").read()
ns={}
for fn in ["sma","dsa_score"]:
    m=re.search(rf'^def {fn}\(.*?(?=^def |\Z)',src,re.M|re.S)
    if m: exec(m.group(0),ns)
sma,dsa_score=ns["sma"],ns["dsa_score"]

def load(code):
    for f in glob.glob(f"{DATA}/*{code}*.csv"):
        rows=[]
        with open(f,newline='') as fh:
            for r in csv.DictReader(fh):
                try: rows.append(dict(date=r["date"][:10],o=float(r["open"]),h=float(r["high"]),
                                      l=float(r["low"]),c=float(r["close"]),v=float(r["volume"])))
                except: pass
        return rows
    return []

POOL_ALL=["600522","601138","002156","000878","600760","600988","603380","600487","600219","600460","002396","000938"]
POOL_CAND=["600522","601138","002156","000878","600760","600988","603380"]
POOL_EXCL=[c for c in POOL_ALL if c!="000938"]
NAMES={"600522":"中天科技","601138":"工业富联","002156":"通富微电","000878":"云南铜业","600760":"中航沈飞",
 "600988":"赤峰黄金","603380":"易德龙","600487":"亨通光电","600219":"南山铝业","600460":"士兰微",
 "002396":"星网锐捷","000938":"紫光股份"}

DB={c:load(c) for c in POOL_ALL}
IDX={c:{d["date"]:i for i,d in enumerate(DB[c])} for c in POOL_ALL}
ALLD=sorted(set(d["date"] for c in POOL_ALL for d in DB[c]))

def signal_at(code,date):
    i=IDX[code].get(date)
    if i is None or i<60: return None
    rows=DB[code][:i+1]
    cl=[r["c"] for r in rows]; hi=[r["h"] for r in rows]; lo=[r["l"] for r in rows]; vo=[r["v"] for r in rows]
    d=dsa_score(cl,hi,lo,vo)
    if d is None or d<65: return None
    c=cl[-1]; ma5,ma10,ma60=sma(cl,5),sma(cl,10),sma(cl,60)
    if None in (ma5,ma10,ma60): return None
    hi10=max(hi[-11:-1])          # ★ 修正1: 不含当日（等价 .shift(1)）
    dd=(hi10-c)/hi10*100
    d5=abs(c/ma5-1)*100; d10=abs(c/ma10-1)*100
    if dd>=5 and c>ma60 and (d5<=2 or d10<=2):
        return dict(dsa=d,dd=dd)
    return None

MAX_HOLD=60
def run(pool,t0=None,t1=None):
    cash=INIT_CASH; pos=None; trades=[]
    dates=[d for d in ALLD if (t0 is None or d>=t0) and (t1 is None or d<=t1)]
    for date in dates:
        if pos:
            code=pos["code"]; i=IDX[code].get(date)
            if i is not None and pos["entry_date"]!=date:
                bar=DB[code][i]; pos["days"]+=1; C=pos["cost"]
                # ★ 修正2: 先用【进场时状态】判定止损, 再更新 H
                ex,rs=None,None
                if bar["l"]<=pos["S"]:
                    ex,rs=min(pos["S"],bar["o"]),"R1硬止损"
                elif pos["active"] and pos["P"] and bar["l"]<=pos["P"]:
                    ex,rs=min(pos["P"],bar["o"]),"R4盈利保护"
                elif pos["days"]>=MAX_HOLD:
                    ex,rs=bar["c"],"到期60日"
                if ex:
                    amt=ex*pos["qty"]; fee=sfee(amt); cash+=amt-fee
                    pnl=(ex-C)*pos["qty"]-fee-pos["buy_fee"]
                    trades.append(dict(code=code,name=NAMES[code],ind=pos["entry_date"],outd=date,
                        inpx=pos["entry_price"],outpx=ex,qty=pos["qty"],pnl=pnl,
                        ret=(ex/C-1)*100,days=pos["days"],reason=rs))
                    pos=None
                else:
                    H=max(pos["H"],bar["h"]); pos["H"]=H
                    if H>=C*1.08: pos["active"]=True
                    if pos["active"]:
                        pos["P"]=max(pos.get("P") or 0,round(C*1.03,2),round(H*0.93,2))
        if pos is None and cash>1000:
            best=None
            for code in pool:
                sig=signal_at(code,date)
                if not sig or date not in IDX[code]: continue
                px=DB[code][IDX[code][date]]["c"]
                qty=int(cash/(px*100))*100
                if qty<100: continue
                if best is None or sig["dsa"]>best[1]["dsa"]: best=(code,sig,px,qty)
            if best:
                code,sig,px,qty=best; amt=px*qty; fee=bfee(amt)
                if amt+fee<=cash:
                    cash-=amt+fee
                    pos=dict(code=code,qty=qty,cost=px,entry_price=px,entry_date=date,
                             H=px,S=round(px*0.94,2),P=None,active=False,days=0,buy_fee=fee)
    if pos and dates:
        d0=dates[-1]; code=pos["code"]
        px=DB[code][IDX[code][d0]]["c"] if d0 in IDX[code] else DB[code][-1]["c"]
        amt=px*pos["qty"]; fee=sfee(amt); cash+=amt-fee
        pnl=(px-pos["cost"])*pos["qty"]-fee-pos["buy_fee"]
        trades.append(dict(code=code,name=NAMES[code],ind=pos["entry_date"],outd=d0,inpx=pos["entry_price"],
            outpx=px,qty=pos["qty"],pnl=pnl,ret=(px/pos["cost"]-1)*100,days=pos["days"],reason="期末强平"))
    w=[t for t in trades if t["pnl"]>0]
    return dict(final=cash,ret=(cash/INIT_CASH-1)*100,n=len(trades),
                win=len(w)/len(trades)*100 if trades else 0,
                avg=statistics.mean([t["ret"] for t in trades]) if trades else 0,
                pnl=sum(t["pnl"] for t in trades),trades=trades)

for label,(t0,t1) in [("【3年 2023-09-06~2026-09-14】对齐已有脚本",("2023-09-06",None)),
                      ("【5年 2021-09~2026-09】",(None,None))]:
    print("\n"+"="*104); print(label); print("="*104)
    print("{:<22}{:>7}{:>9}{:>10}{:>12}{:>20}".format("方案","笔数","胜率","均收益","净盈亏","期末/收益率"))
    for lab,pool in [("基准:12只全池",POOL_ALL),("方案A:候选池7只",POOL_CAND),("方案B:排除暂停11只",POOL_EXCL)]:
        r=run(pool,t0,t1)
        print("{:<22}{:>7}{:>8.1f}%{:>9.2f}%{:>11.0f}元{:>11.0f} / {:>6.1f}%".format(
            lab,r["n"],r["win"],r["avg"],r["pnl"],r["final"],r["ret"]))
