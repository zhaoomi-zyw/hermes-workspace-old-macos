"""Intraday DSA signal monitor (Sina daily bars + Tencent live price)."""
from __future__ import annotations
import numpy as np, pandas as pd, urllib.request, akshare as ak, time

WATCH = {
    "603380": "易德龙", "600988": "赤峰黄金", "600460": "士兰微",
    "600522": "中天科技", "002156": "通富微电", "601138": "工业富联",
    "000938": "紫光股份", "600487": "亨通光电", "002396": "星网锐捷",
}
TREND_MA = {"601138": 30}   # 工业富联 override

def sina_df(code, days=120):
    sym = ("sh" if code.startswith("6") else "sz") + code
    start = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime("%Y-%m-%d")
    df = ak.stock_zh_a_daily(symbol=sym, start_date=start, adjust="qfq")
    df = df[["date", "open", "high", "low", "close", "volume"]]
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df

def levels(df):
    df = df.copy()
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    df = df[~df["date"].dt.strftime("%Y-%m-%d").eq(today)].reset_index(drop=True)
    support = df["low"].rolling(20).min().shift(1)
    resistance = df["high"].rolling(20).max().shift(1)
    last = df.iloc[-1]
    return {
        "close": float(last["close"]),
        "support": float(support.iloc[-1]) if not np.isnan(support.iloc[-1]) else None,
        "resistance": float(resistance.iloc[-1]) if not np.isnan(resistance.iloc[-1]) else None,
        "ma5": float(df["close"].rolling(5).mean().iloc[-1]),
        "ma10": float(df["close"].rolling(10).mean().iloc[-1]),
        "date": last["date"].strftime("%Y-%m-%d"),
    }

def tencent(code):
    sym = ("sh" if code.startswith("6") else "sz") + code
    url = "http://qt.gtimg.cn/q=" + sym
    req = urllib.request.Request(url, headers={"Referer": "http://finance.qq.com"})
    d = urllib.request.urlopen(req, timeout=10).read().decode("gbk")
    f = d.split('"')[1].split("~")
    return {"price": float(f[3]), "prev": float(f[4]), "high": float(f[33]),
            "low": float(f[34]), "pct": float(f[32])}

print("【盘中 DSA 信号监控 %s】" % pd.Timestamp.now().strftime("%m-%d %H:%M"))
for code, name in WATCH.items():
    try:
        L = levels(sina_df(code))
        px = tencent(code)
        p = px["price"]; sup = L["support"]; res = L["resistance"]
        ma5, ma10 = L["ma5"], L["ma10"]
        low_entry = min(ma5, ma10)
        # signals
        sigs = []
        if sup and p <= sup * 1.02:
            sigs.append("接近20日支撑(低吸区)")
        if res and p >= res * 0.97 and p < res:
            sigs.append("逼近压力")
        if p <= ma10 * 1.02:
            sigs.append("回踩MA10(低吸位%.2f)" % min(ma5, ma10))
        if sup and p < sup:
            sigs.append("破位(跌破支撑)")
        s = " | ".join(sigs) if sigs else "观望(无触发)"
        print(f"{code} {name} 现价{p:.2f} ({px['pct']:+.2f}%) 昨收:{L['close']:.2f} "
              f"MA5:{ma5:.2f} MA10:{ma10:.2f} 支撑:{sup if sup else 0:.2f} 压力:{res if res else 0:.2f} -> {s}")
    except Exception as e:
        print(f"{code} {name} ERR: {e}")
    time.sleep(0.3)
