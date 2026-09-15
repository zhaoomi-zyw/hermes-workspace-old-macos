"""
DSA 策略回测引擎
================
将 Omi 的 DSA 评分体系核心交易规则量化为可回测代码：

- 动态支撑位 = 近 N 日最低价
- 动态压力位 = 近 N 日最高价
- 缩量企稳买入: 价格回踩支撑位 + 成交量萎缩到均量×缩量系数以下 → 建半仓
- 放量突破买入: 收盘突破压力位 + 成交量放大到均量×放量系数以上 → 加满仓
- 止损: 收盘跌破买入价×(1-止损幅度) → 清仓
- 分批止盈: 盈利 +止盈1 卖一半, 再 +止盈2 清仓

参数均可调, 便于做敏感性分析。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from strategies import buy_cost, sell_cost, is_limit_up, is_limit_down
from strategies.ma_strategy import BacktestResult

# 统一卖出策略模块 (唯一权威): 回测退出规则/参数一律取自 sell_policy, 不在此复制
try:
    from strategies import sell_policy as _sellp
    _SP = _sellp.DEFAULT_PARAMS
    SELL_POLICY_AVAIL = True
except Exception:  # pragma: no cover
    _sellp = None
    _SP = None
    SELL_POLICY_AVAIL = False


@dataclass
class DSAConfig:
    lookback: int = 20          # 支撑/压力位回看窗口(入场用)
    vol_window: int = 5         # 均量窗口
    shrink_coef: float = 0.8    # 缩量系数(成交量 < 均量*此值)
    expand_coef: float = 1.5    # 放量系数(成交量 > 均量*此值)
    # 退出参数: 默认从统一模块 sell_policy 派生 (SELL-POLICY-v1.0-20260914)
    stop_loss: float = (_SP.hard_stop_pct if _SP else 0.06)          # R1 硬止损 = C×(1-此值)
    trend_exit_ma: int = 60     # 趋势跟踪离场均线周期(仅趋势提示, R5)
    profit_lock: float = (_SP.profit_activate_pct if _SP else 0.08)  # R3 H≥C×(1+此值)开保护
    trailing_stop: float = (_SP.trail_from_peak_pct if _SP else 0.07)  # R4 H×(1-此值)=保护线
    trend_filter: bool = True   # 趋势过滤: 买入前要求站上趋势均线(排除下跌趋势接飞刀)
    stab_confirm: bool = True   # 企稳确认
    exit_mode: str = "trend"    # "trend"统一sell_policy | "target"固定止盈(遗留)
    tp1: float = 0.10           # target模式第一止盈 (保留, 但趋势股不用)
    tp2: float = 0.20           # target模式第二止盈
    initial_cash: float = 100_000.0


def backtest_dsa(df: pd.DataFrame, cfg: DSAConfig, verbose: bool = False) -> BacktestResult:
    """DSA 策略回测, 支持半仓/满仓。

    exit_mode:
        "trend"  趋势跟踪离场: 盈利后拿住, 跌破 MA(trend_exit_ma) 或动态支撑才清仓
        "target" 固定止盈离场: 达到 tp1/tp2 分批止盈
    """
    df = df.copy().sort_values("date").reset_index(drop=True)

    # 支撑压力位(滚动窗口, 用shift避免未来函数: 当日信号用昨日支撑压力判断) + 均量 + 前收盘 + 趋势均线
    df["support"] = df["low"].rolling(cfg.lookback, min_periods=cfg.lookback).min().shift(1)
    df["resistance"] = df["high"].rolling(cfg.lookback, min_periods=cfg.lookback).max().shift(1)
    df["vol_ma"] = df["volume"].rolling(cfg.vol_window, min_periods=1).mean()
    df["trend_ma"] = df["close"].rolling(cfg.trend_exit_ma, min_periods=cfg.trend_exit_ma).mean()
    df["prev_close"] = df["close"].shift(1)

    cash = cfg.initial_cash
    shares = 0
    entry_price = 0.0
    entry_date = None
    peak_price = 0.0   # 持仓期间最高价(用于移动止损)
    trades = []
    equity = []
    prev_equity = cfg.initial_cash
    returns = []
    pos_state = None  # 本笔持仓的统一模块状态(建仓时创建, 清仓时置 None)

    for i in range(len(df)):
        row = df.iloc[i]
        date, close, low, vol = row["date"], row["close"], row["low"], row["volume"]
        support = row["support"]
        resistance = row["resistance"]

        # 需等支撑压力位充分形成
        has_sr = not np.isnan(support) and not np.isnan(resistance)

        # 持仓状态下的检查: 止损/离场
        if shares > 0 and has_sr:
            pnl_pct = close / entry_price - 1
            trend_ma = row["trend_ma"]
            has_trend = not np.isnan(trend_ma)

            if cfg.exit_mode == "trend" and SELL_POLICY_AVAIL:
                # 统一模块: 用 sell_policy 状态机判定退出(与实盘同一规则)
                if pos_state is None:
                    pos_state = _sellp.init_position(
                        "bt", "backtest", entry_price, shares,
                        entry_date=str(date), params=_SP)
                # 回测每根K线: 用 bar 的 high 更新 H, 用 close 判定退出
                _sellp.update_quote(pos_state, float(row["high"]),
                                    quote_time=str(date), params=_SP)
                ev = _sellp.evaluate_exit(pos_state, close, quote_time=str(date), params=_SP)
                if ev and _sellp.fire_exit(pos_state, ev):
                    proceeds = shares * close - sell_cost(shares * close)
                    pnl = proceeds - entry_price * shares
                    reason = "止损" if ev["reason"] == "硬止损" else "盈利保护"
                    trades.append({
                        "type": "sell", "reason": reason, "date": date, "price": close,
                        "shares": shares, "pnl": pnl, "pnl_pct": pnl / (entry_price * shares),
                        "hold_days": (date - entry_date).days,
                    })
                    cash += proceeds
                    shares = 0
                    pos_state = None
                    if verbose:
                        print(f"[{reason}] {date} @ {close:.2f} PnL {pnl:+.0f} ({pnl_pct*100:+.1f}%)")
            elif cfg.exit_mode == "trend":
                # 兜底: sell_policy 不可用时用旧逻辑(参数已从模块派生)
                peak_price = max(peak_price, close)
                pnl_pct = close / entry_price - 1
                locked = pnl_pct >= cfg.profit_lock
                hard_stop = close <= entry_price * (1 - cfg.stop_loss)
                trailing_hit = locked and close <= peak_price * (1 - cfg.trailing_stop)
                broke_trend = locked and has_trend and close < trend_ma
                if hard_stop or trailing_hit or broke_trend:
                    proceeds = shares * close - sell_cost(shares * close)
                    pnl = proceeds - entry_price * shares
                    if hard_stop:
                        reason = "止损"
                    elif trailing_hit:
                        reason = "移动止损"
                    else:
                        reason = "破趋势"
                    trades.append({
                        "type": "sell", "reason": reason, "date": date, "price": close,
                        "shares": shares, "pnl": pnl, "pnl_pct": pnl / (entry_price * shares),
                        "hold_days": (date - entry_date).days,
                    })
                    cash += proceeds
                    shares = 0
                    if verbose:
                        print(f"[{reason}] {date} @ {close:.2f} PnL {pnl:+.0f} ({pnl_pct*100:+.1f}%)")
            else:
                # 固定止盈离场: 止损 + 分批止盈
                if close <= entry_price * (1 - cfg.stop_loss) or close < support:
                    proceeds = shares * close - sell_cost(shares * close)
                    pnl = proceeds - entry_price * shares
                    trades.append({
                        "type": "sell", "reason": "止损", "date": date, "price": close,
                        "shares": shares, "pnl": pnl, "pnl_pct": pnl / (entry_price * shares),
                        "hold_days": (date - entry_date).days,
                    })
                    cash += proceeds
                    shares = 0
                    if verbose:
                        print(f"[止损] {date} @ {close:.2f} PnL {pnl:+.0f} ({pnl_pct*100:+.1f}%)")
                elif pnl_pct >= cfg.tp2 and shares > 0:
                    proceeds = shares * close - sell_cost(shares * close)
                    pnl = proceeds - entry_price * shares
                    trades.append({
                        "type": "sell", "reason": "止盈2", "date": date, "price": close,
                        "shares": shares, "pnl": pnl, "pnl_pct": pnl / (entry_price * shares),
                        "hold_days": (date - entry_date).days,
                    })
                    cash += proceeds
                    shares = 0
                    if verbose:
                        print(f"[止盈2] {date} @ {close:.2f} PnL {pnl:+.0f} (+{pnl_pct*100:.1f}%)")
                elif pnl_pct >= cfg.tp1 and shares > 0:
                    sell_shares = (shares // 2 // 100) * 100
                    if sell_shares >= 100:
                        proceeds = sell_shares * close - sell_cost(sell_shares * close)
                        pnl = proceeds - entry_price * sell_shares
                        trades.append({
                            "type": "sell", "reason": "止盈1", "date": date, "price": close,
                            "shares": sell_shares, "pnl": pnl, "pnl_pct": pnl / (entry_price * sell_shares),
                            "hold_days": (date - entry_date).days,
                        })
                        cash += proceeds
                        shares -= sell_shares
                        if verbose:
                            print(f"[止盈1] {date} @ {close:.2f} 卖{sell_shares} PnL {pnl:+.0f}")

        # 空仓状态下的买入信号
        if shares == 0 and has_sr:
            shrink = vol < df["vol_ma"].iloc[i] * cfg.shrink_coef
            expand = vol > df["vol_ma"].iloc[i] * cfg.expand_coef
            # 趋势过滤: 站上趋势均线才允许买入(排除下跌趋势中的假回调/假突破)
            trend_ma = row["trend_ma"]
            in_trend = not np.isnan(trend_ma) and close >= trend_ma
            if cfg.trend_filter and not in_trend:
                trend_ok = False
            else:
                trend_ok = True
            # 企稳确认: 当根K线收阳/收平(排除单边下跌接飞刀)
            stab = (row["close"] >= row["open"]) if cfg.stab_confirm else True

            # 缩量回踩支撑位 → 建半仓 (需趋势过滤 + 企稳确认)
            if low <= support * 1.02 and shrink and trend_ok and stab:
                if not is_limit_up(row["prev_close"], close):
                    buy_shares = int(cash * 0.5 / (close * 100)) * 100
                    if buy_shares >= 100:
                        cost = buy_cost(buy_shares * close)
                        cash -= buy_shares * close + cost
                        shares = buy_shares
                        entry_price = close
                        entry_date = date
                        if verbose:
                            print(f"[缩量企稳] {date} @ {close:.2f} 买{buy_shares}股")
            # 放量突破压力位 → 满仓 (需趋势过滤)
            elif close > resistance and expand and trend_ok:
                if not is_limit_up(row["prev_close"], close):
                    buy_shares = int(cash * 0.95 / (close * 100)) * 100
                    if buy_shares >= 100:
                        cost = buy_cost(buy_shares * close)
                        cash -= buy_shares * close + cost
                        shares = buy_shares
                        entry_price = close
                        entry_date = date
                        if verbose:
                            print(f"[放量突破] {date} @ {close:.2f} 买{buy_shares}股")

        total = cash + shares * close
        equity.append(total)
        returns.append(total / prev_equity - 1 if prev_equity > 0 else 0)
        prev_equity = total

    result = BacktestResult(
        equity=pd.Series(equity, index=df["date"], name="equity"),
        trades=trades,
        returns=pd.Series(returns, index=df["date"], name="returns"),
    )
    result.metrics = result.summary()
    return result
