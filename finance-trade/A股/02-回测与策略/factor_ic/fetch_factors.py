#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""因子 IC 检验 · 第1步：数据拉取（组合源）

数据源选择依据（2026-09-19 实测）：
  ✅ 日K        → 腾讯 web.ifzq.gtimg.cn（800根/3年+，稳定，无限流）
     ⚠️ 东财 push2his 已对本机限流（RemoteDisconnected）
     ⚠️ 同花顺 market history 依赖本地 DuckDB（空库 → Catalog Error），需先 data init
  ✅ 财务指标   → 同花顺 financials indicators（remote，实测 ok:true，含应计/盈利质量）
  ✅ 实时快照   → 腾讯 qt.gtimg.cn（含换手率 f[38]、流通市值 f[44]）

输出：results/factor_ic_20260918/
  daily/<code>.csv   日期/OHLC/成交量/成交额(推算)
  fin/<code>.csv     季度财务
  snapshot.json      实时快照（换手率/市值，用于交叉校验）
⚠️ 只读不写任何实盘链路文件。
"""
from __future__ import annotations

import os
import csv
import json
import subprocess
import time
import urllib.request

OUT = "/Users/omi/workspace/quant-backtest/results/factor_ic_20260918"
UA = {"User-Agent": "Mozilla/5.0", "Referer": "http://finance.qq.com"}

STOCKS = {
    "601138": "工业富联", "002156": "通富微电", "600460": "士兰微", "603380": "易德龙",
    "002396": "星网锐捷", "600487": "亨通光电", "600522": "中天科技", "600988": "赤峰黄金",
    "600219": "南山铝业", "000878": "云南铜业", "600760": "中航沈飞", "000938": "紫光股份",
}


def qq_code(c):
    return ("sh" if c[0] == "6" else "sz") + c


def ths_code(c):
    return c + (".SH" if c[0] == "6" else ".SZ")


def fetch_qq_daily(code, n=800):
    """腾讯日K（前复权）→ 日期,开,收,高,低,成交量(手)"""
    u = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={qq_code(code)},day,,,{n},qfq"
    for _ in range(3):
        try:
            raw = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read()
            d = json.loads(raw)
            node = d["data"][qq_code(code)]
            k = node.get("qfqday") or node.get("day")
            return [{"date": x[0], "open": float(x[1]), "close": float(x[2]),
                     "high": float(x[3]), "low": float(x[4]), "volume": float(x[5])} for x in k]
        except Exception:
            time.sleep(2)
    return []


def fetch_qq_snapshot(codes):
    """实时快照：换手率/流通市值/成交额"""
    out = {}
    for i in range(0, len(codes), 12):
        batch = codes[i:i + 12]
        for _ in range(3):
            try:
                u = "http://qt.gtimg.cn/q=" + ",".join(qq_code(c) for c in batch)
                raw = urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=20).read().decode("gbk", "ignore")
                for line in raw.strip().split(";"):
                    if "=" not in line:
                        continue
                    f = line.split("=", 1)[1].strip().strip('"').split("~")
                    if len(f) < 46:
                        continue
                    c = f[2]
                    out[c] = {"name": f[1], "price": float(f[3]), "turnover_pct": float(f[38]),
                              "amount_wan": float(f[37]), "float_mv_yi": float(f[44]),
                              "total_mv_yi": float(f[45])}
                break
            except Exception:
                time.sleep(2)
    return out


FIN_MAP = {
    "calculate_operating_income_yoy_growth_ratio": "rev_yoy",
    "calculate_parent_holder_net_profit_yoy_growth_ratio": "np_yoy",
    "index_weighted_avg_roe": "roe",
    "sale_gross_margin": "gross_margin",
    "sale_net_interest_ratio": "net_margin",
    "assets_debt_ratio": "debt_ratio",
    "total_assets_turnover_ratio": "asset_turnover",
    "inventory_turnover_ratio": "inv_turnover",
    "current_ratio": "current_ratio",
    "operating_cash_flow_net_divide_income": "ocf_to_income",
    "net_profit_cash_content": "np_cash_content",
    "total_assets_net_ratio": "roa",
}


def fetch_fin(ths):
    """同花顺财务指标（remote）"""
    rows = []
    for y in (2023, 2024, 2025, 2026):
        for q in (1, 2, 3, 4):
            rep = f"{y}-{q}"
            for _ in range(2):
                try:
                    r = subprocess.run(["hithink-finance", "financials", "indicators",
                                        "--thscode", ths, "--report", rep,
                                        "--format", "json", "--source", "remote"],
                                       capture_output=True, text=True, timeout=60)
                    if r.returncode == 0 and r.stdout.strip():
                        d = json.loads(r.stdout)
                        if d.get("ok"):
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
                        break
                except Exception:
                    time.sleep(1)
            time.sleep(0.15)
    return rows


def main():
    os.makedirs(os.path.join(OUT, "daily"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "fin"), exist_ok=True)
    meta = {}

    # 实时快照（换手率/市值）
    snap = fetch_qq_snapshot(list(STOCKS.keys()))
    json.dump(snap, open(os.path.join(OUT, "snapshot.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"实时快照: {len(snap)}/12 只")

    for code, name in STOCKS.items():
        dpath = os.path.join(OUT, "daily", f"{code}.csv")
        fpath = os.path.join(OUT, "fin", f"{code}.csv")

        dl = []
        if not (os.path.exists(dpath) and sum(1 for _ in open(dpath)) > 200):
            dl = fetch_qq_daily(code)
            if dl:
                with open(dpath, "w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=list(dl[0].keys()))
                    w.writeheader()
                    w.writerows(dl)

        fin = []
        if not (os.path.exists(fpath) and sum(1 for _ in open(fpath)) > 3):
            fin = fetch_fin(ths_code(code))
            if fin:
                cols = sorted({k for r in fin for k in r})
                with open(fpath, "w", newline="", encoding="utf-8") as fh:
                    w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
                    w.writeheader()
                    w.writerows(fin)

        nd = sum(1 for _ in open(dpath)) - 1 if os.path.exists(dpath) else 0
        nf = sum(1 for _ in open(fpath)) - 1 if os.path.exists(fpath) else 0
        meta[code] = {"name": name, "daily_days": nd, "fin_periods": nf,
                      "has_snapshot": code in snap}
        print(f"  {code} {name:<6} 日K{nd:>4}天  财务{nf:>2}期  {'新拉' if dl or fin else '缓存'}")

    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"\n✅ 落盘 → {OUT}")


if __name__ == "__main__":
    main()
