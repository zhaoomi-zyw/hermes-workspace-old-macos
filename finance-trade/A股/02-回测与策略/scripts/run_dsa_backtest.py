"""
运行 DSA 策略回测 · 与买入持有/MA 三方对比
============================================
用法:
    python run_dsa_backtest.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd

from strategies.ma_strategy import backtest_ma, load_data
from strategies.dsa_strategy import backtest_dsa, DSAConfig
from run_backtest import buy_hold

STOCKS = {
    "601138": "工业富联",
    "600487": "亨通光电",
    "000938": "紫光股份",
    "600570": "恒生电子",
}
INITIAL_CASH = 100_000.0


def main():
    results = []
    for code, name in STOCKS.items():
        path = f"data/{code}_{name}.csv"
        if not Path(path).exists():
            print(f"⚠️ 缺少 {path}")
            continue
        df = load_data(code, name)
        print(f"\n===== {name} ({code}) | {len(df)} 交易日 =====")

        bh = buy_hold(df, INITIAL_CASH)
        ma = backtest_ma(df, 5, 10, INITIAL_CASH)
        dsa_trend = backtest_dsa(df, DSAConfig(initial_cash=INITIAL_CASH, exit_mode="trend"))
        dsa_target = backtest_dsa(df, DSAConfig(initial_cash=INITIAL_CASH, exit_mode="target"))

        print(f"  买入持有: 累计{bh['累计收益']} 年化{bh['年化收益']} 回撤{bh['最大回撤']}")
        print(f"  MA5/10  : 累计{ma.metrics['累计收益']} 年化{ma.metrics['年化收益']} "
              f"回撤{ma.metrics['最大回撤']} 夏普{ma.metrics['夏普比率']} 胜率{ma.metrics['胜率']}")
        print(f"  DSA趋势 : 累计{dsa_trend.metrics['累计收益']} 年化{dsa_trend.metrics['年化收益']} "
              f"回撤{dsa_trend.metrics['最大回撤']} 夏普{dsa_trend.metrics['夏普比率']} 胜率{dsa_trend.metrics['胜率']} "
              f"交易{dsa_trend.metrics['交易次数']}次")
        print(f"  DSA止盈 : 累计{dsa_target.metrics['累计收益']} 年化{dsa_target.metrics['年化收益']} "
              f"回撤{dsa_target.metrics['最大回撤']} 胜率{dsa_target.metrics['胜率']}")

        results.append({
            "股票": name, "代码": code,
            **{f"基准_{k}": v for k, v in bh.items()},
            **{f"MA_{k}": v for k, v in ma.metrics.items()},
            **{f"DSA趋势_{k}": v for k, v in dsa_trend.metrics.items()},
            **{f"DSA止盈_{k}": v for k, v in dsa_target.metrics.items()},
        })

    if results:
        out = Path("results/dsa_backtest_report.csv")
        out.parent.mkdir(exist_ok=True)
        pd.DataFrame(results).to_csv(out, index=False)
        print(f"\n📁 报告已保存: {out}")


if __name__ == "__main__":
    main()
