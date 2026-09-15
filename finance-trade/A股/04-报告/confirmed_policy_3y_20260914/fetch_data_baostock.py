# -*- coding: utf-8 -*-
"""
fetch_data_baostock.py  —  confirmed_policy_3y_20260914 研究数据层
==================================================================
只读拉取, 只写本研究目录 data_cache/, 不触碰任何生产文件。

源: baostock (免费公开, 匿名登录, 无需密钥; 不购买数据 / 不绕过访问控制)
口径: adjustflag=2 (前复权) 用于信号与模拟; 另拉 adjustflag=3 (不复权) 用于价格对账

产物:
  data_cache/daily_qfq_<code>.csv     日线前复权 (+tradestatus/isST/turn)
  data_cache/daily_raw_<code>.csv     日线不复权 (对账用)
  data_cache/min5_qfq_<code>.csv      5分钟前复权
  data_cache/trade_dates.csv          交易日历
  data_cache/fetch_log.json           拉取审计
"""
import json
import os
import sys
import time
from pathlib import Path

import pandas as pd

try:
    import baostock as bs
except ImportError:
    print("need: pip install baostock")
    sys.exit(1)

HERE = Path(__file__).resolve().parent
CACHE = HERE / "data_cache"
CACHE.mkdir(parents=True, exist_ok=True)

# signal_daily.STOCKS 的 12 只 (2026-09-14 快照)
STOCKS = {
    "601138": ("工业富联", "sh"),
    "002156": ("通富微电", "sz"),
    "600487": ("亨通光电", "sh"),
    "603380": ("易德龙",   "sh"),
    "600988": ("赤峰黄金", "sh"),
    "600460": ("士兰微",   "sh"),
    "600522": ("中天科技", "sh"),
    "002396": ("星网锐捷", "sz"),
    "600219": ("南山铝业", "sh"),
    "000878": ("云南铜业", "sz"),
    "000938": ("紫光股份", "sz"),
    "600760": ("中航沈飞", "sh"),
}

DAILY_START = "2022-06-01"   # 预热 >100 交易日
MIN5_START  = "2023-06-01"   # 5 分钟预热 (回溯 5 个有效日即可)
END         = "2026-09-14"

DAILY_FIELDS = "date,code,open,high,low,close,preclose,volume,amount,adjustflag,turn,tradestatus,pctChg,isST"
MIN5_FIELDS  = "date,time,code,open,high,low,close,volume,amount,adjustflag"


def rs_to_df(rs):
    rows = []
    while rs.error_code == "0" and rs.next():
        rows.append(rs.get_row_data())
    return pd.DataFrame(rows, columns=rs.fields)


def main():
    log = {"source": "baostock", "daily_start": DAILY_START, "min5_start": MIN5_START,
           "end": END, "stocks": {}, "trade_dates": {}}

    lg = bs.login()
    print("login:", lg.error_code, lg.error_msg, flush=True)
    log["login"] = {"code": lg.error_code, "msg": lg.error_msg}
    if lg.error_code != "0":
        json.dump(log, open(CACHE / "fetch_log.json", "w"), ensure_ascii=False, indent=2)
        return

    # ---- 交易日历 ----
    rs = bs.query_trade_dates(start_date=DAILY_START, end_date=END)
    td = rs_to_df(rs)
    td.to_csv(CACHE / "trade_dates.csv", index=False)
    log["trade_dates"] = {"rows": int(len(td)),
                          "trading_days": int((td["is_trading_day"] == "1").sum()),
                          "err": rs.error_code}
    print("trade_dates:", len(td), flush=True)

    for code, (name, mkt) in STOCKS.items():
        bcode = f"{mkt}.{code}"
        rec = {"name": name, "baostock": bcode}
        for tag, fields, freq, adj, start in [
            ("daily_qfq", DAILY_FIELDS, "d", "2", DAILY_START),
            ("daily_raw", DAILY_FIELDS, "d", "3", DAILY_START),
            ("min5_qfq",  MIN5_FIELDS,  "5", "2", MIN5_START),
        ]:
            fp = CACHE / f"{tag}_{code}.csv"
            if fp.exists() and fp.stat().st_size > 200:
                d = pd.read_csv(fp, dtype=str)
                rec[tag] = {"rows": int(len(d)), "cached": True}
                continue
            for attempt in (1, 2, 3):
                try:
                    rs = bs.query_history_k_data_plus(
                        bcode, fields, start_date=start, end_date=END,
                        frequency=freq, adjustflag=adj)
                    df = rs_to_df(rs)
                    if rs.error_code != "0":
                        raise RuntimeError(f"{rs.error_code} {rs.error_msg}")
                    if len(df) == 0:
                        raise RuntimeError("empty")
                    df.to_csv(fp, index=False)
                    rec[tag] = {"rows": int(len(df)), "cached": False,
                                "first": str(df["date"].iloc[0]),
                                "last": str(df["date"].iloc[-1])}
                    break
                except Exception as e:
                    if attempt == 3:
                        rec[tag] = {"rows": 0, "error": str(e)[:200]}
                    else:
                        time.sleep(1.5 * attempt)
            print(f"{code} {name} {tag}: {rec[tag]}", flush=True)
            time.sleep(0.3)
        log["stocks"][code] = rec

    bs.logout()
    json.dump(log, open(CACHE / "fetch_log.json", "w"), ensure_ascii=False, indent=2)
    print("DONE", flush=True)


if __name__ == "__main__":
    main()
