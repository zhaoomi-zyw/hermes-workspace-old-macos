"""
DSA 参数敏感性分析 · 最近120交易日
================================
对紫金/工业富联/亨通，测试多组参数，寻找更适合中短线做T的组合。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd

from strategies.dsa_strategy import backtest_dsa, DSAConfig
from strategies.ma_strategy import load_data

STOCKS = {
    "601899": "紫金矿业",
    "601138": "工业富联",
    "600487": "亨通光电",
}
LOOKBACK_DAYS = 120
INITIAL_CASH = 100_000.0

# 测试的参数组合
PARAM_SETS = {
    "当前默认(防守型)": dict(stop_loss=0.07, trend_exit_ma=60, profit_lock=0.03, trailing_stop=0.05, exit_mode="trend"),
    "放宽止损":     dict(stop_loss=0.10, trend_exit_ma=60, profit_lock=0.03, trailing_stop=0.05, exit_mode="trend"),
    "快均线离场":   dict(stop_loss=0.07, trend_exit_ma=30, profit_lock=0.02, trailing_stop=0.05, exit_mode="trend"),
    "收紧移动止损": dict(stop_loss=0.07, trend_exit_ma=60, profit_lock=0.03, trailing_stop=0.03, exit_mode="trend"),
    "放宽+快均线":  dict(stop_loss=0.10, trend_exit_ma=30, profit_lock=0.02, trailing_stop=0.03, exit_mode="trend"),
    "固定止盈模式": dict(stop_loss=0.07, exit_mode="target", tp1=0.10, tp2=0.20),
    "止盈收紧":     dict(stop_loss=0.07, exit_mode="target", tp1=0.06, tp2=0.12),
}

def main():
    print("="*90)
    print(f"DSA 参数敏感性分析 · 最近{LOOKBACK_DAYS}交易日 · 初始{INITIAL_CASH:,.0f}")
    print("="*90)
    for code, name in STOCKS.items():
        df = load_data(code, name).tail(LOOKBACK_DAYS).reset_index(drop=True)
        print(f"\n===== {name} ({code}) =====")
        print(f"  {'参数组合':<16s}{'累计':>9s}{'年化':>9s}{'回撤':>9s}{'夏普':>7s}{'胜率':>7s}{'交易':>5s}")
        for pname, overrides in PARAM_SETS.items():
            cfg = DSAConfig(initial_cash=INITIAL_CASH, **overrides)
            r = backtest_dsa(df, cfg)
            m = r.metrics
            def pct(v):
                try: return float(str(v).rstrip('%'))
                except: return 0.0
            print(f"  {pname:<16s}{pct(m['累计收益']):>+8.1f}%{pct(m['年化收益']):>+8.1f}%"
                  f"{pct(m['最大回撤']):>+8.1f}%{pct(m['夏普比率']):>7.2f}{pct(m['胜率']):>6.1f}%{m['交易次数']:>5d}")

if __name__ == "__main__":
    main()
