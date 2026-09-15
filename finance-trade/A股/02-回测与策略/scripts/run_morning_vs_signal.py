"""
晨间DSA规则 vs signal_daily优化参数 · 120天对比回测
==================================================
晨间DSA规则(cron 0d1bb1811d94): 20日支撑/压力 + 从近20日高点回撤8%移动止盈
signal_daily优化参数: 紫金固定止盈 / 工业富联MA30+移动止损3%
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd

from strategies.dsa_strategy import backtest_dsa, DSAConfig
from strategies.ma_strategy import load_data, BacktestResult
from run_backtest import buy_hold

STOCKS = {"601899": "紫金矿业", "601138": "工业富联"}
LOOKBACK = 120
CASH = 100_000.0


def backtest_morning(df, cfg, lookback=20, pullback=0.08):
    """晨间DSA规则: 20日支撑/压力 + 回踩低吸/突破买入 + 从20日高点回撤8%离场"""
    df = df.copy().sort_values("date").reset_index(drop=True)
    df["support"] = df["low"].rolling(lookback, min_periods=lookback).min().shift(1)
    df["resistance"] = df["high"].rolling(lookback, min_periods=lookback).max().shift(1)
    df["vol_ma"] = df["volume"].rolling(cfg.vol_window, min_periods=1).mean()
    df["prev_close"] = df["close"].shift(1)
    # 近20日高点(含当日)用于回撤止盈
    df["high20"] = df["high"].rolling(lookback, min_periods=1).max()

    cash = CASH
    shares = 0
    entry_price = 0.0
    entry_date = None
    high_since_entry = 0.0
    trades = []
    equity = []
    prev_eq = CASH
    returns = []

    from strategies import is_limit_up
    for i in range(len(df)):
        row = df.iloc[i]
        date, close, low, high, vol = row["date"], row["close"], row["low"], row["high"], row["volume"]
        support, resistance = row["support"], row["resistance"]
        has_sr = not np.isnan(support) and not np.isnan(resistance)

        if shares > 0:
            high_since_entry = max(high_since_entry, high)
            # 从近20日高点回撤8% → 离场
            if close <= high_since_entry * (1 - pullback):
                proceeds = shares * close  # 简化费用
                pnl = proceeds - entry_price * shares
                trades.append({"type":"sell","reason":"回撤8%","date":date,"price":close,
                               "shares":shares,"pnl":pnl,"pnl_pct":pnl/(entry_price*shares),"hold_days":(date-entry_date).days})
                cash += proceeds
                shares = 0

        if shares == 0 and has_sr:
            shrink = vol < df["vol_ma"].iloc[i] * cfg.shrink_coef
            # 突破压力买入
            if close > resistance:
                if not is_limit_up(row["prev_close"], close):
                    bs = int(cash*0.95/(close*100))*100
                    if bs >= 100:
                        cash -= bs*close; shares=bs; entry_price=close; entry_date=date; high_since_entry=close
            # 回踩支撑缩量低吸
            elif low <= support*1.02 and shrink:
                if not is_limit_up(row["prev_close"], close):
                    bs = int(cash*0.5/(close*100))*100
                    if bs >= 100:
                        cash -= bs*close; shares=bs; entry_price=close; entry_date=date; high_since_entry=close

        total = cash + shares*close
        equity.append(total)
        returns.append(total/prev_eq-1 if prev_eq>0 else 0)
        prev_eq = total

    res = BacktestResult(equity=pd.Series(equity,index=df["date"]),
                         trades=trades,
                         returns=pd.Series(returns,index=df["date"]))
    res.metrics = res.summary()
    return res


def main():
    print("="*78)
    print(f"晨间DSA规则 vs signal_daily优化参数 · 120交易日 · 初始{CASH:,.0f}")
    print("="*78)
    rows = []
    for code, name in STOCKS.items():
        df = load_data(code, name).tail(LOOKBACK).reset_index(drop=True)
        print(f"\n===== {name} ({code}) 窗口 {df['date'].iloc[0].date()} → {df['date'].iloc[-1].date()} =====")

        bh = buy_hold(df, CASH)
        # signal_daily 优化参数
        opt_cfg = DSAConfig(initial_cash=CASH, exit_mode="target", tp1=0.10, tp2=0.20, stop_loss=0.07) if code=="601899" \
            else DSAConfig(initial_cash=CASH, exit_mode="trend", stop_loss=0.10, trend_exit_ma=30, profit_lock=0.02, trailing_stop=0.03)
        sig = backtest_dsa(df, opt_cfg)
        # 晨间规则
        morn = backtest_morning(df, DSAConfig(initial_cash=CASH))

        def g(m):
            return (m['累计收益'], m['最大回撤'], m['夏普比率'], m['胜率'], m['交易次数'])
        def pct(v):
            try: return float(str(v).rstrip('%'))
            except: return 0.0
        bhr, bhs = pct(bh['累计收益']), pct(bh['最大回撤'])
        sc, sd, ssh, sw, st = g(sig.metrics)
        mc, md, msh, mw, mt = g(morn.metrics)

        print(f"  买入持有          : 累计{bhr:>+8.1f}% 回撤{bhs:>+8.1f}%")
        print(f"  signal_daily优化 : 累计{pct(sc):>+8.1f}% 回撤{pct(sd):>+8.1f}% 夏普{pct(ssh):>5.2f} 胜率{pct(sw):>5} 交易{st}")
        print(f"  晨间DSA规则      : 累计{pct(mc):>+8.1f}% 回撤{pct(md):>+8.1f}% 夏普{pct(msh):>5.2f} 胜率{pct(mw):>5} 交易{mt}")
        if sig.trades:
            print("  [signal_daily交易]")
            for t in sig.trades:
                print(f"    {str(t['date'])[:10]} {t['reason']} @{t['price']:.2f} 盈亏{t['pnl']:+.0f}({t['pnl_pct']*100:+.1f}%)")
        if morn.trades:
            print("  [晨间DSA交易]")
            for t in morn.trades:
                print(f"    {str(t['date'])[:10]} {t['reason']} @{t['price']:.2f} 盈亏{t['pnl']:+.0f}({t['pnl_pct']*100:+.1f}%)")
        rows.append({"股票":name,"买入持有累计":bhr,"signal优化累计":sc,"signal回撤":sd,
                     "晨间DSA累计":mc,"晨间回撤":md,"晨间夏普":msh,"晨间胜率":mw,"晨间交易":mt})

    out = Path("results/morning_vs_signal_120d.csv")
    out.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_csv(out, index=False)
    print(f"\n📁 已保存: {out}")

if __name__ == "__main__":
    main()
