"""
方案A 左侧低吸策略 · 3年日线回测 (同花顺数据源)
================================================
忠实复现 Omi 最新买卖策略(方案A 左侧挂单式低吸):
- 买入(低吸): 从10日高点回撤>=5% + 站上MA60 + DSA A/B级(>=65) + 现价接近MA5/MA10(<=MA10*1.03 或 <=MA5*1.02)
              -> 一手试探100股(SIG-010, 单次只持一手)
- 止损: 跌破买入价*(1-0.045) -> 离场
- 止盈: 盈利>=+8% -> 离场
- 最长持仓: 20个交易日
- T+1: 当日买入不可当日卖
- 涨跌停: 涨停(无法买入)/跌停(无法卖出)按前收盘判断
- 费用: 佣金万2.5双边 + 印花税千0.5卖出 + 过户费万0.1

DSA评分(逐日重算, 5维度满分100):
  均线结构60(现价>MA5+15/MA5>MA10+10/MA10>MA20+10/现价>MA20+10/现价>MA60+15)
  + 完美多头排列15(现价>MA5>MA10>MA20>MA60)
  + 60日位置15
  + 量能10(缩量=vol<volma20)
  + 20日趋势15(现价>20日前收盘)
  评级: S>=90 / A 80-89 / B 65-79 / C 50-64 / D<50

用法: .venv/bin/python backtest_planA_3y.py [代码] [--start 2023-09-06]
数据: 读 data/{code}_{name}.csv (同花顺API已拉, 5年前复权)
输出: stdout指标 + results/planA_3y_{code}.html + results/planA_3y_all.html
"""
import sys
import os
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd

from strategies.ma_strategy import load_data, BacktestResult

# 自选9只
STOCKS = {
    "603380": "易德龙", "600988": "赤峰黄金", "600460": "士兰微",
    "600522": "中天科技", "002156": "通富微电", "601138": "工业富联",
    "000938": "紫光股份", "600487": "亨通光电", "002396": "星网锐捷",
}

# ---- 方案A参数 ----
DD_MIN = 0.05          # 从10日高回撤>=5%触发低吸
MA60_ABOVE = True      # 需站上MA60
DSA_MIN = 65           # DSA A/B级 (>=65)
NEAR_MA10_X = 1.03     # 现价<=MA10*1.03
NEAR_MA5_X = 1.02      # 或<=MA5*1.02
STOP_LOSS = 0.045      # 止损-4.5%
TAKE_PROFIT = 0.08     # 止盈+8%
MAX_HOLD = 20          # 最长持仓20交易日
LOT = 100              # 一手100股
INITIAL_CASH = 100_000.0

from strategies import buy_cost, sell_cost, is_limit_up, is_limit_down


def dsa_score_series(df: pd.DataFrame) -> pd.Series:
    """逐日重算 DSA 评分(5维度满分100). 返回每行对应的分数."""
    c = df["close"]
    ma5 = c.rolling(5).mean(); ma10 = c.rolling(10).mean()
    ma20 = c.rolling(20).mean(); ma60 = c.rolling(60).mean()
    vol_ma = df["volume"].rolling(20).mean().shift(1)

    score = pd.Series(0.0, index=df.index)
    score += (c > ma5) * 15
    score += (ma5 > ma10) * 10
    score += (ma10 > ma20) * 10
    score += (c > ma20) * 10
    score += (c > ma60) * 15
    # 完美多头排列
    perfect = (c > ma5) & (ma5 > ma10) & (ma10 > ma20) & (ma20 > ma60)
    score += perfect * 15
    # 60日位置
    lo60 = df["low"].rolling(60).min()
    hi60 = df["high"].rolling(60).max()
    rng = (hi60 - lo60)
    score += ((c - lo60) / rng * 15).fillna(7.5).where(rng > 0, 7.5)
    # 量能: 缩量=10分, 温和=5, 放量=2
    last_v = df["volume"]
    vm = vol_ma
    vol_score = pd.Series(2.0, index=df.index)
    vol_score = np.where(last_v < vm, 10, np.where(last_v < vm * 1.5, 5, 2))
    score += pd.Series(vol_score, index=df.index)
    # 20日趋势
    c20 = c.shift(20)
    score += np.where(c > c20, 15, np.where(c > c.shift(10), 7, 3))
    return score


