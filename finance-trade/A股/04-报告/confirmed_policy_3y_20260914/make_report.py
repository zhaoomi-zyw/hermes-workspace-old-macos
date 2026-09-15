# -*- coding: utf-8 -*-
"""make_report.py — 由 summary.json / proxy_sensitivity.json / verification.json 生成 report.md"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(p, default=None):
    f = HERE / p
    if not f.exists():
        return default
    return json.loads(f.read_text(encoding="utf-8"))


def fmt(v, nd=2, suf=""):
    if v is None:
        return "null"
    if isinstance(v, float):
        return f"{v:.{nd}f}{suf}"
    return f"{v}{suf}"


def main():
    s = load("summary.json")
    p = load("proxy_sensitivity.json", {})
    v = load("verification.json", {})
    if s is None:
        print("no summary.json yet"); return

    L = []
    A = L.append
    A("# 已确认买卖策略 · 全部自选股三年验证\n")
    A(f"研究目录: `results/confirmed_policy_3y_20260914/`  ")
    A(f"生成时间: {s['generated_at']}  ")
    A(f"状态: **{s['status']}**  ")
    A(f"卖出规则模块: {s['strategy_version_sell']}  ")
    A(f"买入规则: {s['buy_policy']}  ")
    A(f"窗口: {s['backtest_window']['start']} ~ {s['backtest_window']['end']} "
      f"({s['backtest_window']['trading_days']} 个交易日)\n")

    A("## 0. 结论速览\n")
    pm = s["scenarios"]["portfolio_main"]
    A(f"- 同一现金池真实组合 (13,822.47 元, 即刻执行): 期末 "
      f"{fmt(pm.get('end_equity'))} 元, 累计 **{fmt(pm.get('total_return_pct'))}%**, "
      f"年化 {fmt(pm.get('annualized_pct'))}%, 最大回撤 {fmt(pm.get('max_drawdown_pct'))}%, "
      f"已平仓 {pm.get('n_closed_trades')} 笔, 胜率 {fmt(pm.get('win_rate_pct'))}%\n")
    A(f"- **手续费/滑点是主因之一**: 主场景手续费 {fmt(pm.get('fee_total'))} 元 = 初始资金的 "
      f"{fmt(pm.get('fee_pct_of_init'))}%, 滑点成本 {fmt(pm.get('slippage_cost_total'))} 元。"
      f"100 股整手 + 每笔最低 5 元佣金在小账户上放大为决定性拖累。\n")
    A(f"- **同期买入持有全面大涨**: 12 只等权(100股整手可行)平均 "
      f"{fmt(s['benchmarks']['equal_weight_12_feasible_100k_avg_return_pct'])}%, "
      f"单股 +{fmt(min(b.get('net_return_pct',0) for b in s['benchmarks']['per_stock_buy_and_hold_13822'].values()))}% ~ "
      f"+{fmt(max(b.get('net_return_pct',0) for b in s['benchmarks']['per_stock_buy_and_hold_13822'].values()))}%。"
      f"该策略在**这一窗口内大幅跑输买入持有**——它靠 -6% 硬止损与 +8% 后保护线高频切仓, 把这批趋势股切碎。\n")
    A(f"- **对建模假设不稳健**: 执行延迟 0/5/15 分钟 → {fmt(s['scenarios']['portfolio_main'].get('total_return_pct'))}% / "
      f"{fmt(s['scenarios']['portfolio_delay5'].get('total_return_pct'))}% / "
      f"{fmt(s['scenarios']['portfolio_delay15'].get('total_return_pct'))}%; "
      f"滑点 0%/0.1%/0.2% → {fmt(s['scenarios']['portfolio_slip0'].get('total_return_pct'))}% / "
      f"{fmt(pm.get('total_return_pct'))}% / {fmt(s['scenarios']['portfolio_slip2'].get('total_return_pct'))}%; "
      f"盘中顺序 → {fmt(s['scenarios']['portfolio_intra_OLHC'].get('total_return_pct'))}%。"
      f"结论量级 (小账户 + 高费用) 稳定为负或微利, 但符号可被假设翻转。\n")
    A("- 12 只各自独立实验收益**不可相加**当组合收益。\n")
    A("- 本结果为**历史回放模拟**, 不能推出未来收益; 详细假设与缺口见第 5、6 节。\n")

    A("## 1. 数据审计\n")
    A(f"- 数据源: {s['data_source']['provider']}")
    A(f"- 日线: {s['data_source']['daily']}")
    A(f"- 分钟: {s['data_source']['minute']}")
    A(f"- 说明: {s['data_source']['note']}")
    A(f"- 分钟分辨率处理: {s['minute_resolution_note']}\n")
    A("### 覆盖明细\n")
    A("| 股票 | 名称 | 日线行数(窗口) | 窗口停牌日 | 5分钟行数 | 5分钟日内数(窗口) | 窗口缺失5分钟日 | 复权口径 |")
    A("|---|---|---|---|---|---|---|---|")
    for c in s["data_coverage"]:
        A(f"| {c['stock']} | {c['name']} | {c['daily_rows_in_window']} | "
          f"{c['daily_halted_days_in_window']} | {c['min5_rows']} | {c['min5_days_in_window']} | "
          f"{c['min5_missing_days_in_window']} | {c['price_basis']} |")
    A("")

    rec = HERE / "price_reconciliation.csv"
    if rec.exists():
        import csv as _csv
        rows = list(_csv.DictReader(rec.open(encoding="utf-8")))
        A("### 复权口径对账 (前复权 vs 不复权)\n")
        A("| 股票 | 名称 | 期初 qfq/raw 比值 | 期末比值 | 窗口内除权除息事件数 | 最近事件 |")
        A("|---|---|---|---|---|---|")
        for r in rows:
            A(f"| {r['code']} | {r['name']} | {r['ratio_first']} | {r['ratio_last']} | "
              f"{r['n_adjust_events']} | {r['events_sample']} |")
        A("")
        A("> 全部标的最新的 qfq/raw 比值 = 1.0, 说明前复权以最新日为基准; 期初比值 < 1 反映窗口内"
          "累计分红/送转的复权回撤 (最深为工业富联 0.869 ≈ 13%)。因此用前复权价模拟的"
          "**100 股整手、佣金最低 5 元、现金账本只能标为近似**。\n")

    gap = [c for c in s["data_coverage"] if c["min5_missing_days_in_window"] > 0]
    A("### 窗口内分钟数据缺口 (逐股)\n")
    if gap:
        A("| 股票 | 名称 | 缺失交易日数 | 缺失日期样例 | 日线停牌日 |")
        A("|---|---|---|---|---|")
        for c in gap:
            A(f"| {c['stock']} | {c['name']} | {c['min5_missing_days_in_window']} | "
              f"{c['min5_missing_days_sample']} | {c['daily_halted_days_in_window']} |")
        A("")
        A("> 缺口均为停牌日; 停牌期间无法评估盘中触发, 引擎按「无分钟数据则跳过该日盘中判定」处理, "
          "已在阻塞计数中单列 `no_min_data`。\n")
    else:
        A("无缺口 (12 只 × 窗口内全部交易日均有 5 分钟数据)。\n")

    A("## 2. 12 只各自独立实验 (各 13,822.47 元)\n")
    A("| 股票 | 名称 | 累计净收益% | 年化% | 最大回撤% | 已平仓笔数 | 胜率% | 平均每笔 | 利润因子 | 最大连亏 | 平均仓位% | 收益集中度% | 期末权益 | 买入持有% |")
    A("|---|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for c, m in s["independent_experiments"].items():
        A(f"| {c} | {m['name']} | {fmt(m.get('total_return_pct'))} | {fmt(m.get('annualized_pct'))} | "
          f"{fmt(m.get('max_drawdown_pct'))} | {m.get('n_closed_trades')} | "
          f"{fmt(m.get('win_rate_pct'))} | {fmt(m.get('avg_pnl_per_trade'))} | "
          f"{fmt(m.get('profit_factor'),3)} | {m.get('max_consecutive_losses')} | "
          f"{fmt(m.get('avg_exposure_pct'))} | {fmt(m.get('top_trade_share_of_gross_pnl_pct'))} | "
          f"{fmt(m.get('end_equity'))} | "
          f"{fmt(s['benchmarks']['per_stock_buy_and_hold_13822'][c].get('net_return_pct'))} |")
    A("")
    A("> 胜率为 null 表示该股无已平仓交易; 收益集中度 = 单笔最大盈利 / 已平仓总净利润 "
      "(可为负或 > 100%, 表示最大一笔盈利超过全部平仓净利润之和)。"
      "逐股完整阻塞计数见 `per_stock.csv` 的 `blocked_json`。\n")

    A("### 逐年收益 (%)\n")
    A("| 股票 | 2023 | 2024 | 2025 | 2026 |")
    A("|---|---|---|---|---|")
    for c, m in s["independent_experiments"].items():
        y = m.get("yearly_return_pct") or {}
        A(f"| {c} {m['name']} | {fmt(y.get('2023'))} | {fmt(y.get('2024'))} | "
          f"{fmt(y.get('2025'))} | {fmt(y.get('2026'))} |")
    A("")

    A("## 3. 组合与场景\n")
    A("| 场景 | 期末权益 | 累计% | 年化% | 最大回撤% | 平仓笔数 | 胜率% | 利润因子 | 手续费 | 平均仓位% |")
    A("|---|---|---|---|---|---|---|---|---|---|")
    for k, m in s["scenarios"].items():
        A(f"| {k} | {fmt(m.get('end_equity'))} | {fmt(m.get('total_return_pct'))} | "
          f"{fmt(m.get('annualized_pct'))} | {fmt(m.get('max_drawdown_pct'))} | "
          f"{m.get('n_closed_trades')} | {fmt(m.get('win_rate_pct'))} | "
          f"{fmt(m.get('profit_factor'),3)} | {fmt(m.get('fee_total'))} | "
          f"{fmt(m.get('avg_exposure_pct'))} |")
    A("")

    A("### 主场景阻塞原因计数 (全部标的 × 全窗口 × 5分钟网格)\n")
    A("| 原因 | 次数 | 说明 |")
    A("|---|---|---|")
    _ex = {"cond_ma60": "价格未站上前一日MA60 或 MA60 未上翘",
           "cond_atr_band": "回撤深度 (HH−现价)/ATR14 不在 [2.5,4.5]",
           "cond_vol_ratio": "同刻累计量比 ≥ 0.8",
           "cond_vol_missing": "同刻量比数据缺失 (不通过)",
           "cooldown_block": "清仓后冷却期未结束",
           "no_min_data": "当日无分钟数据 (停牌)",
           "size_cash": "现金不足 (含费用)",
           "size_single_risk": "超单笔 2% 损失预算",
           "size_port_risk": "超组合 4% 风险上限",
           "size_mv_cap": "超单股 35% 市值上限",
           "size_lot_100": "不足 100 股整手",
           "price_band_exceeded": "执行时价格越出限价 (不追价, 不成交)",
           "order_expired": "限价单 15 分钟到期/越过 14:45",
           "recommended": "生成推荐 (进入待执行)"}
    for k, n in (pm.get("blocked") or {}).items():
        A(f"| {k} | {n} | {_ex.get(k, '执行时重验条件失败' if k.startswith('recheck_fail') else '')} |")
    A("")

    A("### 基准\n")
    A(f"- 12 股等权(100股整手可行, 100,000 资金基准)平均收益: "
      f"{fmt(s['benchmarks']['equal_weight_12_feasible_100k_avg_return_pct'])}%")
    A(f"- 12 股等权(分数股理论)平均收益: "
      f"{fmt(s['benchmarks']['equal_weight_12_theoretical_fractional_avg_return_pct'])}%")
    A("")
    A("| 股票 | 买入持有净收益%(13,822) | 买入持有净收益%(100,000) | 区间涨跌幅% |")
    A("|---|---|---|---|")
    for c, b in s["benchmarks"]["per_stock_buy_and_hold_13822"].items():
        A(f"| {c} {b['name']} | {fmt(b.get('net_return_pct'))} | "
          f"{fmt(s['benchmarks']['per_stock_buy_and_hold_100k'][c].get('net_return_pct'))} | "
          f"{fmt(b.get('return_pct'))} |")
    A("")

    A("## 4. 日线代理敏感性研究 (⚠️ 非原规则完整回测)\n")
    A(f"> {p.get('disclaimer','')}\n")
    if p.get("paths"):
        A("| 路径 | 资金 | 累计% | 最大回撤% | 平仓笔数 | 胜率% |")
        A("|---|---|---|---|---|---|")
        for k, m in p["paths"].items():
            A(f"| {k} | {k.split('_')[-1]} | {fmt(m.get('total_return_pct'))} | "
              f"{fmt(m.get('max_drawdown_pct'))} | {m.get('n_closed_trades')} | "
              f"{fmt(m.get('win_rate_pct'))} |")
        A("")

    A("## 5. 假设与口径\n")
    for k, val in s["assumptions"].items():
        A(f"- `{k}`: {val}")
    A("- 主资金场景 13,822.47 元为**研究假设**(最新已知成本+现金), 不是核实的实时净资产; 不注入当前真实持仓。")
    A("- 组合风险 = Σ(现价至有效退出线正距离×数量 + 合理卖出费用) + 新交易风险 ≤ 净资产 4%; 浮盈不抵扣。")
    A("- 多股同时合格只推荐排序最高且预算允许者; 并列按代码升序(复现约定); 通知占用预算, 在途单期间不再推荐。\n")

    A("## 6. 缺口与限制\n")
    A("- 自选股清单为 **2026-09-14 快照** 回溯, 存在**幸存者/选股前视偏差**, **不是**历史动态自选股池。")
    A("- 仅前复权价格, 无复权因子/分红明细 → 100 股整手、费用、现金账本为**近似**。")
    A("- 5 分钟为可获得最细粒度 (baostock 无 1 分钟; 东财/新浪分钟历史仅 32~42 个交易日)。")
    A("- 无法重现人工确认流程; 回测以「下单后延迟 0/5/15 分钟执行、越界即不成交」近似, 与真实提醒系统存在差异。")
    A("- 交易时间窗口在分钟层可验证; 日线代理层**无法**验证时间窗口与 15 分钟限价条件。")
    A("- 最高价与最低价盘中先后顺序未知, 统一采用悲观顺序(先 high 更新保护线, 再 low 判触发)。")
    A("- 不假定涨跌停一定成交或一定不成交; 无法确定排队的场景保守跳过。\n")

    A("## 7. 验证\n")
    if v:
        A(f"最少验证项: **{v.get('n_pass')}/{v.get('n_checks')} 通过**\n")
        for c in v.get("checks", []):
            A(f"- [{'PASS' if c['ok'] else 'FAIL'}] {c['check']}" + (f" — {c['detail']}" if c['detail'] else ""))
    A("")

    A("## 8. 复现命令\n")
    A("```bash")
    A("cd /Users/omi/workspace/quant-backtest")
    A(".venv/bin/python results/confirmed_policy_3y_20260914/fetch_data_baostock.py   # 数据层(只读拉取)")
    A(".venv/bin/python results/confirmed_policy_3y_20260914/run_confirmed_policy_3y.py  # 主回测")
    A(".venv/bin/python results/confirmed_policy_3y_20260914/run_daily_proxy.py         # 日线代理")
    A(".venv/bin/python results/confirmed_policy_3y_20260914/verify_invariants.py       # 不变式校验")
    A("```")

    (HERE / "report.md").write_text("\n".join(L), encoding="utf-8")
    print("report.md written,", len(L), "lines")


if __name__ == "__main__":
    main()
