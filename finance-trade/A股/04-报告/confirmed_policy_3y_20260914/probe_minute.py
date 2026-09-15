# -*- coding: utf-8 -*-
"""探测分钟数据真实可得范围(东财/新浪), 不改任何生产文件。"""
import json, sys, traceback
from datetime import datetime
import akshare as ak
import pandas as pd

out = {}

def probe(name, fn):
    try:
        df = fn()
        if df is None or len(df)==0:
            out[name] = {"ok": False, "err": "empty"}
            return
        cols = list(df.columns)
        # 找时间列
        tcol = None
        for c in ["时间","day","date","datetime","time"]:
            if c in df.columns:
                tcol = c; break
        rec = {"ok": True, "rows": int(len(df)), "cols": cols}
        if tcol:
            rec["tcol"] = tcol
            rec["first"] = str(df[tcol].iloc[0])
            rec["last"] = str(df[tcol].iloc[-1])
        # 每日条数
        if tcol:
            try:
                d = pd.to_datetime(df[tcol]).dt.date
                vc = d.value_counts()
                rec["n_days"] = int(len(vc))
                rec["bars_per_day_max"] = int(vc.max())
                rec["bars_per_day_min"] = int(vc.min())
            except Exception as e:
                rec["daycount_err"] = str(e)
        out[name] = rec
    except Exception as e:
        out[name] = {"ok": False, "err": type(e).__name__+": "+str(e)[:200]}

# 1) 东财 5分钟, 尝试拉 3 年
probe("em_5min_3y", lambda: ak.stock_zh_a_hist_min_em(symbol="601138", start_date="2023-09-14 09:30:00", end_date="2026-09-14 15:00:00", period="5", adjust="qfq"))
# 2) 东财 5分钟, 无 adjust
probe("em_5min_3y_noqfq", lambda: ak.stock_zh_a_hist_min_em(symbol="601138", start_date="2023-09-14 09:30:00", end_date="2026-09-14 15:00:00", period="5", adjust=""))
# 3) 东财 1分钟
probe("em_1min_3y", lambda: ak.stock_zh_a_hist_min_em(symbol="601138", start_date="2023-09-14 09:30:00", end_date="2026-09-14 15:00:00", period="1", adjust="qfq"))
# 4) 新浪 5分钟
probe("sina_5min", lambda: ak.stock_zh_a_minute(symbol="sh601138", period="5", adjust="qfq"))
# 5) 新浪 1分钟
probe("sina_1min", lambda: ak.stock_zh_a_minute(symbol="sh601138", period="1", adjust="qfq"))

print(json.dumps(out, ensure_ascii=False, indent=2))
