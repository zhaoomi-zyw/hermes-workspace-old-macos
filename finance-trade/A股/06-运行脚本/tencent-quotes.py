#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯实时行情注入脚本 (cron script)
=================================
从 qt.gtimg.cn 抓取指定股票实时行情，输出结构化文本注入 cron prompt。
agent 无需再用 anysearch 搜索股价——直接拿到精确实时价。

用法: python3 tencent-quotes.py "sh600522,sh601138,sz000938,sz002475,sh601899"
输出: 每只股票一行: 名称 代码 现价 涨跌幅% 昨收 今开 最高 最低 成交量(手) 成交额(万) 时间
默认代码: 中天科技, 工业富联, 紫光股份, 立讯精密, 紫金矿业, 博众精工, 易德龙, 赤峰黄金, 士兰微, 云铝, 通富微电, 亨通光电
"""
import urllib.request
import sys
import os
import importlib.util

# 交易日历门控 (2026-09-02): 非交易日不输出行情注入(节假日静默)。
# 注意: 本脚本常被 LLM cron 用作行情注入; LLM 层自身也判定交易日, 此处为第二道防线。
_HERE = os.path.dirname(os.path.abspath(__file__))
_CAL = None
def _load_calendar():
    global _CAL
    if _CAL is None:
        p = os.path.join(_HERE, "cn_trading_calendar.py")
        if os.path.exists(p):
            spec = importlib.util.spec_from_file_location("cn_trading_calendar", p)
            _CAL = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(_CAL)
        else:
            _CAL = False
    return _CAL or None


def calendar_ok_today() -> bool:
    """True=交易日可输出行情; False=非交易日/unknown(fail-closed, 不输出行情)。"""
    cal = _load_calendar()
    if cal is None:
        return False
    return cal.should_run_today()

DEFAULT_CODES = [
    "sh600988",  # 赤峰黄金(持仓)
    "sz000878",  # 云南铜业(持仓)
    "sh601138",  # 工业富联
    "sz002156",  # 通富微电
    "sh600487",  # 亨通光电
    "sh600522",  # 中天科技
    "sh603380",  # 易德龙
    "sh600460",  # 士兰微
    "sz002396",  # 星网锐捷
    "sz000938",  # 紫光股份
    "sh600219",  # 南山铝业
    "sh600760",  # 中航沈飞
]

def fetch(codes):
    url = "http://qt.gtimg.cn/q=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"Referer": "http://finance.qq.com"})
    data = urllib.request.urlopen(req, timeout=10).read().decode("gbk")
    lines = []
    for line in data.strip().split(";"):
        line = line.strip()
        if not line or "=" not in line or '="' not in line:
            continue
        f = line.split('="')[1].rstrip('"').split("~")
        if len(f) < 35:
            continue
        # 字段: 1名称 2代码 3现价 4昨收 5今开 6成交量(手) 30时间 31涨跌额 32涨跌幅 33最高 34最低
        name, code = f[1], f[2]
        price, prev, open_p = f[3], f[4], f[5]
        pct, high, low = f[32], f[33], f[34]
        vol, t = f[6], f[30]
        lines.append(
            f"{name}({code}) 现价:{price} 涨跌幅:{pct}% 昨收:{prev} 今开:{open_p} "
            f"最高:{high} 最低:{low} 成交量:{vol}手 时间:{t}"
        )
    return lines

def main():
    # 交易日历门控 (fail-closed): 非交易日不输出行情
    if not calendar_ok_today():
        return  # 空输出 => 不注入行情
    codes = sys.argv[1].split(",") if len(sys.argv) > 1 else DEFAULT_CODES
    try:
        out = fetch(codes)
    except Exception as e:
        print(f"[腾讯行情获取失败] {e}")
        sys.exit(0)  # 不中断, 留给 agent 兜底
    if not out:
        print("[腾讯行情: 无数据]")
        return
    print("【腾讯实时行情 " + __import__("datetime").datetime.now().strftime("%m-%d %H:%M") + "】")
    for l in out:
        print(l)

if __name__ == "__main__":
    main()
