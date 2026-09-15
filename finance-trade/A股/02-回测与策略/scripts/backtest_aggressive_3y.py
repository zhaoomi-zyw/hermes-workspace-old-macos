"""
积极版策略 3年回测 — 对比方案A
================================
方案A(防守): 固定止盈+8% / 止损-4.5% / 最长20天 — 容易卖飞趋势股
积极版(趋势): 让利润奔跑 — 移动止损 + 破MA60离场, 止损放宽给震荡空间

积极版规则:
- 买入: 保留左侧低吸(回撤>=5%+站上MA60+DSA A/B+接近MA5/MA10) 
        + 增加放量突破入场(close>20日高+量>1.5倍均量, 右侧追强)
- 止损: -7% (放宽, 避免高波动被洗)
- 盈利保护: 浮盈>=+8% 后启用移动止损(从持仓最高收盘回撤10%) 和 破MA60离场
- 未达盈利保护: 只受硬止损约束(给建仓初期空间, 不被小波动洗掉)
- 最长持仓: 60交易日
- 仓位: 资金可用则买 满手(整百股), 上限占可用资金95%
- T+1/涨跌停/费用 同方案A

用法: .venv/bin/python backtest_aggressive_3y.py [代码] [--cash 10000]
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd

from strategies.ma_strategy import load_data, BacktestResult, buy_cost, sell_cost, is_limit_up, is_limit_down
from backtest_planA_3y import STOCKS, dsa_score_series

START = "2023-09-06"
INIT_CASH = 10000.0

# 积极版参数
DD_MIN = 0.05
DSA_MIN = 65
STOP_LOSS = 0.07
PROFIT_LOCK = 0.08      # 浮盈+8%后启用趋势离场
TRAILING = 0.10         # 从最高收盘回撤10%离场
MAX_HOLD = 60
NEAR_MA10_X = 1.03
NEAR_MA5_X = 1.02


def backtest_aggressive(df, init_cash=INIT_CASH, verbose=False):
    df = df.copy().sort_values("date").reset_index(drop=True)
    c = df["close"].astype(float)
    ma5 = c.rolling(5).mean(); ma10 = c.rolling(10).mean(); ma60 = c.rolling(60).mean()
    hi10 = df["high"].astype(float).rolling(10).max().shift(1)
    res20 = df["high"].astype(float).rolling(20).max().shift(1)  # 20日压力(放量突破用)
    vol_ma20 = df["volume"].rolling(20).mean().shift(1)
    dsascore = dsa_score_series(df)
    df["prev_close"] = c.shift(1)

    cash = init_cash
    shares = 0
    entry_price = 0.0
    entry_idx = -1
    peak_close = 0.0   # 持仓期最高收盘
    trades = []
    equity = []
    returns = []
    prev_eq = init_cash

    for i in range(len(df)):
        row = df.iloc[i]
        date, close, low, high, vol = row["date"], row["close"], row["low"], row["high"], row["volume"]
        if i < 60 or np.isnan(ma60.iloc[i]) or np.isnan(hi10.iloc[i]):
            total = cash + shares*close
            equity.append(total); returns.append(total/prev_eq-1 if prev_eq>0 else 0); prev_eq=total
            continue

        # ---- 持仓离场 ----
        if shares > 0:
            hold_days = i - entry_idx
            can_sell = hold_days >= 1
            pnl_pct = close / entry_price - 1
            if can_sell and not is_limit_down(row["prev_close"], close):
                # 更新峰值(仅盈利保护后有意义, 但先记录)
                peak_close = max(peak_close, high if False else close)
                exit_reason = None
                # 硬止损(任何时候, 放宽到-7%)
                if close <= entry_price * (1 - STOP_LOSS):
                    exit_reason = "止损"
                else:
                    locked = pnl_pct >= PROFIT_LOCK
                    if locked:
                        # 盈利保护后: 移动止损 + 破MA60
                        peak_close = max(peak_close, close)
                        if close <= peak_close * (1 - TRAILING):
                            exit_reason = "移动止损"
                        elif not np.isnan(ma60.iloc[i]) and close < ma60.iloc[i]:
                            exit_reason = "破MA60"
                    if exit_reason is None and hold_days >= MAX_HOLD:
                        exit_reason = "到期"
                if exit_reason:
                    proceeds = shares*close - sell_cost(shares*close)
                    pnl = proceeds - entry_price*shares
                    trades.append({"type":"sell","reason":exit_reason,"date":date,"price":close,
                                   "shares":shares,"pnl":pnl,"pnl_pct":pnl/(entry_price*shares),
                                   "hold_days":hold_days})
                    cash += proceeds; shares = 0
                    if verbose: print(f"[{exit_reason}] {str(date)[:10]} @{close:.2f} 盈亏{pnl:+.0f}({pnl_pct*100:+.1f}%)")

        # ---- 空仓买入 ----
        if shares == 0 and i >= 60:
            price = close
            dd = (hi10.iloc[i]-price)/hi10.iloc[i]
            above60 = price >= ma60.iloc[i]
            dsa_ok = dsascore.iloc[i] >= DSA_MIN
            near_ma10 = price <= ma10.iloc[i]*NEAR_MA10_X
            near_ma5 = price <= ma5.iloc[i]*NEAR_MA5_X
            expand = not np.isnan(res20.iloc[i]) and not np.isnan(vol_ma20.iloc[i]) and \
                     close > res20.iloc[i] and vol > vol_ma20.iloc[i]*1.5
            # 左侧低吸 OR 放量突破(右侧追强)
            signal = (dd >= DD_MIN and above60 and dsa_ok and (near_ma5 or near_ma10)) or \
                     (expand and above60 and dsa_ok)
            if signal and not is_limit_up(row["prev_close"], close):
                # 满手(整百股, 占可用95%)
                buy_shares = int(cash*0.95/(close*100))*100
                if buy_shares >= 100:
                    cost = buy_cost(buy_shares*close)
                    cash -= buy_shares*close + cost
                    shares = buy_shares
                    entry_price = close; entry_idx = i; peak_close = close
                    tag = "低吸" if (dd>=DD_MIN and near_ma5 or near_ma10) else "突破"
                    if verbose: print(f"[买{tag}] {str(date)[:10]} @{close:.2f} dd{dd*100:.1f}% DSA{dsascore.iloc[i]:.0f} 买{buy_shares}")

        total = cash + shares*close
        equity.append(total); returns.append(total/prev_eq-1 if prev_eq>0 else 0); prev_eq=total

    if shares > 0:
        close = df["close"].iloc[-1]; date = df["date"].iloc[-1]
        pnl_pct = close/entry_price-1
        proceeds = shares*close - sell_cost(shares*close)
        pnl = proceeds - entry_price*shares
        trades.append({"type":"sell","reason":"期末平仓","date":date,"price":close,
                       "shares":shares,"pnl":pnl,"pnl_pct":pnl_pct,
                       "hold_days":len(df)-1-entry_idx})
        cash += proceeds; shares = 0
        equity[-1] = cash

    result = BacktestResult(equity=pd.Series(equity,index=df["date"][:len(equity)],name="equity"),
                            trades=trades,
                            returns=pd.Series(returns,index=df["date"][:len(returns)],name="returns"))
    result.metrics = result.summary()
    result._final_equity = equity[-1]
    return result


def fmt_pct(v):
    try: return float(str(v).rstrip('%'))
    except: return 0.0

def main():
    import sys as _s
    args = _s.argv[1:]
    cash = INIT_CASH
    codes = []
    i = 0
    while i < len(args):
        if args[i] == "--cash" and i+1 < len(args):
            cash = float(args[i+1]); i += 2
        else: codes.append(args[i]); i += 1
    targets = {c: STOCKS[c] for c in (codes or STOCKS.keys()) if c in STOCKS}
    print(f"积极版策略 3年回测 (初始¥{cash:,.0f})  区间 2023-09-06→2026-09-04")
    print(f"规则: 低吸(回撤5%)或放量突破入场 + 止损-7% + 浮盈8%后移动止损10%/破MA60 + 最长60天")
    print()
    print(f"{'标的':<8}{'积极累计':>9}{'方案A':>9}{'买入持有':>10}{'积极回撤':>10}{'方案A回撤':>11}{'积极夏普':>9}{'交易':>6}")
    print("-"*80)
    # 加载方案A结果(重跑)
    from backtest_planA_3y import backtest_planA
    rows=[]
    for code,name in targets.items():
        df = load_data(code,name); df["date"]=pd.to_datetime(df["date"])
        df = df[df["date"]>=pd.to_datetime(START)].reset_index(drop=True)
        if len(df)<200: continue
        agg = backtest_aggressive(df, init_cash=cash)
        plana = backtest_planA(df, init_cash=cash)
        ma = agg.metrics; mp = plana.metrics
        agg_ret=fmt_pct(ma['累计收益']); plana_ret=fmt_pct(mp['累计收益'])
        agg_dd=fmt_pct(ma['最大回撤']); plana_dd=fmt_pct(mp['最大回撤'])
        agg_sh=fmt_pct(ma['夏普比率'])
        nt=len([t for t in agg.trades if t['type']=='sell'])
        print(f"{name:<8}{agg_ret:>+8.1f}%{plana_ret:>+8.1f}%{'—':>10}{agg_dd:>+9.1f}%{plana_dd:>+10.1f}%{agg_sh:>9.2f}{nt:>6}")
        rows.append((name,agg_ret,agg_dd,agg_sh))
    print("-"*80)
    import numpy as np
    if rows:
        print(f"{'平均':<8}{np.mean([r[1] for r in rows]):>+8.1f}%  (积极)  |  回撤均值 {np.mean([r[2] for r in rows]):+.1f}%  夏普均值 {np.mean([r[3] for r in rows]):.2f}")

if __name__ == "__main__":
    main()
