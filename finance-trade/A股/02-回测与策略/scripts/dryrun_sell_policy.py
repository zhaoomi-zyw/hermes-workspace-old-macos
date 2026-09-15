#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dry-run: 捕获 sell_policy 退出提醒的待发送内容(不发送、不改真实状态)。"""
import sys, importlib.util, copy
spec = importlib.util.spec_from_file_location("sell_policy", "/Users/omi/workspace/quant-backtest/strategies/sell_policy.py")
sp = importlib.util.module_from_spec(spec); sys.modules["sell_policy"] = sp; spec.loader.exec_module(sp)

print("策略版本:", sp.STRATEGY_VERSION)
print("=" * 60)

# 场景A: 硬止损触发 (星网 C=35.88, S=33.73, 现价模拟33.50)
st = sp.StateStore().get("sz002396")
st = copy.deepcopy(st)
sp.update_quote(st, 33.50, quote_time="20260914T103000")
ev = sp.evaluate_exit(st, 33.50, quote_time="2026-09-14 10:30:00")
if ev and sp.fire_exit(st, ev):
    print("【dry-run A: 硬止损触发】")
    print(sp.build_exit_alert(st, ev))
print("=" * 60)

# 场景B: 盈利保护触发 (赤峰, 模拟 H 到 48.31 开启保护后回落)
st2 = sp.StateStore().get("sh600988")
st2 = copy.deepcopy(st2)
sp.update_quote(st2, 48.31, quote_time="t_high")   # H 达到 44.735*1.08=48.31 → 开保护
print("保护开启后:", "protection_active=", st2.protection_active, "P=", st2.profit_line)
trig = st2.profit_line
ev2 = sp.evaluate_exit(st2, trig, quote_time="2026-09-15 14:00:00")
if ev2 and sp.fire_exit(st2, ev2):
    print("\n【dry-run B: 盈利保护触发】")
    print(sp.build_exit_alert(st2, ev2))
print("=" * 60)
print("(dry-run 结束; 未发送任何消息, 未修改真实状态文件)")
