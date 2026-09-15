"""
MA 均线趋势策略 · 回测引擎
==========================
策略: MA5/MA10 金叉买入、死叉卖出。
融入 A股约束: T+1、涨跌停、交易费用。

用纯 pandas 实现，逻辑透明可控，便于后续加入 DSA 规则。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from strategies import buy_cost, sell_cost, is_limit_up, is_limit_down


@dataclass
class BacktestResult:
    equity: pd.Series          # 每日总资产
    trades: list[dict]         # 每笔交易记录
    returns: pd.Series         # 每日收益率
    metrics: dict = field(default_factory=dict)

    def summary(self) -> dict:
        """核心绩效指标"""
        eq = self.equity
        total_return = eq.iloc[-1] / eq.iloc[0] - 1
        years = len(eq) / 252
        annual_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
        daily_ret = self.returns
        sharpe = daily_ret.mean() / daily_ret.std() * np.sqrt(252) if daily_ret.std() > 0 else 0

        # 最大回撤
        cummax = eq.cummax()
        drawdown = eq / cummax - 1
        max_drawdown = drawdown.min()

        # 交易统计
        closes = [t for t in self.trades if t["type"] == "sell"]
        pnls = [t["pnl"] for t in closes] if closes else [0]
        wins = [p for p in pnls if p > 0]
        win_rate = len(wins) / len(pnls) if pnls else 0

        return {
            "累计收益": f"{total_return*100:.2f}%",
            "年化收益": f"{annual_return*100:.2f}%",
            "最大回撤": f"{max_drawdown*100:.2f}%",
            "夏普比率": f"{sharpe:.2f}",
            "交易次数": len(self.trades),
            "胜率": f"{win_rate*100:.1f}%" if closes else "N/A",
            "平均盈利": f"{np.mean(wins)*100:.2f}%" if wins else "N/A",
            "平均亏损": f"{np.mean([p for p in pnls if p<0])*100:.2f}%" if any(p<0 for p in pnls) else "N/A",
        }


def backtest_ma(
    df: pd.DataFrame,
    fast: int = 5,
    slow: int = 10,
    initial_cash: float = 100_000.0,
    verbose: bool = False,
) -> BacktestResult:
    """
    均线金叉/死叉策略回测。

    参数:
        df: 含 open/high/low/close/prev_close 的日线数据(已按日期升序)
        fast/slow: 快慢均线周期
        initial_cash: 初始资金
    """
    df = df.copy().sort_values("date").reset_index(drop=True)

    # 均线 + 前收盘(用于涨跌停判断)
    df["ma_fast"] = df["close"].rolling(fast).mean()
    df["ma_slow"] = df["close"].rolling(slow).mean()
    df["prev_close"] = df["close"].shift(1)

    cash = initial_cash
    shares = 0
    entry_price = 0.0
    entry_date = None
    trades = []
    equity = []
    prev_equity = initial_cash
    returns = []

    for i in range(len(df)):
        row = df.iloc[i]
        date, close = row["date"], row["close"]
        prev_ma_fast = df["ma_fast"].iloc[i - 1] if i > 0 else np.nan
        prev_ma_slow = df["ma_slow"].iloc[i - 1] if i > 0 else np.nan

        # 金叉信号: 昨日MAfast<=MAslow 且 今日MAfast>MAslow
        golden = (
            not np.isnan(prev_ma_fast)
            and not np.isnan(prev_ma_slow)
            and prev_ma_fast <= prev_ma_slow
            and df["ma_fast"].iloc[i] > df["ma_slow"].iloc[i]
        )
        # 死叉信号
        death = (
            not np.isnan(prev_ma_fast)
            and not np.isnan(prev_ma_slow)
            and prev_ma_fast >= prev_ma_slow
            and df["ma_fast"].iloc[i] < df["ma_slow"].iloc[i]
        )

        # 买入: 金叉 + 空仓 + 非涨停(用昨日收盘判断是否触及涨停)
        if golden and shares == 0:
            if not is_limit_up(row["prev_close"], close):
                shares = int(cash / (close * 100)) * 100  # A股整手(100股)
                if shares > 0:
                    cost = buy_cost(shares * close)
                    cash -= shares * close + cost
                    entry_price = close
                    entry_date = date
                    if verbose:
                        print(f"[买入] {date} @ {close:.2f}  {shares}股")

        # 卖出: 死叉 + 持仓 + 非跌停 + 非当日买入(T+1)
        elif death and shares > 0:
            if entry_date != date and not is_limit_down(row["prev_close"], close):
                proceeds = shares * close - sell_cost(shares * close)
                pnl = proceeds - entry_price * shares
                trades.append({
                    "type": "sell", "date": date, "price": close,
                    "shares": shares, "pnl": pnl, "pnl_pct": pnl / (entry_price * shares),
                    "hold_days": (date - entry_date).days,
                })
                cash += proceeds
                shares = 0
                if verbose:
                    print(f"[卖出] {date} @ {close:.2f}  PnL {pnl:+.0f} ({pnl/(entry_price*shares)*100:+.2f}%)")

        # 记录每日总资产
        total = cash + shares * close
        equity.append(total)
        returns.append(total / prev_equity - 1 if prev_equity > 0 else 0)
        prev_equity = total

    # 末了强平(可选, 保留持仓市值计入equity即可)
    result = BacktestResult(
        equity=pd.Series(equity, index=df["date"], name="equity"),
        trades=trades,
        returns=pd.Series(returns, index=df["date"], name="returns"),
    )
    result.metrics = result.summary()
    return result


def load_data(code: str, name: str, data_dir="data") -> pd.DataFrame:
    """加载 CSV 并保证列齐全"""
    import os
    path = os.path.join(data_dir, f"{code}_{name}.csv")
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df
