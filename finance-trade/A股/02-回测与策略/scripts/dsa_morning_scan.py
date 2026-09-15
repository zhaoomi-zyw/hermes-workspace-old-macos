"""09-02 晨间 DSA 扫描: 用昨日日线算支撑/压力/MA60, 用今日实时价判信号"""
from __future__ import annotations
import numpy as np, pandas as pd, urllib.request, json
from fetch_data import fetch_history
from strategies.dsa_strategy import DSAConfig

WATCH = {
    "603380": "易德龙", "600988": "赤峰黄金", "600460": "士兰微",
    "600522": "中天科技", "002156": "通富微电", "601138": "工业富联",
    "000938": "紫光股份", "600487": "亨通光电", "002396": "星网锐捷",
}
HOLD = {"002396": (100, 40.59)}   # 星网锐捷持仓

def tencent_price(codes):
    syms = [("sh" if c.startswith("6") else "sz") + c for c in codes]
    url = "http://qt.gtimg.cn/q=" + ",".join(syms)
    req = urllib.request.Request(url, headers={"Referer": "http://finance.qq.com"})
    data = urllib.request.urlopen(req, timeout=10).read().decode("gbk")
    out = {}
    for line in data.strip().split(";"):
        line = line.strip()
        if "=" not in line: continue
        hdr, rest = line.split("=", 1)
        code = hdr.replace("v_", "")[-6:]
        f = rest.strip().strip('"').split("~")
        if len(f) > 34:
            out[code] = {"price": float(f[3]), "prev": float(f[4]), "open": float(f[5]),
                         "high": float(f[33]), "low": float(f[34]), "time": f[30],
                         "pct": float(f[32]), "vol_ratio": float(f[49]) if len(f) > 49 and f[49] else None}
    return out

def levels(df, cfg):
    df = df.copy().sort_values("date").reset_index(drop=True)
    # 去掉今日(未收盘)那根: 只剔除 date==today 的partial bar, 保留昨日收盘
    today = pd.Timestamp.now().strftime("%Y-%m-%d")
    df["__d"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df[df["__d"] != today].drop(columns=["__d"]).reset_index(drop=True)
    support = df["low"].rolling(cfg.lookback, min_periods=cfg.lookback).min().shift(1).iloc[-1]
    resistance = df["high"].rolling(cfg.lookback, min_periods=cfg.lookback).max().shift(1).iloc[-1]
    trend_ma = df["close"].rolling(cfg.trend_exit_ma, min_periods=cfg.trend_exit_ma).mean().iloc[-1]
    vol_ma = df["volume"].rolling(cfg.vol_window, min_periods=1).mean().iloc[-1]
    ma5 = df["close"].rolling(5).mean().iloc[-1]
    ma10 = df["close"].rolling(10).mean().iloc[-1]
    return {"support": support, "resistance": resistance, "trend_ma": trend_ma,
            "vol_ma": vol_ma, "ma5": ma5, "ma10": ma10, "last_close": df["close"].iloc[-1],
            "last_date": str(df["date"].iloc[-1].date() if hasattr(df["date"].iloc[-1], "date") else df["date"].iloc[-1])}

def signal(px, L, code):
    cfg = DSAConfig()
    support, resistance, trend = L["support"], L["resistance"], L["trend_ma"]
    # 相对昨收
    pct = (px["price"] / px["prev"] - 1) * 100
    price = px["price"]
    near_support = not np.isnan(support) and price <= support * 1.02
    broke_resist = not np.isnan(resistance) and price > resistance
    in_trend = not np.isnan(trend) and price >= trend
    below_trend = not np.isnan(trend) and price < trend
    broke_support = not np.isnan(support) and price < support
    close_to_sup = not np.isnan(support) and price <= support * 1.03
    close_to_res = not np.isnan(resistance) and price >= resistance * 0.97
    # 低吸位: MA5/MA10 回踩(现价接近MA5/MA10)
    ma5, ma10 = L["ma5"], L["ma10"]
    low_entry = min(ma5, ma10)
    near_ma = price <= ma10 * 1.03  # 现价接近/跌破MA10

    if broke_support:
        sig = "卖出/破位"
    elif below_trend:
        sig = "观望(下跌趋势,不接飞刀)" if not np.isnan(support) else "观望"
    elif broke_resist:
        sig = "持有/站上压力"
    elif near_support:
        sig = "低吸(接近支撑)"
    elif close_to_sup:
        sig = "低吸(接近支撑)"
    elif close_to_res:
        sig = "关注(接近压力)"
    else:
        sig = "观望"
    return sig, pct

def main():
    print("【DSA 晨间扫描 09-02 09:25】")
    # 实时价
    codes = list(WATCH.keys())
    px = tencent_price(codes)
    rows = []
    for code, name in WATCH.items():
        try:
            df = fetch_history(code, name)
            L = levels(df, DSAConfig())
            if code not in px:
                rows.append({"code": code, "name": name, "err": "无实时价"}); continue
            sig, pct = signal(px[code], L, code)
            rows.append({"code": code, "name": name, "px": px[code]["price"], "pct": pct,
                         "support": L["support"], "resistance": L["resistance"], "trend": L["trend_ma"],
                         "ma5": L["ma5"], "ma10": L["ma10"], "signal": sig, "last_close": L["last_close"],
                         "last_date": L["last_date"], "vol_ratio": px[code].get("vol_ratio")})
        except Exception as e:
            rows.append({"code": code, "name": name, "err": str(e)})
    print(json.dumps(rows, ensure_ascii=False, indent=1, default=str))

if __name__ == "__main__":
    main()
