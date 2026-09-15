"""
积极版策略 3年回测 —— DSA评分版本对比 (v1旧 vs v3重构)
=====================================================
同样积极版规则, 只切换 dsa_score 实现, 对比:
  - 累计收益 / 年化 / 最大回撤 / 夏普 / 胜率 / 交易次数
用法: .venv/bin/python backtest_aggressive_compare.py [--cash 10000] [--score v1|v3|both]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd
from strategies.ma_strategy import load_data, BacktestResult
from strategies import buy_cost, sell_cost, is_limit_up, is_limit_down
from dsa_scores import score_v1_series, score_v3_series, score_v4_series

# 当前真实11只自选 (2026-09-08, 已去紫光, 含南山/云南/沈飞)
STOCKS = {
    "601138": "工业富联", "002156": "通富微电", "600487": "亨通光电", "603380": "易德龙",
    "600988": "赤峰黄金", "600460": "士兰微", "600522": "中天科技", "002396": "星网锐捷",
    "600219": "南山铝业", "000878": "云南铜业", "600760": "中航沈飞",
}
# 各评分版本的 DSA_MIN (B级门槛)
DSA_MIN = {"v1": 65, "v3": 45, "v4": 65}   # v4沿用v1尺度(>=65=B)

START = "2023-09-06"
INIT_CASH = 10000.0
DD_MIN = 0.05
STOP_LOSS = 0.07
PROFIT_LOCK = 0.08
TRAILING = 0.10
MAX_HOLD = 60
NEAR_MA10_X = 1.03
NEAR_MA5_X = 1.02


def backtest(df, score_series, dsa_min, init_cash=INIT_CASH, verbose=False):
    df = df.copy().sort_values("date").reset_index(drop=True)
    c = df["close"].astype(float)
    ma5 = c.rolling(5).mean(); ma10 = c.rolling(10).mean(); ma60 = c.rolling(60).mean()
    hi10 = df["high"].astype(float).rolling(10).max().shift(1)
    res20 = df["high"].astype(float).rolling(20).max().shift(1)
    vol_ma20 = df["volume"].rolling(20).mean().shift(1)
    dsascore = score_series(df)
    df["prev_close"] = c.shift(1)
    cash = init_cash; shares = 0; entry_price = 0.0; entry_idx = -1; peak_close = 0.0
    trades = []; equity = []; returns = []; prev_eq = init_cash
    for i in range(len(df)):
        row = df.iloc[i]; date, close, low, high, vol = row["date"], row["close"], row["low"], row["high"], row["volume"]
        if i < 60 or np.isnan(ma60.iloc[i]) or np.isnan(hi10.iloc[i]) or np.isnan(dsascore.iloc[i]):
            total = cash + shares*close; equity.append(total); returns.append(total/prev_eq-1 if prev_eq>0 else 0); prev_eq=total; continue
        # 持仓离场
        if shares > 0:
            pnl = (close/entry_price - 1)
            peak_close = max(peak_close, close)
            hold = i - entry_idx
            exit_ = None
            if pnl <= -STOP_LOSS: exit_ = "止损"
            elif pnl >= PROFIT_LOCK:
                if close <= peak_close*(1-TRAILING): exit_ = "移动止损"
                elif close < ma60.iloc[i]: exit_ = "破MA60"
            elif hold >= MAX_HOLD: exit_ = "超期"
            if exit_:
                proceeds = shares*close - sell_cost(shares*close)
                cash += proceeds
                trades.append({"date": date, "entry": entry_price, "exit": close, "shares": shares, "pnl": proceeds - shares*entry_price, "exit_reason": exit_, "hold": hold})
                shares = 0; entry_idx = -1
        # 开仓(仅左侧低吸: 因为右侧已停用)
        if shares == 0:
            dd = (hi10.iloc[i] - close)/hi10.iloc[i]
            near_ma = (close <= ma10.iloc[i]*NEAR_MA10_X) or (close <= ma5.iloc[i]*NEAR_MA5_X)
            above60 = close > ma60.iloc[i]
            dsa_ok = dsascore.iloc[i] >= dsa_min
            prev_close = df["prev_close"].iloc[i]
            can_buy = (not is_limit_up(prev_close, close)) and (not is_limit_down(prev_close, close))
            if dd >= DD_MIN and near_ma and above60 and dsa_ok and can_buy:
                max_shares = int(cash*0.95 / (close*100)) * 100
                if max_shares >= 100:
                    bsh = 100
                    cost = buy_cost(bsh*close)
                    if cost <= cash*0.95:
                        cash -= cost; shares = bsh; entry_price = close; entry_idx = i; peak_close = close
                        if verbose: print(f"[买] {str(date)[:10]} @{close:.2f} DSA{dsascore.iloc[i]:.0f} 回撤{dd:.1%}")
        total = cash + shares*close; equity.append(total); returns.append(total/prev_eq-1 if prev_eq>0 else 0); prev_eq=total
    # 收尾
    if shares>0:
        proceeds=shares*c.iloc[-1]-sell_cost(shares*c.iloc[-1]); cash+=proceeds
        trades.append({"date":df["date"].iloc[-1],"entry":entry_price,"exit":c.iloc[-1],"shares":shares,"pnl":proceeds-shares*entry_price,"exit_reason":"期末","hold":len(df)-entry_idx})
    eq=np.array(equity)
    total_ret=eq[-1]/init_cash-1
    n=len(eq); yrs=n/244
    annual=(1+total_ret)**(1/yrs)-1 if yrs>0 else 0
    peak=np.maximum.accumulate(eq); dd=((eq-peak)/peak).min()
    r=np.array(returns[1:]); sd=r.std()
    sharpe=r.mean()/sd*np.sqrt(244) if sd>0 else 0
    wins=[t for t in trades if t["pnl"]>0]
    wins_amt=np.sum([t["pnl"] for t in wins]); loss_amt=-np.sum([t["pnl"] for t in trades if t["pnl"]<=0])
    return {"trades":trades,"total_ret":total_ret,"annual":annual,"maxdd":dd,"sharpe":sharpe,
            "n":len(trades),"win_rate":len(wins)/len(trades) if trades else 0,"net_pnl":sum(t["pnl"] for t in trades),
            "avg_win":wins_amt/len(wins) if wins else 0,"avg_loss":loss_amt/(len(trades)-len(wins)) if len(trades)>len(wins) else 0}

def report(name, res):
    print(f"\n【{name}】交易{res['n']}笔 | 累计{res['total_ret']*100:+.1f}% | 年化{res['annual']*100:+.1f}% | 最大回撤{res['maxdd']*100:.1f}% | 夏普{res['sharpe']:+.2f} | 胜率{res['win_rate']*100:.0f}% | 净盈亏{res['net_pnl']:+.0f}")

if __name__ == "__main__":
    cash=10000.0; scoremode="v1,v4"
    if "--cash" in sys.argv: cash=float(sys.argv[sys.argv.index("--cash")+1])
    if "--score" in sys.argv: scoremode=sys.argv[sys.argv.index("--score")+1]
    VERSIONS=[x.strip() for x in scoremode.split(",") if x.strip()]
    SCORES={"v1":score_v1_series,"v3":score_v3_series,"v4":score_v4_series}
    argcodes=[a for a in sys.argv[1:] if a[:1].isdigit() and a not in ("10000","1000","5000","20000")]
    targets={c:STOCKS[c] for c in (argcodes or list(STOCKS.keys())) if c in STOCKS}
    agg={s:{"tot":[],"dd":[],"sharpe":[],"ret":[],"n":0,"wins":0} for s in VERSIONS}
    print(f"=== 积极版 3年回测: DSA评分版本对比 {VERSIONS} ===")
    print(f"标的 {len(targets)}只 | 起始{cash:,.0f}元 | 区间 {START} ~ 至今 | 左侧低吸(右侧已停用)")
    for code,name in targets.items():
        df=load_data(code,name); df["date"]=pd.to_datetime(df["date"])
        df=df[df["date"]>=pd.to_datetime(START)].reset_index(drop=True)
        if len(df)<200: print(f"  [跳过]{code}"); continue
        for s in VERSIONS:
            dsa_min=DSA_MIN[s]; sf=SCORES[s]
            r=backtest(df, sf, dsa_min, init_cash=cash)
            agg[s]["tot"].append(r["total_ret"]);agg[s]["dd"].append(r["maxdd"]);agg[s]["sharpe"].append(r["sharpe"])
            agg[s]["ret"].append(r["annual"]);agg[s]["n"]+=r["n"];agg[s]["wins"]+=int(r["n"]*r["win_rate"])
    print("\n"+"="*72)
    print("逐股对比:")
    hdr=f"{'标的':<8}"+"".join(f"{v:>12}" for v in VERSIONS)
    print(hdr)
    for code,name in targets.items():
        df=load_data(code,name); df["date"]=pd.to_datetime(df["date"])
        df=df[df["date"]>=pd.to_datetime(START)].reset_index(drop=True)
        if len(df)<200: continue
        line=f"{name:<8}"
        for v in VERSIONS:
            r=backtest(df, SCORES[v], DSA_MIN[v], init_cash=cash)
            line+=f"{r['total_ret']*100:>+11.1f}%"
        print(line)
    for s in VERSIONS:
        t=np.array(agg[s]["tot"]);d=np.array(agg[s]["dd"]);sh=np.array(agg[s]["sharpe"]);an=np.array(agg[s]["ret"])
        print(f"◆ {s} 均累计{t.mean()*100:+.1f}% | 均年化{an.mean()*100:+.1f}% | 均回撤{d.mean()*100:.1f}% | 均夏普{sh.mean():+.2f} | 总交易{agg[s]['n']}笔(胜率{agg[s]['wins']/max(agg[s]['n'],1)*100:.0f}%)")
