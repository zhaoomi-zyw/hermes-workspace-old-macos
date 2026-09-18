#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""低吸三条件【全量扫描】—— 逐只输出①②③判定（不只报合格名单）

用途：BUY-LOW-v1 只推送"全满足"的标的；本脚本额外给出每只卡在哪一条，
     便于人工判断"接近满足"的标的（如只差③缩量）。

⚠️ 判定一律调用 buy_policy 的权威函数，不自行实现阈值逻辑。
   数据源：腾讯实时行情 + 日K（前复权）+ 5分钟K。
"""
import os
import sys
import json
import datetime
import urllib.request

sys.path.insert(0, "/Users/omi/workspace/quant-backtest/strategies")
import buy_policy as BP  # noqa: E402

WATCHLIST = {
    "sh601138": "工业富联", "sz002156": "通富微电", "sh600460": "士兰微",
    "sh603380": "易德龙", "sz002396": "星网锐捷", "sh600487": "亨通光电",
    "sh600522": "中天科技", "sh600988": "赤峰黄金", "sh600219": "南山铝业",
    "sz000878": "云南铜业", "sh600760": "中航沈飞", "sz000938": "紫光股份",
}


def _http(url, timeout=20):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"Referer": "http://finance.qq.com"}),
        timeout=timeout).read()


def fetch_realtime(codes):
    out = {}
    raw = _http("http://qt.gtimg.cn/q=" + ",".join(codes)).decode("gbk", "ignore")
    for line in raw.strip().split(";"):
        if "=" not in line:
            continue
        key = line.split("=")[0].replace("v_", "").strip()   # ⚠️ 必须 strip：腾讯第2段起带换行符
        f = line.split("=", 1)[1].strip().strip('"').split("~")
        if len(f) < 40:
            continue
        try:
            out[key] = {"name": f[1], "price": float(f[3]), "prev": float(f[4]),
                        "vol": float(f[6]), "time": f[30]}
        except (ValueError, IndexError):
            continue
    return out


def fetch_day_kline(code, n=200):
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,{n},qfq"
    d = json.loads(_http(url, 25).decode())
    node = d["data"][code]
    k = node.get("qfqday") or node.get("day")
    return [{"date": x[0], "open": float(x[1]), "close": float(x[2]),
             "high": float(x[3]), "low": float(x[4]), "vol": float(x[5])} for x in k]


def fetch_min5(code, n=600):
    url = f"https://ifzq.gtimg.cn/appstock/app/kline/mkline?param={code},m5,,{n}"
    d = json.loads(_http(url, 25).decode())
    k = (d.get("data") or {}).get(code, {}).get("m5") or []
    out = []
    for x in k:
        try:
            dt = datetime.datetime.strptime(str(x[0])[:12], "%Y%m%d%H%M")
            out.append({"dt": dt, "day": dt.strftime("%Y-%m-%d"), "volume": float(x[5])})
        except Exception:
            pass
    return out


def main():
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    in_sess = BP.in_session(BP.now_hhmm(now))

    lines = [f"📊 低吸三条件全量扫描  {now:%Y-%m-%d %H:%M}",
             f"策略 {BP.POLICY_VERSION}｜时段内 {'✅' if in_sess else '⚠️否（结论仅供参考）'}",
             f"范围 {len(WATCHLIST)} 只自选股", ""]

    try:
        rt = fetch_realtime(list(WATCHLIST.keys()))
    except Exception as e:
        print(f"[扫描失败] 行情抓取异常 {type(e).__name__}: {e}")
        return
    if not rt:
        print("[扫描失败] 行情为空")
        return

    rows, hits = [], []
    for code, name in WATCHLIST.items():
        q = rt.get(code)
        if not q:
            rows.append((name, None, None, None, None, None, None, "无行情"))
            continue
        price = q["price"]
        try:
            day = fetch_day_kline(code)
            comp = [r for r in day if r["date"] != today]
            closes = [r["close"] for r in comp]
            highs = [r["high"] for r in comp]
            ms = BP.ma60_series(closes)
            ma60, ma60_5 = ms[-1], ms[-1 - BP.MA60_LOOKBACK]
            atr = BP.atr14_wilder(comp)
            h20 = BP.h20(highs)
            t = BP.trend_ok(price, ma60, ma60_5)
            a, _ = BP.atr_band_ok(price, h20, atr, ma60)
            dev = BP.atr_deviation(price, h20, atr)
            vr, vdet, vconf = BP.same_time_vol_ratio(fetch_min5(code), now)
            v = BP.vol_ratio_ok(vr, vconf) if vconf else False
            ok = bool(t and a and v)
            miss = []
            if not t:
                miss.append("①")
            if not a:
                miss.append("②")
            if not v:
                miss.append("③")
            rows.append((name, price, ma60, dev, vr, vconf, (t, a, v), "、".join(miss) or "无(全满足)"))
            if ok:
                lo, hi = BP.allowed_price_range(h20, atr, ma60)
                hits.append((name, code, price, ma60, dev, vr, lo, hi))
        except Exception as e:
            rows.append((name, price, None, None, None, None, None, f"计算异常:{type(e).__name__}"))

    lines.append("逐只明细（①趋势 ②位置 ③缩量）")
    lines.append("名称        现价    MA60   偏离  量比   ①②③  卡点")
    for name, price, ma60, dev, vr, vconf, flags, miss in rows:
        if price is None:
            lines.append(f"{name:<10} 无数据")
            continue
        fl = flags if flags else (None, None, None)
        s = "".join("✅" if x else ("⏳" if x is False and vconf is False else "❌")
                    for x in fl) if all(x is not None for x in fl) else "—"
        lines.append("{:<10}{:>7.2f}{:>8}{:>7}{:>7}  {:<6}{}".format(
            name, price,
            f"{ma60:.2f}" if ma60 else "-",
            f"{dev:.2f}" if dev is not None else "-",
            (f"{vr:.2f}" if vr is not None else "n/a"),
            s, miss))

    lines.append("")
    if hits:
        lines.append("🔥 三条件全满足：")
        for name, code, price, ma60, dev, vr, lo, hi in hits:
            lines.append(f"  {name}({code[2:]}) 现价 {price:.2f}")
            lines.append(f"    ①价>MA60 {ma60:.2f} ✓  ②偏离 {dev:.2f} ✓  ③量比 {vr:.2f} ✓")
            lines.append(f"    参考限价区间 {lo:.2f} ~ {hi:.2f}")
        lines.append("")
        lines.append("→ 低吸监控会另行推送合格标的（含15分钟有效期）")
    else:
        lines.append("🔥 三条件全满足：无")
        near = [r for r in rows if r[7] and len(r[7]) == 1]
        if near:
            lines.append("")
            lines.append("⚠️ 接近满足（只差1项）：")
            for r in near:
                lines.append(f"  {r[0]}  只差 {r[7]}")

    lines.append("")
    lines.append("⚠️ 本扫描为条件显示，非买入建议；数量由你自行决定。")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
