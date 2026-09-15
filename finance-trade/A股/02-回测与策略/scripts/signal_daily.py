"""
实时 DSA 信号脚本 · Phase 4 模拟盘
====================================
每天用最新行情计算 DSA 买卖信号，输出结构化建议。

用法:
    python signal_daily.py              # 全部标的
    python signal_daily.py 601138       # 单只

输出为纯文本(便于微信推送), 包含每只股票的:
- 当前价格/最新日期
- DSA 信号状态: 买入/持有/卖出/观望
- 关键支撑/压力位
- 操作建议
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd

from strategies.dsa_strategy import DSAConfig
# 2026-09-06: 日线数据源从 akshare(fetch_data) 切换到同花顺官方API(fetch_data_hithink)
# 消除东财IP风控断连+按年分片; 两模块 fetch_history(code,name) 签名一致, 返回同格式df
from fetch_data_hithink import fetch_history

# 共享权威风控 (2026-09-02): 现金8119/持仓赤峰100@44.96/防守池35万排除
# 用于给"买入"模拟信号附加 时间/仓位/T+1/RR 门控提示(绝不下单)
try:
    from pathlib import Path
    import importlib.util as _ilu
    _gp = "/Users/omi/.hermes/profiles/main/scripts/trading_execution_guard.py"
    _gspec = _ilu.spec_from_file_location("trading_execution_guard", _gp)
    guard = _ilu.module_from_spec(_gspec)
    _gspec.loader.exec_module(guard)
    GUARD_AVAIL = True
except Exception:
    guard = None
    GUARD_AVAIL = False

# 纯数字代码 → 腾讯代码前缀 (sh=6xx, sz=else)
def _tencent_code(code: str) -> str:
    return ("sh" if code.startswith("6") else "sz") + code

# 交易日历 (2026-09-02): daily_plan 只在交易日盘后生成次日候选
try:
    _cp = "/Users/omi/.hermes/profiles/main/scripts/cn_trading_calendar.py"
    _cspec = _ilu.spec_from_file_location("cn_trading_calendar", _cp)
    cal = _ilu.module_from_spec(_cspec)
    _cspec.loader.exec_module(cal)
    CAL_AVAIL = True
except Exception:
    cal = None
    CAL_AVAIL = False


# 自选股 (2026-09-06: 去紫光000938[已清仓趋势弱], 加南山铝业600219/云南铜业000878[有色避险]/中航沈飞600760[军工])
STOCKS = {
    "601138": "工业富联",
    "002156": "通富微电",
    "600487": "亨通光电",
    "603380": "易德龙",
    "600988": "赤峰黄金",
    "600460": "士兰微",
    "600522": "中天科技",
    "002396": "星网锐捷",
    "600219": "南山铝业",
    "000878": "云南铜业",
    "000938": "紫光股份",
    "600760": "中航沈飞",
}

# 每只股票的优化参数(2026-09-06 全面改为积极版趋势策略)
# 紫金(已清仓): target残留
# 工业富联/中天/亨通/赤峰/通富: 积极版 trend模式(移动止损+破MA60让利润奔跑)
# 紫光/士兰微/星网/易德龙: 趋势弱, 仍用积极版但标注风险
PER_STOCK_CFG = {
    "601899": dict(exit_mode="target", tp1=0.10, tp2=0.20, stop_loss=0.06),      # 紫金(已清仓, 保留记录)
    # 积极版默认(所有趋势股): trend模式 + 止损7% + 盈利保护8% + 移动止损10%
    # dsa_strategy.DSAConfig 默认已是积极版参数, 无需逐只覆盖; 这里只对特例覆盖
    "601138": dict(exit_mode="trend", stop_loss=0.06, trend_exit_ma=60,
                   profit_lock=0.08, trailing_stop=0.10),                        # 工业富联积极版
    "600988": dict(exit_mode="trend", stop_loss=0.06, trend_exit_ma=60,
                   profit_lock=0.08, trailing_stop=0.10),                        # 赤峰黄金积极版(当前持仓)
    "600487": dict(exit_mode="trend", stop_loss=0.06, trend_exit_ma=60,
                   profit_lock=0.08, trailing_stop=0.10),                        # 亨通光电积极版
    "600522": dict(exit_mode="trend", stop_loss=0.06, trend_exit_ma=60,
                   profit_lock=0.08, trailing_stop=0.10),                        # 中天科技积极版
}

# 当前实仓 (每次操作后更新): 数据源改为统一卖出策略模块 sell_policy (唯一权威)
# 2026-09-14: 不再硬编码; 从 ~/.hermes/state/sell-policy-state.json 读取
# 兜底(仅当状态文件缺失时): 券商实盘成本(含费用) 2026-09-14
_FALLBACK_HOLDINGS = {"600988": (200, 44.735), "002396": (100, 35.880)}
_FALLBACK_CASH = 1287.47  # 券商实盘确认 2026-09-14 (可用=可取)

# 统一卖出策略模块 (唯一权威) — 加载
try:
    import importlib.util as _spu
    _SP_PATH = "/Users/omi/workspace/quant-backtest/strategies/sell_policy.py"
    _spspec = _spu.spec_from_file_location("sell_policy", _SP_PATH)
    sell_policy = _spu.module_from_spec(_spspec)
    import sys as _sys2
    _sys2.modules["sell_policy"] = sell_policy
    _spspec.loader.exec_module(sell_policy)
    SELL_POLICY_AVAIL = True
except Exception:
    sell_policy = None
    SELL_POLICY_AVAIL = False


def load_holdings():
    """R 统一: 从 sell_policy 状态读取持仓(唯一权威), 缺失则用兜底。返回 {数值code:(shares,cost)}, cash。"""
    if SELL_POLICY_AVAIL:
        try:
            positions = sell_policy.StateStore().all()
            if positions:
                h = {}
                for c, p in positions.items():
                    if p.total_qty > 0:
                        num = c[2:] if c[:2] in ("sh", "sz") else c  # sh600988 -> 600988
                        h[num] = (p.total_qty, p.cost)
                if h:
                    return h, _FALLBACK_CASH
        except Exception:
            pass
    return dict(_FALLBACK_HOLDINGS), _FALLBACK_CASH


HOLDINGS, CASH = load_holdings()

# 盘中条件单(同花顺实际挂单, 2026-08-23): {代码: (止损价, 止盈价)}
# 工业富联: 止损61.80(8/19低点61.83下方) / 止盈63.65(近高69.18×0.92, 锁+1.8%)
# 紫金矿业: 止损32.0(未挂止盈, 趋势持有)
CONDITION_ORDERS = {
    "601138": (61.80, 63.65),   # 工业富联止损/止盈
    "601899": (32.0, None),     # 紫金止损
}


def compute_signal(df: pd.DataFrame, cfg: DSAConfig) -> dict:
    """基于最新数据计算 DSA 信号"""
    df = df.copy().sort_values("date").reset_index(drop=True)
    lookback = cfg.lookback

    # 支撑压力位(用昨日, 避免未来函数)
    support = df["low"].rolling(lookback, min_periods=lookback).min().shift(1)
    resistance = df["high"].rolling(lookback, min_periods=lookback).max().shift(1)
    vol_ma = df["volume"].rolling(cfg.vol_window, min_periods=1).mean()
    trend_ma = df["close"].rolling(cfg.trend_exit_ma, min_periods=cfg.trend_exit_ma).mean()

    last = df.iloc[-1]
    prev = df.iloc[-2]
    close = last["close"]
    low = last["low"]
    vol = last["volume"]
    cur_support = support.iloc[-1]
    cur_resistance = resistance.iloc[-1]
    cur_vol_ma = vol_ma.iloc[-1]
    cur_trend = trend_ma.iloc[-1]

    shrink = vol < cur_vol_ma * cfg.shrink_coef
    expand = vol > cur_vol_ma * cfg.expand_coef
    near_support = low <= cur_support * 1.02 if not np.isnan(cur_support) else False
    broke_resistance = close > cur_resistance if not np.isnan(cur_resistance) else False
    # 趋势过滤(2026-08-30): 站上趋势均线才允许买入, 排除下跌趋势接飞刀
    in_trend = not np.isnan(cur_trend) and close >= cur_trend
    trend_ok = in_trend
    # 企稳确认(2026-08-30): 当根K线收阳/收平, 排除单边下跌
    stab = last["close"] >= last["open"]
    # 方案A: 放宽的"关注"信号——接近支撑/压力即可提示(±3%), 不要求严格触发
    close_to_support = cur_support is not None and np.isnan(cur_support)==False and close <= cur_support * 1.03
    close_to_resistance = cur_resistance is not None and np.isnan(cur_resistance)==False and close >= cur_resistance * 0.97

    # 判断信号
    if not np.isnan(cur_support) and not np.isnan(cur_resistance):
        if near_support and shrink and trend_ok and stab:
            signal, action = "买入", "缩量回踩支撑位企稳(站上趋势+收阳), 可建半仓"
        elif broke_resistance and expand and trend_ok:
            signal, action = "买入", "放量突破压力位(站上趋势), 可建满仓"
        elif near_support and shrink and not trend_ok:
            signal, action = "观望", "缩量回踩但处于下跌趋势(未站上趋势线), 不接飞刀, 等企稳"
        elif near_support and shrink and trend_ok and not stab:
            signal, action = "观望", "缩量回踩但当日收阴(未确认企稳), 等收阳再介入"
        elif close < cur_support:
            signal, action = "卖出", "跌破支撑位, 考虑止损"
        elif not np.isnan(cur_trend) and close < cur_trend:
            signal, action = "卖出", "跌破趋势线(MA%d), 考虑减仓" % cfg.trend_exit_ma
        elif close > cur_resistance:
            signal, action = "持有", "站上压力位, 趋势向好"
        elif close_to_support:
            signal, action = "低吸", "接近支撑位%.2f, 可回踩低吸" % cur_support
        elif close_to_resistance:
            signal, action = "关注", "接近压力位%.2f, 关注突破" % cur_resistance
        else:
            signal, action = "观望", "处于支撑压力之间, 等待信号"
    else:
        signal, action = "观望", "数据不足(上市时间短)"

    # 日期: 兼容 Timestamp 和 date 类型
    d = last["date"]
    date_str = str(d.date() if hasattr(d, "date") else d)

    return {
        "date": date_str,
        "close": close,
        "support": None if np.isnan(cur_support) else cur_support,
        "resistance": None if np.isnan(cur_resistance) else cur_resistance,
        "trend_ma": None if np.isnan(cur_trend) else cur_trend,
        "vol_ratio": round(vol / cur_vol_ma, 2) if cur_vol_ma > 0 else None,
        "signal": signal,
        "action": action,
    }


def get_cfg(code: str) -> DSAConfig:
    """获取某只股票的优化参数配置"""
    return DSAConfig(**PER_STOCK_CFG.get(code, {}))


def _aggressive_exit_advice(df, cost: float, code: str) -> str:
    """持仓离场建议 (2026-09-14 改为调用统一模块 sell_policy, 不再复制参数)。

    规则由 sell_policy 唯一实现: 硬止损C×0.94 / H≥C×1.08开保护 / P=max(旧P,C×1.03,H×0.93);
    MA60 仅趋势提示。此处仅把最新价喂给模块状态得到"离场/持有"文本。
    """
    try:
        c = df["close"].astype(float)
        price = float(c.iloc[-1])
        ma60 = c.rolling(60).mean()
        m60 = float(ma60.iloc[-1]) if len(c) >= 60 else None
        if not SELL_POLICY_AVAIL:
            return None
        store = sell_policy.StateStore()
        tcode = _tencent_code(code)
        st = store.get(tcode)
        if st is None:
            # 状态缺失(如新买入未登记): 用成本临时构造, 不写入
            st = sell_policy.init_position(tcode, STOCKS.get(code, code), cost, 100, entry_date="unknown")
        # 用最新收盘(作为有效行情近似)更新并判定
        last_date = str(df["date"].iloc[-1]) if "date" in df else ""
        sell_policy.update_quote(st, price, quote_time=last_date)
        line = st.effective_exit_line()
        pnl_pct = price / st.cost - 1
        parts = []
        if st.protection_active:
            parts.append(f"🟢 盈利保护已开启: 保护线P={st.profit_line:.2f}(H={st.peak_h:.2f}), "
                         f"硬止损S={st.hard_stop:.2f}, 有效退出线={line:.2f}")
        else:
            parts.append(f"浮盈{pnl_pct*100:+.1f}%未达保护开启线(+8%), 仅硬止损S={st.hard_stop:.2f}生效; "
                         f"H={st.peak_h:.2f}")
        if price <= line:
            parts.append(f"🔴 现价{price:.2f}已≤有效退出线{line:.2f}, 触发退出")
        else:
            parts.append(f"现价{price:.2f} > 退出线{line:.2f}, 持有")
        if m60 is not None:
            parts.append(f"(MA60 {m60:.2f} 仅趋势提示)")
        if st.pending_exit:
            pe = st.pending_exit
            parts.append(f"⚠️ 存在待退出事件 {pe['event_id']}: 可卖{pe['qty_sellable']}股/待退出{pe['qty_pending']}股")
        return " / ".join(parts)
    except Exception:
        return None


def generate_report(codes: Optional[list] = None) -> str:
    """生成全部标的的模拟盘报告(纯文本), 含当前持仓分析"""
    targets = {c: STOCKS[c] for c in (codes or STOCKS.keys()) if c in STOCKS}
    lines = ["📈 A股DSA模拟盘 · 每日信号(含持仓)", "=" * 30]

    # 交易日历门控 (2026-09-02): daily_plan 只在交易日盘后生成次日候选
    _is_trading_today = True
    _next_td_label = "次日"
    if CAL_AVAIL:
        _st = cal.calendar_status()
        _is_trading_today = (_st["status"] == cal.STATUS_TRADING)
        _nxt = cal.next_trading_day()
        if _nxt is not None:
            _next_td_label = f"次日({_nxt.isoformat()})"
        else:
            # 日历覆盖不足(接近confirmed_end/超范围): 不臆造次日, 标注需刷新
            _next_td_label = "次日(日历覆盖不足,无法确认,需刷新官方交易日)"
    if not _is_trading_today:
        # 非交易日盘后(周末/节假日)不生成候选; 不硬卡, 仅注明(fail-closed于买入判定由guard daily_plan处理)
        lines.append(f"⚠️ 今日({_is_trading_today and '交易日' or '非交易日'})非交易日, 生成的是下一交易日({_next_td_label})候选参考")
    else:
        lines.append(f"✅ 交易日确认, 以下为{_next_td_label}候选(非实盘信号)")

    # 数据缓存, 避免持仓和信号区块重复拉取
    cache: dict = {}
    for c in targets.keys():
        try:
            cache[c] = fetch_history(c, STOCKS[c])
        except Exception as e:
            cache[c] = e  # 存异常, 后续统一处理

    # 持仓分析
    lines.append("\n【当前持仓】")
    total_val = CASH
    if HOLDINGS:
        for code, (shares, cost) in HOLDINGS.items():
            name = STOCKS.get(code, code)
            try:
                df = cache.get(code)
                if isinstance(df, Exception):
                    raise df
                s = compute_signal(df, get_cfg(code))
                price = s["close"]
                mv = price * shares
                pnl = (price - cost) * shares
                pnl_pct = (price / cost - 1) * 100
                total_val += mv
                lines.append(f"  {name} {shares}股 @成本{cost:.2f}")
                lines.append(f"    现价{price:.2f} 市值{mv:.0f} 浮盈{pnl:+.0f}({pnl_pct:+.1f}%)")
                # 积极版持仓离场建议 (2026-09-06): 浮盈≥+8%才破MA60/移动止损离场
                exit_advice = _aggressive_exit_advice(df, cost, code)
                if exit_advice:
                    lines.append(f"    ▶ {exit_advice}")
                else:
                    lines.append(f"    信号:{s['signal']} → {s['action']}")
                co = CONDITION_ORDERS.get(code)
                if co:
                    sl, tp = co
                    co_parts = []
                    if sl: co_parts.append(f"止损{sl:.2f}")
                    if tp: co_parts.append(f"止盈{tp:.2f}")
                    if co_parts: lines.append(f"    条件单: {' / '.join(co_parts)}")
            except Exception as e:
                lines.append(f"  {name} 数据失败: {e}")
    else:
        lines.append("  无持仓(全部空仓)")
    lines.append(f"  可用现金: {CASH:.0f}元  总资产: ~{total_val:.0f}元")

    # 各标的信号
    lines.append("\n【自选股信号】")
    for code, name in targets.items():
        try:
            df = cache.get(code)
            if isinstance(df, Exception):
                raise df
        except Exception as e:
            lines.append(f"\n[{code}] {name} 数据获取失败: {e}")
            continue

        s = compute_signal(df, get_cfg(code))
        hold_mark = "🟢持仓" if code in HOLDINGS else "   "
        lines.append(f"\n▎{name} ({code}){hold_mark}")
        lines.append(f"  日期: {s['date']}  现价: {s['close']:.2f}")
        lines.append(f"  支撑: {s['support']:.2f}  压力: {s['resistance']:.2f}")
        if s["trend_ma"]:
            lines.append(f"  趋势MA{get_cfg(code).trend_exit_ma}: {s['trend_ma']:.2f}  量比: {s['vol_ratio']}")
        lines.append(f"  ▶ 信号: {s['signal']}")
        lines.append(f"    建议: {s['action']}")
        # 模拟买入门控 (2026-09-02): 买入信号附加 时间/仓位/T+1/RR 等价检查
        if s["signal"] == "买入" and GUARD_AVAIL:
            try:
                px = s["close"]
                sup = s.get("support") or px * 0.96
                res = s.get("resistance") or px * 1.06
                stop = sup * 0.98
                target = res
                # 收盘后模拟盘(如19:05): daily_plan 只生成次日候选,
                # 不应用当前钟点门禁, 保留仓位/RR/T+1/-5%压力检查。
                # (2026-09-02 语义复核修正: 不再伪造时间点绕过门禁)
                import datetime as _dt
                _now = _dt.datetime.now()
                g = guard.evaluate_buy(
                    px, stop, target,
                    context="daily_plan", now_dt=_now, hs300_pct=None,
                )
                _gate_txt = "✅次日候选(经盘中确认后可执行)" if g["allowed"] else "🚫阻止:" + g["reasons"][-1]
                lines.append(f"    [风控] {_gate_txt}")
                if g["rr"]:
                    lines.append(f"    [风控] RR={g['rr']:.2f} 一手≈{g['position_after']['value']:.0f}元 "
                                 f"(占可投{g['single_position_after']['ratio']*100:.1f}%) 隔夜-5%≈{g['overnight_stress_loss']:.0f}元")
                lines.append(f"    [风控] {g['t_plus_one']['note']} | {('次日仅09:40-14:20经盘中确认后可执行')} (模拟候选, 绝不下单)")
            except Exception:
                pass

    lines.append("\n" + "=" * 30)
    lines.append("⚠️ 模拟信号仅供研究, 不构成投资建议")
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]
    print(generate_report(args if args else None))
