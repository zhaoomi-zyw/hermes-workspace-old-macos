"""
DSA 策略回测 · 最近120交易日
============================
对紫金矿业/工业富联/亨通光电 三只，用最近120个交易日跑 DSA 策略，
与买入持有对比。
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd

from strategies.dsa_strategy import backtest_dsa, DSAConfig
from strategies.ma_strategy import load_data
from run_backtest import buy_hold

STOCKS = {
    "601899": "紫金矿业",
    "601138": "工业富联",
    "600487": "亨通光电",
}
LOOKBACK_DAYS = 120
INITIAL_CASH = 100_000.0

def main():
    results = []
    print("="*70)
    print(f"DSA 策略回测 · 最近 {LOOKBACK_DAYS} 交易日 · 初始资金 {INITIAL_CASH:,.0f}")
    print("="*70)
    for code, name in STOCKS.items():
        path = f"data/{code}_{name}.csv"
        if not Path(path).exists():
            print(f"⚠️ 缺少 {path}")
            continue
        df = load_data(code, name)
        # 取最近120个交易日
        df = df.tail(LOOKBACK_DAYS).reset_index(drop=True)
        print(f"\n===== {name} ({code}) | 回测窗口 {df['date'].iloc[0]} → {df['date'].iloc[-1]} | {len(df)}日 =====")

        bh = buy_hold(df, INITIAL_CASH)
        dsa = backtest_dsa(df, DSAConfig(initial_cash=INITIAL_CASH, exit_mode="trend"))

        print(f"  买入持有 : 累计{bh['累计收益']} 年化{bh['年化收益']} 最大回撤{bh['最大回撤']}")
        m = dsa.metrics
        print(f"  DSA趋势  : 累计{m['累计收益']} 年化{m['年化收益']} 回撤{m['最大回撤']} "
              f"夏普{m['夏普比率']} 胜率{m['胜率']} 交易{m['交易次数']}次")
        print(f"  [DSA明细交易]")
        for t in dsa.trades:
            print(f"    {t['date']} {t['type']}({t.get('reason','')}) @{t['price']:.2f} "
                  f"x{t['shares']} 盈亏{t['pnl']:+.0f} ({t['pnl_pct']*100:+.1f}%)")

        results.append({
            "股票": name, "代码": code,
            "回测起始": df['date'].iloc[0], "回测结束": df['date'].iloc[-1],
            "窗口天数": len(df),
            "买入持有累计": bh['累计收益'], "买入持有年化": bh['年化收益'],
            "DSA累计收益": m['累计收益'], "DSA年化": m['年化收益'],
            "DSA最大回撤": m['最大回撤'], "DSA夏普": m['夏普比率'],
            "DSA胜率": m['胜率'], "DSA交易次数": m['交易次数'],
        })

    if results:
        out = Path("results/dsa_120d_backtest.csv")
        out.parent.mkdir(exist_ok=True)
        pd.DataFrame(results).to_csv(out, index=False)
        print(f"\n📁 报告已保存: {out}")

if __name__ == "__main__":
    main()
