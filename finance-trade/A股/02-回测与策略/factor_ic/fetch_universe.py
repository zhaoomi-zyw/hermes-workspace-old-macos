#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""因子 IC 检验 · 扩样本（C 方案）

目的：把样本从 12 只高度同质的股票 → 沪深300（300只，跨行业），
      验证「营收增速有效」「动量负向」等结论是否只是行业行情假象。

数据源：
  成分股  → hithink-finance index constituents --thscode 000300.SH
  日K     → 腾讯 web.ifzq.gtimg.cn（800根/3年，稳定）
  财务    → hithink-finance financials indicators（单只调用，较慢 → 可选开关）

输出：results/factor_ic_20260918/universe/
  daily/<code>.csv   日K
  fin/<code>.csv     财务（--with-fin 时）
  universe.json      成分股名单

用法：
  python fetch_universe.py                 # 仅日K（快，约3分钟）
  python fetch_universe.py --with-fin 60   # 另取前60只的财务
"""
from __future__ import annotations

import os
import csv
import json
import subprocess
import sys
import time
import urllib.request

OUT = "/Users/omi/workspace/quant-backtest/results/factor_ic_20260918/universe"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "http://finance.qq.com"}


def cli_json(args, timeout=90, tries=3):
    for _ in range(tries):
        try:
            r = subprocess.run(["hithink-finance"] + args + ["--format", "json", "--source", "remote"],
                               capture_output=True, text=True, timeout=timeout)
            if r.returncode == 0 and r.stdout.strip():
                return json.loads(r.stdout)
        except Exception:
            pass
        time.sleep(2)
    return None


def get_constituents(idx="000300.SH"):
    d = cli_json(["index", "constituents", "--thscode", idx])
    if not d or not d.get("ok"):
        return {}
    return {x["ticker"]: x["name"] for x in (d["data"].get("item") or [])}


def qq_code(c):
    return ("sh" if c[0] == "6" else "sz") + c


def fetch_qq_daily(code, n=800):
    u = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={qq_code(code)},day,,,{n},qfq"
    for _ in range(2):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=25).read()
            node = json.loads(raw)["data"][qq_code(code)]
            k = node.get("qfqday") or node.get("day")
            return [{"date": x[0], "open": float(x[1]), "close": float(x[2]),
                     "high": float(x[3]), "low": float(x[4]), "volume": float(x[5])} for x in k]
        except Exception:
            time.sleep(1.5)
    return []


FIN_MAP = {
    "calculate_operating_income_yoy_growth_ratio": "rev_yoy",
    "calculate_parent_holder_net_profit_yoy_growth_ratio": "np_yoy",
    "index_weighted_avg_roe": "roe",
    "sale_gross_margin": "gross_margin",
    "sale_net_interest_ratio": "net_margin",
    "assets_debt_ratio": "debt_ratio",
    "total_assets_turnover_ratio": "asset_turnover",
    "operating_cash_flow_net_divide_income": "ocf_to_income",
}


def fetch_fin(code, years=(2024, 2025, 2026)):
    ths = code + (".SH" if code[0] == "6" else ".SZ")
    rows = []
    for y in years:
        for q in (1, 2, 3, 4):
            rep = f"{y}-{q}"
            d = cli_json(["financials", "indicators", "--thscode", ths, "--report", rep], timeout=45, tries=1)
            if d and d.get("ok"):
                rec = {"report": rep}
                for ab in (d["data"].get("abilities") or []):
                    for ind in (ab.get("indicators") or []):
                        key = FIN_MAP.get(ind.get("index_id"))
                        if key:
                            try:
                                rec[key] = float(ind["value"])
                            except (TypeError, ValueError):
                                pass
                if len(rec) > 1:
                    rows.append(rec)
            time.sleep(0.1)
    return rows


def main():
    with_fin = 0
    if "--with-fin" in sys.argv:
        i = sys.argv.index("--with-fin")
        with_fin = int(sys.argv[i + 1]) if i + 1 < len(sys.argv) else 60

    os.makedirs(os.path.join(OUT, "daily"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "fin"), exist_ok=True)

    cons = get_constituents()
    print(f"沪深300 成分股: {len(cons)} 只")
    if not cons:
        print("❌ 成分股获取失败")
        return
    json.dump(cons, open(os.path.join(OUT, "universe.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    ok = fail = cached = 0
    codes = sorted(cons.keys())
    for i, code in enumerate(codes, 1):
        dp = os.path.join(OUT, "daily", f"{code}.csv")
        if os.path.exists(dp) and sum(1 for _ in open(dp)) > 400:
            cached += 1
            continue
        dl = fetch_qq_daily(code)
        if dl:
            with open(dp, "w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=list(dl[0].keys()))
                w.writeheader()
                w.writerows(dl)
            ok += 1
        else:
            fail += 1
        if i % 30 == 0:
            print(f"  进度 {i}/{len(codes)}  成功{ok} 失败{fail} 缓存{cached}")
        time.sleep(0.25)

    print(f"\n日K 完成: 成功{ok} 失败{fail} 缓存{cached} / 共{len(codes)}")

    if with_fin:
        sub = codes[:with_fin]
        print(f"\n财务拉取（前 {with_fin} 只，每只 12 期）...")
        for i, code in enumerate(sub, 1):
            fp = os.path.join(OUT, "fin", f"{code}.csv")
            if os.path.exists(fp) and sum(1 for _ in open(fp)) > 3:
                continue
            fin = fetch_fin(code)
            if fin:
                cols = sorted({k for r in fin for k in r})
                with open(fp, "w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                    w.writeheader()
                    w.writerows(fin)
            if i % 10 == 0:
                print(f"  财务进度 {i}/{len(sub)}")
    print(f"\n✅ 落盘 → {OUT}")


if __name__ == "__main__":
    main()
