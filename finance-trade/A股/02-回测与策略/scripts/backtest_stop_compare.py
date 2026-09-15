"""
积极版策略 3年回测 —— 止损档位对比 (-7% vs -6%)
================================================
同样积极版规则(左侧低吸+DSA≥B+回撤≥5%+站上MA60, 浮盈8%后移动止损10%/破MA60),
只切换硬止损幅度, 对比 2026-09-11 收紧前后:
  -7% (旧) vs -6% (新)
输出: 累计/年化/最大回撤/夏普/胜率/交易数 + 逐股对比
用法: .venv/bin/python backtest_stop_compare.py [--cash 10000]
"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd
from strategies.ma_strategy import load_data
from strategies import buy_cost, sell_cost, is_limit_up, is_limit_down
from dsa_scores import score_v1_series

STOCKS = {
    "601138": "工业富联", "002156": "通富微电", "600487": "亨通光电", "603380": "易德龙",
    "600988": "赤峰黄金", "600460": "士兰微", "600522": "中天科技", "002396": "星网锐捷",
    "600219": "南山铝业", "000878": "云南铜业", "600760": "中航沈飞",
}
START = "2023-09-06"
INIT_CASH = 10000.0
DD_MIN = 0.05
DSA_MIN = 65
PROFIT_LOCK = 0.08
TRAILING = 0.10
MAX_HOLD = 60
NEAR_MA10_X = 1.03
NEAR_MA5_X = 1.02


def backtest(df, stop_loss, init_cash=INIT_CASH):
    df = df.copy().sort_values("date").reset_index(drop=True)
    c = df["close"].astype(float)
    ma5 = c.rolling(5).mean(); ma10 = c.rolling(10).mean(); ma60 = c.rolling(60).mean()
    hi10 = df["high"].astype(float).rolling(10).max().shift(1)
    dsascore = score_v1_series(df)
    df["prev_close"] = c.shift(1)
    cash = init_cash; shares = 0; entry_price = 0.0; entry_idx = -1; peak_close = 0.0
    trades = []; equity = []; returns = []; prev_eq = init_cash
    for i in range(len(df)):
        row = df.iloc[i]; date, close, low, high, vol = row["date"], row["close"], row["low"], row["high"], row["volume"]
        if i < 60 or np.isnan(ma60.iloc[i]) or np.isnan(hi10.iloc[i]) or np.isnan(dsascore.iloc[i]):
            total = cash + shares*close; equity.append(total); returns.append(total/prev_eq-1 if prev_eq>0 else 0); prev_eq=total; continue
        if shares > 0:
            pnl = (close/entry_price - 1); peak_close = max(peak_close, close); hold = i - entry_idx; exit_ = None
            if pnl <= -stop_loss: exit_ = "止损"
            elif pnl >= PROFIT_LOCK:
                if close <= peak_close*(1-TRAILING): exit_ = "移动止损"
                elif close < ma60.iloc[i]: exit_ = "破MA60"
            elif hold >= MAX_HOLD: exit_ = "超期"
            if exit_:
                proceeds = shares*close - sell_cost(shares*close); cash += proceeds
                trades.append({"date": str(date)[:10], "entry": entry_price, "exit": close, "shares": shares,
                               "pnl": proceeds - shares*entry_price, "exit_reason": exit_, "hold": hold,
                               "ret": (close/entry_price-1)*100})
                shares = 0; entry_idx = -1
        if shares == 0:
            dd = (hi10.iloc[i] - close)/hi10.iloc[i]
            near_ma = (close <= ma10.iloc[i]*NEAR_MA10_X) or (close <= ma5.iloc[i]*NEAR_MA5_X)
            above60 = close > ma60.iloc[i]
            dsa_ok = dsascore.iloc[i] >= DSA_MIN
            prev_close = df["prev_close"].iloc[i]
            can_buy = (not is_limit_up(prev_close, close)) and (not is_limit_down(prev_close, close))
            if dd >= DD_MIN and near_ma and above60 and dsa_ok and can_buy:
                bsh = 100; cost = buy_cost(bsh*close)
                if cost <= cash*0.95:
                    cash -= cost; shares = bsh; entry_price = close; entry_idx = i; peak_close = close
        total = cash + shares*close; equity.append(total); returns.append(total/prev_eq-1 if prev_eq>0 else 0); prev_eq=total
    if shares>0:
        proceeds=shares*c.iloc[-1]-sell_cost(shares*c.iloc[-1]); cash+=proceeds
        trades.append({"date":str(df["date"].iloc[-1])[:10],"entry":entry_price,"exit":c.iloc[-1],"shares":shares,
                       "pnl":proceeds-shares*entry_price,"exit_reason":"期末","hold":len(df)-entry_idx,
                       "ret":(c.iloc[-1]/entry_price-1)*100})
    eq=np.array(equity); total_ret=eq[-1]/init_cash-1; n=len(eq); yrs=n/244
    annual=(1+total_ret)**(1/yrs)-1 if yrs>0 else 0
    peak=np.maximum.accumulate(eq); mdd=((eq-peak)/peak).min()
    r=np.array(returns[1:]); sd=r.std(); sharpe=r.mean()/sd*np.sqrt(244) if sd>0 else 0
    wins=[t for t in trades if t["pnl"]>0]
    return {"trades":trades,"total_ret":total_ret,"annual":annual,"maxdd":mdd,"sharpe":sharpe,
            "n":len(trades),"win_rate":len(wins)/len(trades) if trades else 0,
            "net_pnl":sum(t["pnl"] for t in trades),"avg_hold":np.mean([t["hold"] for t in trades]) if trades else 0,
            "stopouts":len([t for t in trades if t["exit_reason"]=="止损"])}


if __name__ == "__main__":
    cash = 10000.0
    if "--cash" in sys.argv: cash = float(sys.argv[sys.argv.index("--cash")+1])
    VARIANTS = [("-7%", 0.07), ("-6%", 0.06)]
    results = {}; per_stock = {}
    for label, sl in VARIANTS:
        tot=[]; dd=[]; sh=[]; an=[]; nt=0; nw=0; ns=0; ah=[]
        per_stock[label]=[]
        for code,name in STOCKS.items():
            df=load_data(code,name); df["date"]=pd.to_datetime(df["date"])
            df=df[df["date"]>=pd.to_datetime(START)].reset_index(drop=True)
            if len(df)<200: continue
            r=backtest(df, sl, init_cash=cash)
            tot.append(r["total_ret"]); dd.append(r["maxdd"]); sh.append(r["sharpe"]); an.append(r["annual"])
            nt+=r["n"]; nw+=int(r["n"]*r["win_rate"]); ns+=r["stopouts"]
            if r["n"]: ah.append(r["avg_hold"])
            per_stock[label].append((name, r["total_ret"], r["maxdd"], r["sharpe"], r["n"], r["win_rate"], r["stopouts"]))
        results[label]={"tot":np.mean(tot),"annual":np.mean(an),"dd":np.mean(dd),"sharpe":np.mean(sh),
                        "n":nt,"wr":nw/max(nt,1),"stopouts":ns,"avg_hold":np.mean(ah) if ah else 0,
                        "all_tot":tot, "all_dd":dd}
    # 控制台输出
    print(f"=== 积极版3年回测: 止损 -7%(旧) vs -6%(新) ===  11只自选 | 起始{cash:,.0f}元 | {START}~至今 | 左侧低吸")
    print(f"{'止损':<6}{'均累计':>10}{'均年化':>9}{'均回撤':>9}{'均夏普':>8}{'总交易':>7}{'胜率':>6}{'止损离场':>8}{'均持仓':>7}")
    for label,_ in VARIANTS:
        r=results[label]
        print(f"{label:<6}{r['tot']*100:>+9.1f}%{r['annual']*100:>+8.1f}%{r['dd']*100:>+8.1f}%{r['sharpe']:>+8.2f}{r['n']:>7}{r['wr']*100:>5.0f}%{r['stopouts']:>8}{r['avg_hold']:>6.1f}天")
    print("\n逐股累计收益对比:")
    print(f"{'标的':<9}{'-7%旧':>10}{'-6%新':>10}{'差异':>9}")
    for i,(name,_,_,_,_,_,_) in enumerate([(x[0],0,0,0,0,0,0) for x in per_stock['-7%']]):
        a=per_stock['-7%'][i][1]; b=per_stock['-6%'][i][1]
        print(f"{name:<9}{a*100:>+9.1f}%{b*100:>+9.1f}%{(b-a)*100:>+8.1f}%")
    # 保存json供HTML用
    out={"results":{k:{kk:vv for kk,vv in v.items() if kk not in ('all_tot','all_dd')} for k,v in results.items()},
         "per_stock":per_stock, "cash":cash, "start":START}
    json.dump(out, open("/Users/omi/workspace/quant-backtest/results/stop_compare.json","w"), ensure_ascii=False, default=float)
    print("\n结果已存 results/stop_compare.json")
