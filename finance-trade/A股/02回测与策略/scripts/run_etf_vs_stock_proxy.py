# -*- coding: utf-8 -*-
"""ETF 池 vs 个股池 —— 同日线代理口径对照 (2026-09-24)

方法:
  * 复用 results/confirmed_policy_3y_20260914 的引擎与 run_daily_proxy
  * 两组都走 run_proxy（D-1 信号 + D 日开盘执行），口径完全一致
  * 窗口 2023-09-14 ~ 2026-09-14，初始资金 13822.47（与主结果一致）
  * ETF 无 5 分钟数据 → 量比用「前一日全天量 / 此前5日全天均量 < 0.80」替代条件
    个股组也同样只用日线，保证可比性

声明: 日线代理不是原规则完整回测；窗口内 ETF 不可用 5 分钟分钟级撮合。
      结果仅作方向性对照，不得当作收益预测。
"""
from __future__ import annotations
import json, sys
from pathlib import Path

HERE = Path("/Users/omi/workspace/quant-backtest/results/confirmed_policy_3y_20260914")
sys.path.insert(0, str(HERE))
sys.path.insert(0, "/Users/omi/workspace/quant-backtest")

import confirmed_policy_engine as E
import run_daily_proxy as R

INIT = 13822.47

ETF_CODES = ["sh515880","sh512480","sz159995","sh515050","sz159819",
             "sh512010","sz159992","sh513120","sh512170"]
STK_CODES = [c for c, (n, m) in E.STOCKS.items()]   # 12 只（6位数字）

# ETF 名称注入（仅内存；run_daily_proxy 内部会查 E.STOCKS[c][0] 取名称）
ETF_NAMES = {
    "sh515880": "通信ETF国泰", "sh512480": "半导体ETF国联安", "sz159995": "芯片ETF华夏",
    "sh515050": "通信ETF华夏", "sz159819": "人工智能ETF", "sh512010": "医药ETF易方达",
    "sz159992": "创新药ETF银华", "sh513120": "港股创新药广发", "sh512170": "医疗ETF华宝",
}
for _c, _n in ETF_NAMES.items():
    E.STOCKS[_c] = (_n, _c[:2])


import run_confirmed_policy_3y as RC


def stats(res, data, codes):
    """用引擎现役 metrics（口径单一来源，不自行重写）。"""
    cal = data["_calendar"]
    m = RC.metrics(res, cal, E.BACKTEST_START, E.BACKTEST_END)
    eq = res.daily_equity
    final = eq[-1]["equity"] if eq else None
    return {
        "final": round(final, 2) if final else None,
        "ret_pct": m.get("total_return_pct"),
        "mdd_pct": m.get("max_drawdown_pct"),
        "trades": m.get("n_closed_trades"),
        "win_rate": m.get("win_rate_pct"),
        "profit_factor": m.get("profit_factor"),
        "fee_total": round(res.fee_total, 2),
        "slip_total": round(res.slip_total, 2),
        "extra": {k: v for k, v in list(m.items())[:0]},
    }

def per_symbol(res):
    out = {}
    for t in res.trades:
        if not t.exit_date:
            continue
        d = out.setdefault(t.stock, {"n": 0, "pnl": 0.0, "win": 0})
        d["n"] += 1; d["pnl"] += t.pnl_net
        if t.pnl_net > 0: d["win"] += 1
    return out

result = {}
for label, codes in [("ETF池(9只)", ETF_CODES), ("个股池(12只)", STK_CODES)]:
    print(f"\n{'='*90}\n▶ {label}  running ...\n{'='*90}", flush=True)
    data = E.load_all(codes)
    res = R.run_proxy(data, codes, init_cash=INIT, path="OLHC",
                      label=label, scenario="daily_proxy")
    s = stats(res, data, codes)
    ps = per_symbol(res)
    result[label] = {"summary": s, "per_symbol": ps,
                     "equity": [{"date": e["date"], "equity": e["equity"], "cash": e["cash"],
                                 "mv": e["market_value"]} for e in res.daily_equity],
                     "trades": [{"stock": tr.stock, "name": tr.name, "entry": tr.entry_date,
                                 "exit": tr.exit_date, "pnl": tr.pnl_net, "pct": tr.pnl_pct,
                                 "reason": tr.exit_reason, "days": tr.holding_days}
                                for tr in res.trades if tr.exit_date]}
    print(json.dumps(s, ensure_ascii=False, indent=2))
    print("\n  逐标的:")
    for c, v in sorted(ps.items(), key=lambda x: x[1]["pnl"]):
        print("    %-14s n=%-3d pnl=%+10.2f  胜率=%.0f%%" % (c, v["n"], v["pnl"], v["win"]/v["n"]*100))

outp = HERE / "etf_vs_stock_dailyproxy.json"
outp.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("\n\n" + "="*90)
print("★ 对比总表（同日线代理口径，窗口 2023-09-14 ~ 2026-09-14，初始 %.2f）" % INIT)
print("="*90)
print("%-16s %10s %10s %10s %7s %9s %12s" % ("组合", "期末权益", "累计收益", "最大回撤", "交易数", "胜率", "利润因子"))
for label in result:
    s = result[label]["summary"]
    print("%-16s %10.2f %9.2f%% %9.2f%% %7d %8.1f%% %12s" % (
        label, s["final"], s["ret_pct"], s["mdd_pct"], s["trades"],
        s["win_rate"] or 0, s["profit_factor"] or "-"))
print("\n结果已存: %s" % outp)
