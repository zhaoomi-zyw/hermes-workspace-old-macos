#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首批「主动管理 ETF」发行/上市监控（watchdog）

背景（2026-09-18 查证）：
  2026-06-17 证监会宣布支持主动ETF
  2026-07-16/17 首批18只上报（审批状态：接收材料）
  2026-09-08 仍在「最后一公里」（审批中）
  → 媒体报道预计 2026-10 月集中启动募集，上市约 10月底~11月
  → 截至 2026-09-18，全市场 700 只 ETF 中名称含「主动」的 = 0 只

监控方式（直连接口，不用搜索，避免内容风控）：
  拉取东财全量 ETF 列表（push2delay 域名可用，push2 被风控）
  → 筛选名称含「主动」的标的
  → 与上次快照比对，出现新增即推送
  → 同时报告「增强ETF」数量变化（辅助信号）

首次运行只建立基线并报告当前状态；之后只在有变化时推送。
"""
import urllib.request
import json
import os
import re
import sys
import time
from datetime import datetime

STATE_FILE = os.path.expanduser("~/.hermes/profiles/main/cron/state/active_etf_watch.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0"


def fetch_all_etfs(pages=8, pz=200):
    rows = []
    for pn in range(1, pages + 1):
        url = (f"https://push2delay.eastmoney.com/api/qt/clist/get?pn={pn}&pz={pz}"
               "&po=1&np=1&fltt=2&invt=2&fid=f3"
               "&fs=b:MK0021,b:MK0022,b:MK0023,b:MK0024&fields=f12,f13,f14,f2,f3,f6")
        for attempt in range(3):
            try:
                raw = urllib.request.urlopen(urllib.request.Request(url, headers={
                    "User-Agent": UA, "Referer": "https://quote.eastmoney.com/"}), timeout=30
                ).read().decode("utf-8", "ignore")
                d = json.loads(raw)
                got = (d.get("data") or {}).get("diff") or []
                rows += got
                break
            except Exception:
                if attempt == 2:
                    return rows
                time.sleep(2)
        time.sleep(0.4)
    return rows


def main():
    rows = fetch_all_etfs()
    if not rows:
        print("[主动ETF监控] 取数失败（接口不可用）", file=sys.stderr)
        sys.exit(2)

    active = [x for x in rows if "主动" in (x.get("f14") or "")]
    enhanced = [x for x in rows if "增强" in (x.get("f14") or "")]

    prev = {}
    try:
        prev = json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:
        prev = {}

    prev_active = set(prev.get("active_codes") or [])
    cur_active = {x["f12"] for x in active}
    new_codes = cur_active - prev_active

    state = {
        "active_codes": sorted(cur_active),
        "active_names": sorted(x["f14"] for x in active),
        "enhanced_count": len(enhanced),
        "etf_total": len(rows),
        "last_checked": datetime.now().isoformat(),
    }
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    first_run = not prev
    if first_run:
        print("📡 主动管理ETF 上市监控 · 基线建立")
        print(f"   全市场 ETF {len(rows)} 只")
        print(f"   名称含「主动」：{len(active)} 只" + ("（尚未上市 ✓ 与预期一致）" if not active else ""))
        print(f"   名称含「增强」：{len(enhanced)} 只（参考项）")
        if active:
            print("   ⚠️ 已出现主动ETF：")
            for x in active:
                print(f"      {x['f12']}  {x['f14']}")
        return

    if new_codes:
        print("🚨 主动管理ETF 出现新品种！")
        for x in active:
            if x["f12"] in new_codes:
                print(f"   ● {x['f12']}  {x['f14']}")
                print(f"     现价 {x.get('f2')}  涨跌 {x.get('f3')}%  成交额 {(x.get('f6') or 0)/1e8:.3f}亿")
        print("\n   → 券商 App 搜索该代码确认可交易性")
        print("   → 对比模板：Obsidian 04-Trading/主动管理ETF-18只对比模板.md")
    else:
        # 无新增主动ETF：仅当增强ETF数量明显变化时提示
        prev_enh = prev.get("enhanced_count", 0)
        if len(enhanced) - prev_enh >= 3:
            print(f"📈 增强ETF 新增 {len(enhanced)-prev_enh} 只（{prev_enh} → {len(enhanced)}）")
            print(f"   主动管理ETF 仍为 {len(active)} 只（未上市）")
        # 否则完全静默


if __name__ == "__main__":
    main()
