#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_cn_calendar.py — 生成中国A股交易日历缓存 (v2, 修正版)
=============================================================
用 quant venv 的 akshare (tool_trade_date_hist_sina) 拉**权威官方交易日**,
生成 ~/.hermes/state/cn-a-share-trading-calendar.json。

v2 修正 (2026-09-02 用户纠正):
- trade_dates **只含 AkShare 已确认的官方交易日** (至当年年末官方数据耗尽点)。
  绝不用普通工作日 projection 冒充交易日 —— 那样会让 is_trading_day 对未来日期错误返回 True。
- requested_range 元数据可声明到 2030 (表达"需求/目标覆盖")，但 trade_dates 与 confirmed_end
  只反映真实官方确认的交易日。
- 超出 confirmed_end 的日期 => calendar_status=UNKNOWN (fail-closed/fail-open 由业务脚本处理)。

原子写入, 无凭据。
"""
from __future__ import annotations

import datetime
import json
import os

CACHE_FILE = os.path.expanduser("~/.hermes/state/cn-a-share-trading-calendar.json")

# 我们想要/规划的覆盖目标 (需求侧; 但 trade_dates 只到官方确认处)
REQUESTED_END_YEAR = 2030


def main():
    import akshare as ak

    df = ak.tool_trade_date_hist_sina()
    official = [d.isoformat() for d in df["trade_date"].tolist()]
    official = sorted(set(official))

    # 只保留 2025 至官方数据末尾 (AkShare 通常提供至当年年末)
    # trade_dates = 纯官方确认交易日, 绝不投影
    trade_dates = official  # 全量官方 (1990 起), 但下方 confirmed range 标注实际可用范围
    confirmed_start = "2025-01-01"
    # confirmed_end = 官方数据最后一个日期 (2026-12-31 或当年年末)
    confirmed_end = official[-1]

    # 元数据: requested (需求目标) vs confirmed (官方确认)
    cache = {
        "source": "akshare:tool_trade_date_hist_sina (官方交易日, 无投影)",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "requested_range": {
            "start": f"2025-01-01",
            "end": f"{REQUESTED_END_YEAR}-12-31",
        },
        "confirmed_range": {
            "start": confirmed_start,
            "end": confirmed_end,
        },
        "confirmed_end_note": (
            f"仅缓存 AkShare 官方确认交易日至 {confirmed_end}; 超出此日期一律 "
            f"CALENDAR_UNKNOWN(fail-closed买入/fail-open止损), 绝不将普通工作日投影为交易日。"
            f"官方全年交易日通常每年初由交易所公布, 需届时用新官方数据刷新缓存。"
        ),
        "trade_dates": trade_dates,   # 纯官方, 无 projection
        "count": len(trade_dates),
    }

    os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
    tmp = CACHE_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=1)
    os.replace(tmp, CACHE_FILE)
    print(f"缓存已写入: {CACHE_FILE}")
    print(f"官方交易日总数(1990起): {len(trade_dates)}")
    print(f"confirmed_range: {confirmed_start} ~ {confirmed_end}")
    print(f"requested_range(需求目标): 2025-01-01 ~ {REQUESTED_END_YEAR}-12-31 (非实际交易日)")
    print(f"trade_dates 末日期: {trade_dates[-1]} (仅官方)")


if __name__ == "__main__":
    main()
