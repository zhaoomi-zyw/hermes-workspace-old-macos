#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""因子 IC 检验 · 财务数据【批量版】（比逐期查询快 6 倍）

对比：
  旧：financials indicators --report YYYY-N   → 每只 12 次调用（~25秒/只）
  新：financials income --period quarterly --limit 12  → 每只 1 次（+ cash-flow 1 次）

自行计算指标（同花顺 indicators 已算好的版本见企业版）：
  毛利率   = (operating_income - operating_costs) / operating_income
  净利率   = net_profit / operating_income
  ROE代理  = parent_holder_net_profit / 净资产（需 balance-sheet，此处略 → 用净利率代）
  应计     = act_cash_flow_net / net_profit         ⭐ 盈利质量/应计因子
  营收增速 = 同比（相同 fiscal_period 的上一年）
  净利增速 = 同比（同上）

输出：results/factor_ic_20260918/universe/fin/<code>.csv
列：report, gross_margin, net_margin, rev_yoy, np_yoy, ocf_to_income
⚠️ 已存在的旧文件会被覆盖为统一格式。
"""
from __future__ import annotations

import os
import csv
import json
import subprocess
import sys
import time

OUT = "/Users/omi/workspace/quant-backtest/results/factor_ic_20260918/universe"


def cli_json(args, timeout=60, tries=2):
    for _ in range(tries):
        try:
            r = subprocess.run(["hithink-finance"] + args + ["--format", "json", "--source", "remote"],
                               capture_output=True, text=True, timeout=timeout)
            if r.returncode == 0 and r.stdout.strip():
                return json.loads(r.stdout)
        except Exception:
            pass
        time.sleep(1)
    return None


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fetch_one(code):
    ths = code + (".SH" if code[0] == "6" else ".SZ")
    inc = cli_json(["financials", "income", "--thscode", ths,
                    "--period", "quarterly", "--limit", "14"])
    cf = cli_json(["financials", "cash-flow", "--thscode", ths,
                   "--period", "quarterly", "--limit", "14"])
    if not inc or not inc.get("ok"):
        return []
    rows_inc = inc["data"].get("item") or []
    rows_cf = cf["data"].get("item") or [] if cf and cf.get("ok") else []
    cfmap = {}
    for r in rows_cf:
        key = (r.get("fiscal_year"), r.get("fiscal_period"))
        cfmap[key] = num(r.get("act_cash_flow_net"))

    by_key = {}
    for r in rows_inc:
        key = (r.get("fiscal_year"), r.get("fiscal_period"))
        by_key[key] = r

    out = []
    for (y, q), r in sorted(by_key.items(), key=lambda t: (t[0][0], t[0][1])):
        oi = num(r.get("operating_income"))
        oc = num(r.get("operating_costs"))
        npf = num(r.get("net_profit"))
        pnp = num(r.get("parent_holder_net_profit"))
        gm = (oi - oc) / oi if (oi and oc) else None
        nm = npf / oi if (oi and npf) else None
        ocf = cfmap.get((y, q))
        acc = (ocf / npf) if (ocf is not None and npf) else None
        # 同比
        prev = by_key.get((y - 1, q))
        rev_yoy = npy = None
        if prev:
            poi = num(prev.get("operating_income"))
            ppnp = num(prev.get("parent_holder_net_profit"))
            if poi and oi:
                rev_yoy = (oi / poi - 1) * 100
            if ppnp and pnp:
                npy = (pnp / ppnp - 1) * 100
        out.append({
            "report": f"{y}-{str(q).replace('Q','')}",
            "gross_margin": round(gm * 100, 4) if gm is not None else None,
            "net_margin": round(nm * 100, 4) if nm is not None else None,
            "rev_yoy": round(rev_yoy, 4) if rev_yoy is not None else None,
            "np_yoy": round(npy, 4) if npy is not None else None,
            "ocf_to_income": round(acc, 4) if acc is not None else None,
            "roe": None,   # 需资产负债表，暂缺（保持列一致）
            "debt_ratio": None,
        })
    return out


def main():
    os.makedirs(os.path.join(OUT, "fin"), exist_ok=True)
    cons = json.load(open(os.path.join(OUT, "universe.json"), encoding="utf-8"))
    codes = sorted(cons.keys())
    if "--limit" in sys.argv:
        codes = codes[:int(sys.argv[sys.argv.index("--limit") + 1])]

    ok = fail = 0
    for i, code in enumerate(codes, 1):
        fp = os.path.join(OUT, "fin", f"{code}.csv")
        rows = fetch_one(code)
        if rows:
            cols = ["report", "gross_margin", "net_margin", "rev_yoy", "np_yoy",
                    "ocf_to_income", "roe", "debt_ratio"]
            with open(fp, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                w.writeheader()
                w.writerows(rows)
            ok += 1
        else:
            fail += 1
        if i % 20 == 0:
            print(f"  财务 {i}/{len(codes)}  成功{ok} 失败{fail}")
        time.sleep(0.15)
    print(f"\n✅ 财务完成: 成功{ok} 失败{fail} / 共{len(codes)}")


if __name__ == "__main__":
    main()
