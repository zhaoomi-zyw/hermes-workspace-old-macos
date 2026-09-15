#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
migrate_sell_policy.py — 历史最高价/保护状态迁移 (2026-09-14)
=============================================================
用真实分时记录(新浪 5分钟K)重建各持仓的「持仓后最高价 H」与保护状态,
初始化 sell-policy-state.json。

数据来源与缺口如实标注:
- 优先: 新浪 CN_MarketDataService 5分钟K (scale=5), 覆盖 2026-08-14~09-14。
- 粒度: 5分钟K的 high 为"该5分钟内最高", 非逐笔; 标为「已观测最高价」,
  存在采样遗漏风险(新高与越线若发生在两次采样之间可能未被完整捕捉)。
- 不用买入前的当日高点/此前交易高点填补。

生命周期定义:
- 赤峰黄金 sh600988: 本笔持仓始于 2026-09-02(首买100@44.96), 9/11 加仓100@44.41,
  合并成本 44.735(券商含费)。H = 9/02 09:30 起该股最高价。
- 星网锐捷 sz002396: 本笔持仓始于 2026-09-14 10:03 买回100@35.88。
  (T-027/T-029 是 9/10 的旧笔, 已于 9/11 平仓, 不属本生命周期, 不继承。)
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from strategies.sell_policy import (
    StateStore, init_position, update_quote, add_position, roll_trading_day,
    round_price, DEFAULT_PARAMS, STRATEGY_VERSION,
)


def fetch_sina_min(symbol: str, datalen: int = 1023):
    url = (f"https://quotes.sina.cn/cn/api/jsonp_v2.php/x/"
           f"CN_MarketDataService.getKLineData?symbol={symbol}&scale=5&ma=no&datalen={datalen}")
    req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
    txt = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
    m = re.search(r"x\((.*)\)", txt, re.S)
    if not m:
        raise RuntimeError("sina parse fail")
    return json.loads(m.group(1))


def observed_high_after(bars, after: str):
    post = [b for b in bars if b["day"] >= after]
    if not post:
        return None, None, None
    hi = max(float(b["high"]) for b in post)
    return hi, post[0]["day"], post[-1]["day"]


def main():
    report = {"strategy_version": STRATEGY_VERSION, "migrations": []}

    # ---- 赤峰黄金: 9/02 首买 -> 9/11 加仓 (按真实顺序回放, 遵守 R6: S 只升不降) ----
    bars = fetch_sina_min("sh600988")
    hi, d0, d1 = observed_high_after(bars, "2026-09-02 09:30:00")
    # R6: 先用首买成本建立生命周期, 再回放加仓, 硬止损只升不降
    st = init_position("sh600988", "赤峰黄金", 44.96, 100,
                       sellable_qty=100, today_new_qty=0, entry_date="2026-09-02")
    s_initial = st.hard_stop                      # 44.96×0.94 = 42.26
    add_position(st, 100, 44.41, entry_date="2026-09-11")  # 无费合并成本44.685
    # 9/11 加仓到 9/14 已过 T+1 → 全部可卖
    roll_trading_day(st)
    # 券商确认含费合并成本 = 44.735; 覆盖成本, 但 S 按 R6 只升不降保持 42.26
    st.cost = 44.735  # 保留3位精度(不取整到2位)
    st.hard_stop = round_price(max(s_initial, st.cost * (1 - DEFAULT_PARAMS.hard_stop_pct)))
    gap = None
    if hi is None:
        gap = "无 9/02 起分钟数据, H 无法重建, 保留保守值(成本), 保护状态按未开启处理"
        st.migrated = True
        st.migration_note = gap
    else:
        st.peak_h = round_price(hi)
        st.peak_h_time = d1 or ""
        st.migrated = True
        st.migration_note = (f"H 由新浪5分钟K重建: 区间 {d0}~{d1}, "
                             f"H={st.peak_h} (已观测最高价, 5分钟粒度, 非逐笔); "
                             f"S 按 R6 回放: 首买S={s_initial} -> 加仓后 max(旧S, 44.735×0.94=42.05)={st.hard_stop}")
        from strategies.sell_policy import _activate_and_update_lines
        _activate_and_update_lines(st, DEFAULT_PARAMS)
    StateStore().put(st)
    report["migrations"].append({
        "code": "sh600988", "name": "赤峰黄金", "lifecycle_from": "2026-09-02",
        "cost": st.cost, "qty": st.total_qty, "peak_h_rebuilt": st.peak_h,
        "peak_h_window": [d0, d1], "granularity": "5min(sina)",
        "protection_active": st.protection_active, "profit_line": st.profit_line,
        "hard_stop": st.hard_stop, "hard_stop_initial": s_initial,
        "hard_stop_if_reset_by_merged_cost": round_price(44.735 * 0.94),
        "existing_live_watchdog_stop": 42.05,
        "discrepancy_note": ("现有实盘watchdog用42.05(按合并成本44.735×0.94); "
                             "按R6只升不降应为42.26(源自首买44.96×0.94)。"
                             "差异0.21元, 需Omi确认采用哪个。"),
        "effective_exit": st.effective_exit_line(),
        "gap": gap, "note": st.migration_note,
    })

    # ---- 星网锐捷: 9/14 10:03 起 ----
    bars = fetch_sina_min("sz002396")
    hi, d0, d1 = observed_high_after(bars, "2026-09-14 10:03:00")
    st2 = init_position("sz002396", "星网锐捷", 35.880, 100,
                        sellable_qty=0, today_new_qty=100, entry_date="2026-09-14")
    gap2 = None
    if hi is None:
        gap2 = "无 9/14 起分钟数据, H 无法重建, 保留保守值(成本)"
        st2.migrated = True
        st2.migration_note = gap2
    else:
        st2.peak_h = round_price(hi)
        st2.peak_h_time = d1 or ""
        st2.migrated = True
        st2.migration_note = (f"H 由新浪5分钟K重建: 区间 {d0}~{d1}, "
                              f"H={st2.peak_h} (已观测最高价, 5分钟粒度, 非逐笔)")
        from strategies.sell_policy import _activate_and_update_lines
        _activate_and_update_lines(st2, DEFAULT_PARAMS)
    StateStore().put(st2)
    report["migrations"].append({
        "code": "sz002396", "name": "星网锐捷", "lifecycle_from": "2026-09-14",
        "cost": st2.cost, "qty": st2.total_qty, "peak_h_rebuilt": st2.peak_h,
        "peak_h_window": [d0, d1], "granularity": "5min(sina)",
        "protection_active": st2.protection_active, "profit_line": st2.profit_line,
        "hard_stop": st2.hard_stop, "effective_exit": st2.effective_exit_line(),
        "gap": gap2, "note": st2.migration_note,
    })

    out = "/Users/omi/workspace/quant-backtest/results/sell_policy_migration_2026-09-14.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\n迁移报告已写入: {out}")


if __name__ == "__main__":
    main()
