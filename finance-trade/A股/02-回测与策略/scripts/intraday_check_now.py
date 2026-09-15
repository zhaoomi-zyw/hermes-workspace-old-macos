#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""盘中DSA信号检查: 用昨日收盘的支撑/压力/趋势 vs 今日实时价判断买入信号"""
import sys, urllib.request, warnings
warnings.filterwarnings("ignore")
import pandas as pd, numpy as np
sys.path.insert(0, "/Users/omi/workspace/quant-backtest")
import signal_daily as sd

CODES = {
    "688097":("博众精工","sh688097"), "603380":("易德龙","sh603380"),
    "600988":("赤峰黄金","sh600988"), "600460":("士兰微","sh600460"),
    "000807":("云铝股份","sz000807"), "601899":("紫金矿业","sh601899"),
    "600522":("中天科技","sh600522"), "002156":("通富微电","sz002156"),
    "601138":("工业富联","sh601138"), "000938":("紫光股份","sz000938"),
    "600487":("亨通光电","sh600487"), "002475":("立讯精密","sz002475"),
}

# 实时行情
def realtime(codes):
    q = ",".join(codes)
    req = urllib.request.Request("http://qt.gtimg.cn/q="+q,
                                 headers={"Referer":"http://finance.qq.com"})
    raw = urllib.request.urlopen(req, timeout=10).read().decode("gbk")
    out = {}
    for line in raw.strip().split(";"):
        if "=" not in line: continue
        key, body = line.split("=",1)
        f = body.strip('"').split("~")
        if len(f) < 35: continue
        code = f[2]  # 6位代码字段
        f = body.strip('"').split("~")
        out[code] = dict(name=f[1], price=float(f[3]), prev=float(f[4]),
                         pct=float(f[32]), high=float(f[33]), low=float(f[34]),
                         vol=float(f[36]), time=f[30])
    return out

def fetch_daily(code):
    """用本地csv或akshare东财/新浪取日线, 返回df[date,open,high,low,close,volume]"""
    import os, akshare as ak
    p = f"/Users/omi/workspace/quant-backtest/data/{code}_{CODES[code][0]}.csv"
    if os.path.exists(p):
        df = pd.read_csv(p)
        df["date"]=pd.to_datetime(df["date"])
        return df.sort_values("date").reset_index(drop=True)
    try:
        df = ak.stock_zh_a_hist(symbol=code, period="daily", adjust="qfq")
        df = df.rename(columns={"日期":"date","开盘":"open","最高":"high","最低":"low","收盘":"close","成交量":"volume"})
        df["date"]=pd.to_datetime(df["date"])
        return df[["date","open","high","low","close","volume"]].sort_values("date").reset_index(drop=True)
    except Exception:
        prefix = "sh" if code[0]=="6" else "sz"
        df = ak.stock_zh_a_daily(symbol=prefix+code, adjust="qfq")
        df["date"]=pd.to_datetime(df["date"])
        return df[["date","open","high","low","close","volume"]].sort_values("date").reset_index(drop=True)

rt = realtime([c for _,c in CODES.values()])
print(f"{'代码':<8}{'名称':<6}{'现价':>8}{'涨跌%':>7}  DSA评估")
print("="*70)
for code,(name,_) in CODES.items():
    d = rt.get(code)
    if not d: continue
    try:
        df = fetch_daily(code)
        cfg = sd.get_cfg(code)
        lookback = cfg.lookback
        if len(df) < lookback+5:
            print(f"{code:<8}{name:<6}  数据不足({len(df)})"); continue
        last = df.iloc[-1]
        y_high = df["high"].rolling(lookback,min_periods=lookback).max().shift(1).iloc[-1]
        y_low  = df["low"].rolling(lookback,min_periods=lookback).min().shift(1).iloc[-1]
        vol_ma = df["volume"].rolling(cfg.vol_window,min_periods=1).mean().iloc[-1]
        tma    = df["close"].rolling(cfg.trend_exit_ma,min_periods=cfg.trend_exit_ma).mean().iloc[-1]
        p = d["price"]
        # 实时量比近似: 用实时成交量/昨日同时段, 简单用vol vs vol_ma粗判
        near_sup = d["low"] <= y_low*1.02
        broke_res = p > y_high
        trend_ok = p > tma
        # 量比 f[49]未取, 用实时成交量与vol_ma比例(全天数据不全,粗估)
        tags=[]
        if broke_res and trend_ok: tags.append("放量突破压力↑")
        elif near_sup and trend_ok: tags.append("回踩支撑(接近)")
        elif near_sup and not trend_ok: tags.append("回踩支撑但趋势弱")
        elif p < y_low: tags.append("跌破支撑⚠")
        else: tags.append("区间震荡")
        print(f"{code:<8}{name:<6}{p:>8.2f}{d['pct']:>7.2f} 支撑{y_low:.2f}/压力{y_high:.2f}/趋势MA{tma:.2f} | {tags[0]}")
    except Exception as e:
        print(f"{code:<8}{name:<6}  错误:{str(e)[:40]}")