def backtest_planA(df: pd.DataFrame, verbose=False, init_cash: float = INITIAL_CASH) -> BacktestResult:
    """方案A 左侧低吸 日线回测."""
    df = df.copy().sort_values("date").reset_index(drop=True)
    c = df["close"].astype(float)
    ma5 = c.rolling(5).mean()
    ma10 = c.rolling(10).mean()
    ma60 = c.rolling(60).mean()
    # 10日最高(不含当日, shift避免未来函数)
    hi10 = df["high"].astype(float).rolling(10).max().shift(1)
    dsascore = dsa_score_series(df)
    df["prev_close"] = c.shift(1)

    cash = init_cash
    shares = 0
    entry_price = 0.0
    entry_idx = -1
    entry_date = None
    trades = []
    equity = []
    returns = []
    prev_eq = INITIAL_CASH

    for i in range(len(df)):
        row = df.iloc[i]
        date, close = row["date"], row["close"]
        # 均线需有效
        if i < 60 or np.isnan(ma60.iloc[i]) or np.isnan(hi10.iloc[i]):
            total = cash + shares * close
            equity.append(total)
            returns.append(total / prev_eq - 1 if prev_eq > 0 else 0)
            prev_eq = total
            continue

        # ---- 持仓离场检查 ----
        if shares > 0:
            hold_days = i - entry_idx
            pnl_pct = close / entry_price - 1
            # T+1: 买入次日才能卖
            can_sell = hold_days >= 1
            exit_reason = None
            if can_sell and not is_limit_down(row["prev_close"], close):
                if close <= entry_price * (1 - STOP_LOSS):
                    exit_reason = "止损"
                elif pnl_pct >= TAKE_PROFIT:
                    exit_reason = "止盈"
                elif hold_days >= MAX_HOLD:
                    exit_reason = "到期"
            if exit_reason:
                proceeds = shares * close - sell_cost(shares * close)
                pnl = proceeds - entry_price * shares
                trades.append({
                    "type": "sell", "reason": exit_reason, "date": date, "price": close,
                    "shares": shares, "pnl": pnl, "pnl_pct": pnl / (entry_price * shares),
                    "hold_days": hold_days,
                })
                cash += proceeds
                shares = 0
                if verbose:
                    print(f"[{exit_reason}] {str(date)[:10]} @{close:.2f} 盈亏{pnl:+.0f}")

        # ---- 空仓买入信号 (方案A左侧低吸) ----
        if shares == 0 and i >= 60 and not np.isnan(ma60.iloc[i]) and not np.isnan(ma10.iloc[i]):
            price = close
            dd = (hi10.iloc[i] - price) / hi10.iloc[i]
            above60 = price >= ma60.iloc[i]
            dsa_ok = dsascore.iloc[i] >= DSA_MIN
            near_ma10 = price <= ma10.iloc[i] * NEAR_MA10_X
            near_ma5 = price <= ma5.iloc[i] * NEAR_MA5_X
            # 左侧低吸触发
            if dd >= DD_MIN and above60 and dsa_ok and (near_ma5 or near_ma10):
                if not is_limit_up(row["prev_close"], close):
                    # 一手试探100股
                    buy_shares = LOT
                    cost = buy_cost(buy_shares * close)
                    if buy_shares * close + cost <= cash:
                        cash -= buy_shares * close + cost
                        shares = buy_shares
                        entry_price = close
                        entry_idx = i
                        entry_date = date
                        if verbose:
                            print(f"[低吸买] {str(date)[:10]} @{close:.2f} 回撤{dd*100:.1f}% DSA{dsascore.iloc[i]:.0f} 买{buy_shares}股")

        total = cash + shares * close
        equity.append(total)
        returns.append(total / prev_eq - 1 if prev_eq > 0 else 0)
        prev_eq = total

    # 期末强制平仓
    if shares > 0:
        close = df["close"].iloc[-1]
        date = df["date"].iloc[-1]
        proceeds = shares * close - sell_cost(shares * close)
        pnl = proceeds - entry_price * shares
        trades.append({
            "type": "sell", "reason": "期末平仓", "date": date, "price": close,
            "shares": shares, "pnl": pnl, "pnl_pct": pnl / (entry_price * shares),
            "hold_days": len(df) - 1 - entry_idx,
        })
        cash += proceeds
        shares = 0
        equity[-1] = cash

    result = BacktestResult(
        equity=pd.Series(equity, index=df["date"][:len(equity)], name="equity"),
        trades=trades,
        returns=pd.Series(returns, index=df["date"][:len(returns)], name="returns"),
    )
    result.metrics = result.summary()
    # 补充: 期末总资产
    result._final_equity = equity[-1]
    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    start_default = "2023-09-06"
    start = start_default
    init_cash = INITIAL_CASH
    codes = []
    i = 0
    while i < len(args):
        if args[i] == "--start" and i + 1 < len(args):
            start = args[i + 1]; i += 2
        elif args[i] == "--cash" and i + 1 < len(args):
            init_cash = float(args[i + 1]); i += 2
        else:
            codes.append(args[i]); i += 1
    targets = {c: STOCKS[c] for c in (codes or STOCKS.keys()) if c in STOCKS}
    if not targets:
        print("无有效标的"); sys.exit(1)
    all_rows = []
    for code, name in targets.items():
        df = load_data(code, name)
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"] >= pd.to_datetime(start)].reset_index(drop=True)
        print(f"\n===== {name} ({code}) {df['date'].iloc[0].date()}→{df['date'].iloc[-1].date()} {len(df)}日 =====")
        res = backtest_planA(df, verbose=True, init_cash=init_cash)
        m = res.metrics
        print(f"  期末总资产: {res._final_equity:,.0f}  累计: {m['累计收益']}")
        print(f"  年化: {m['年化收益']} 回撤: {m['最大回撤']} 夏普: {m['夏普比率']}")
        print(f"  胜率: {m['胜率']} 交易: {m['交易次数']}")
        all_rows.append({"code": code, "name": name, "equity": res._final_equity,
                         "trades": res.trades, "df": df, "res": res})
