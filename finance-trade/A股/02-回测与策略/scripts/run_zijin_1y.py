"""
紫金矿业 1年回测 · DSA固定止盈模式 vs 买入持有
============================================
1年(约240+交易日)窗口，用紫金优化参数(固定止盈)回测
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd

from strategies.dsa_strategy import backtest_dsa, DSAConfig
from strategies.ma_strategy import load_data
from run_backtest import buy_hold

code, name = "601899", "紫金矿业"
YEARS = 1  # 回看1年
CASH = 100_000.0

def main():
    df = load_data(code, name)
    # 取最近约1年(250个交易日，留余量给均线计算)
    df = df.tail(260).reset_index(drop=True)
    # 报告用最近1年(240个交易日)做统计窗口
    report_df = df.tail(240)
    
    print("="*70)
    print(f"紫金矿业({code}) 1年回测 · 窗口 {report_df['date'].iloc[0].date()} → {report_df['date'].iloc[-1].date()}")
    print(f"初始资金 {CASH:,.0f} · DSA用固定止盈模式(紫金优化参数)")
    print("="*70)

    # 买入持有(整个df窗口)
    bh_full = buy_hold(report_df, CASH)
    
    # DSA固定止盈模式(紫金优化参数)
    cfg = DSAConfig(initial_cash=CASH, exit_mode="target", tp1=0.10, tp2=0.20, stop_loss=0.07)
    dsa = backtest_dsa(df, cfg)  # 用全df算(含均线预热)，但统计用report窗口的净值
    # 截取report窗口的净值
    eq = dsa.equity
    eq_rep = eq.loc[report_df['date'].iloc[0]:]
    # 重算DSA指标(基于report窗口)
    dsa.equity = eq_rep
    dsa.returns = dsa.returns.loc[report_df['date'].iloc[0]:]
    dsa.metrics = dsa.summary()

    print(f"\n【买入持有】")
    print(f"  累计: {bh_full['累计收益']}  年化: {bh_full['年化收益']}  最大回撤: {bh_full['最大回撤']}")

    print(f"\n【DSA固定止盈】")
    m = dsa.metrics
    print(f"  累计: {m['累计收益']}  年化: {m['年化收益']}  最大回撤: {m['最大回撤']}")
    print(f"  夏普: {m['夏普比率']}  胜率: {m['胜率']}  交易: {m['交易次数']}次")
    print(f"  平均盈利: {m['平均盈利']}  平均亏损: {m['平均亏损']}")
    
    print(f"\n【DSA明细交易】")
    for t in dsa.trades:
        print(f"  {str(t['date'])[:10]} {t['type']}({t.get('reason','')}) @{t['price']:.2f} "
              f"x{t['shares']} 盈亏{t['pnl']:+.0f}({t['pnl_pct']*100:+.1f}%) 持仓{t['hold_days']}天")

    # 保存
    out = Path("results/zijin_1y_backtest.csv")
    out.parent.mkdir(exist_ok=True)
    pd.DataFrame([{"策略":"买入持有","累计收益":bh_full['累计收益'],"年化收益":bh_full['年化收益'],
                   "最大回撤":bh_full['最大回撤']},
                  {"策略":"DSA固定止盈","累计收益":m['累计收益'],"年化收益":m['年化收益'],
                   "最大回撤":m['最大回撤'],"夏普":m['夏普比率'],"胜率":m['胜率'],"交易次数":m['交易次数']}]
                 ).to_csv(out, index=False)
    print(f"\n📁 已保存: {out}")

if __name__ == "__main__":
    main()
