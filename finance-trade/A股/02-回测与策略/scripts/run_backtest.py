"""
运行 MA 均线策略回测 · 输出对比报告
====================================
对每只股票跑 MA5/10 金叉策略，并与"买入持有"基准对比。

用法:
    python run_backtest.py
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pandas as pd

from strategies.ma_strategy import backtest_ma, load_data

STOCKS = {
    "601138": "工业富联",
    "600487": "亨通光电",
    "000938": "紫光股份",
    "600570": "恒生电子",
}
INITIAL_CASH = 100_000.0


def buy_hold(df: pd.DataFrame, cash: float) -> dict:
    """买入持有基准: 第一天全仓买入到最后"""
    df = df.sort_values("date").reset_index(drop=True)
    first_close = df["close"].iloc[0]
    shares = int(cash / (first_close * 100)) * 100
    final_close = df["close"].iloc[-1]
    total_return = shares * final_close / cash - 1
    years = len(df) / 252
    annual = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
    cummax = (df["close"] * shares).cummax()
    max_dd = ((df["close"] * shares) / cummax - 1).min()
    return {"累计收益": f"{total_return*100:.2f}%", "年化收益": f"{annual*100:.2f}%",
            "最大回撤": f"{max_dd*100:.2f}%"}


def main():
    results = []
    for code, name in STOCKS.items():
        path = f"data/{code}_{name}.csv"
        if not os.path.exists(path):
            print(f"⚠️ 缺少数据 {path}，请先运行 python fetch_data.py")
            continue
        df = load_data(code, name)
        print(f"\n===== {name} ({code}) | {len(df)} 个交易日 =====")

        bh = buy_hold(df, INITIAL_CASH)
        print(f"  买入持有: 累计{bh['累计收益']} 年化{bh['年化收益']} 回撤{bh['最大回撤']}")

        res = backtest_ma(df, fast=5, slow=10, initial_cash=INITIAL_CASH)
        m = res.metrics
        print(f"  MA5/10  : 累计{m['累计收益']} 年化{m['年化收益']} 回撤{m['最大回撤']} "
              f"夏普{m['夏普比率']} 交易{m['交易次数']}次 胜率{m['胜率']}")

        results.append({"股票": name, "代码": code, **{f"策略_{k}": v for k, v in m.items()},
                        **{f"基准_{k}": v for k, v in bh.items()}})

    if results:
        df_out = pd.DataFrame(results)
        out = Path("results/ma5_10_backtest_report.csv")
        out.parent.mkdir(exist_ok=True)
        df_out.to_csv(out, index=False)
        print(f"\n📁 报告已保存: {out}")


if __name__ == "__main__":
    main()
