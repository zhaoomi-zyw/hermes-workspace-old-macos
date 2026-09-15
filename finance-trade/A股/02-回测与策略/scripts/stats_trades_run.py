#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计 trade_journal.json 的真实交易胜率 (2026-09-03 修正版数据)"""
import json, sys
from collections import defaultdict
from datetime import datetime

path = "/Users/omi/workspace/quant-backtest/trade_journal.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)
trades = data.get("trades", [])
print(f"共 {len(trades)} 笔记录")

# 月度划分
def month(d):
    return d[:7]  # "2026-07"

# 已平仓=有exit_price和pnl
closed = [t for t in trades if t.get("pnl") is not None]
print(f"已平仓 {len(closed)} 笔")

# 整体统计
def stat(tlist, label):
    if not tlist:
        print(f"{label}: 无数据")
        return
    wins = [t for t in tlist if t["pnl"] > 0]
    losses = [t for t in tlist if t["pnl"] < 0]
    be = [t for t in tlist if t["pnl"] == 0]
    total = sum(t["pnl"] for t in tlist)
    n = len(tlist)
    wr = len(wins)/n*100
    avg_win = sum(t["pnl"] for t in wins)/len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses)/len(losses) if losses else 0
    ratio = abs(avg_win/avg_loss) if avg_loss else 0
    print(f"{label}: {n}笔 胜{len(wins)} 负{len(losses)} 平{len(be)} 胜率{wr:.0f}% "
          f"净{total:+.0f} 均盈{avg_win:+.0f} 均亏{avg_loss:+.0f} 盈亏比{ratio:.2f}")

print("\n===== 整体 =====")
stat(closed, "全部")

# 按月
print("\n===== 按月 =====")
bymonth = defaultdict(list)
for t in closed:
    bymonth[month(t["date_exit"])].append(t)
for m in sorted(bymonth):
    stat(bymonth[m], f"{m}")

# 按信号
print("\n===== 按信号 =====")
bysig = defaultdict(list)
for t in closed:
    sid = t.get("signal_id") or "UNKNOWN"
    bysig[sid].append(t)
for sid in sorted(bysig):
    stat(bysig[sid], sid)

# 持仓天数统计
print("\n===== 持仓天数 =====")
days = [t.get("holding_days",0) for t in closed if t.get("holding_days")]
if days:
    print(f"平均 {sum(days)/len(days):.1f}天, 最短{min(days)}, 最长{max(days)}")

# 分股票盈亏
print("\n===== 分股票净盈亏 =====")
bystk = defaultdict(float)
cnt = defaultdict(int)
for t in closed:
    s = t.get("stock","?")[:6]
    bystk[s]+=t["pnl"]; cnt[s]+=1
for s in sorted(bystk, key=lambda x:-bystk[x]):
    print(f"  {s}: {cnt[s]}笔 {bystk[s]:+.0f}元")
