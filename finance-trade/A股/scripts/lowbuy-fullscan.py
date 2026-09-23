#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""低吸三条件【全量扫描】—— 逐只输出①②③判定（不只报合格名单）

用途：BUY-LOW-v1 只推送"全满足"的标的；本脚本额外给出每只卡在哪一条，
     便于人工判断"接近满足"的标的（如只差③缩量）。

⚠️ 判定一律调用 buy_policy 的权威函数，不自行实现阈值逻辑。
   数据源：腾讯实时行情 + 日K（前复权）+ 5分钟K。

⚠️ ③缩量的 as-of 语义（2026-09-23 修正说明）
   same_time_vol_ratio(min5, now) 的基准时点取 `now`：
     · 盘中运行  → 分子/分母都是「至 now 的同刻累计」= 真正同刻口径 ✅
     · 盘后运行  → now 落在 15:00 后，分子/分母双双退化为「全天」，
                  等价于 vol_ratio_close 的全天口径 → 不是同刻口径 ⚠️
   本脚本盘后运行时会显式把③标为「盘后不可判」，并另列全天口径供参考，
   避免给出「看似通过」的误导值。（实证：云南铜业 2026-09-23 同刻 11:30=0.967❌
   而全天=0.659✅，同一数据结论相反。）
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
    # ⭐ 2026-09-22 用户明确批准加入（第13只）
    # ⚠️ 与自选 sz002396 星网锐捷为【母子公司】：星网锐捷持锐捷网络 44.88%，
    #    锐捷网络贡献星网锐捷约 75% 收入与利润 → 两者风险敞口高度重叠
    "sz301165": "锐捷网络",
    # ⭐ 2026-09-22 用户明确批准加入（第 14/15 只）—— 医药簇，池内首个非「科技/资源/军工」方向
    #    分散性实测：恒瑞 vs 原13只等权 +0.06（几乎无关）；海思科 +0.23（偏同向，可接受）
    #    两者互相关 +0.44（同属化学制药，正常）
    #    财务(2026中报)：恒瑞 毛利86.3%/ROE8.04%/营收-1.9% ｜ 海思科 毛利80.2%/ROE18.30%/营收+54.7%
    #    ATR%：恒瑞 2.55% ｜ 海思科 4.11%（入池标准②要求 ≤5%，均合格）
    "sh600276": "恒瑞医药", "sz002653": "海思科",
    # ⭐ 2026-09-22 用户明确批准加入（第 16 只）—— 中药（医药簇内第 3 只）
    #    分散性实测：云南白药 vs 原13只(不含医药) = -0.36（强负相关 ⭐）
    #    医药簇内部：vs 恒瑞 +0.40 ｜ vs 海思科 +0.18 ｜ 簇内平均 +0.34
    #    参考：云南白药↔同仁堂 +0.76、↔片仔癀 +0.56 → 「中药」内部高度同质，故只入 1 只
    #    财务(2026中报)：毛利/ROE 见主文件 §二；ATR ~1.28%（池内最低波动）
    "sz000538": "云南白药",
    # ⭐ 2026-09-22 加入（第17只）—— 半导体材料，一级缺口；单股上限例外(一手7107=净值52%)
    "sz300054": "鼎龙股份",
}


def _load_holdings():
    """读当前持仓（sell-policy-state 权威）→ 用于标注「持仓股不加仓」"""
    try:
        import json as _j
        sp = _j.load(open(os.path.expanduser("~/.hermes/state/sell-policy-state.json"), encoding="utf-8"))
        return {c: (p.get("name"), p.get("total_qty")) for c, p in (sp.get("positions") or {}).items()}
    except Exception:
        return {}


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
    # ⭐ ③缩量的 as-of 模式：盘中 = 同刻口径（有效）；盘后 = 全天口径（非"同刻"，仅参考）
    vol_same_time = in_sess

    lines = [f"📊 低吸三条件全量扫描  {now:%Y-%m-%d %H:%M}",
             f"策略 {BP.POLICY_VERSION}｜时段内 {'✅' if in_sess else '⚠️否（结论仅供参考）'}",
             f"范围 {len(WATCHLIST)} 只自选股",
             (f"③口径：同刻（as-of {now:%H:%M}）" if vol_same_time
              else "③口径：⚠️ 盘后——无「同刻」可言，③不可判；下表另列「全天口径」仅供参考"), ""]

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
            rows.append((name, None, None, None, None, None, None, "无行情", None))
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
            HELD = _load_holdings()
            _m5 = fetch_min5(code)
            vr, vdet, vconf = BP.same_time_vol_ratio(_m5, now)
            # ⭐ 盘后：同刻口径无意义 → 不参与判定，另取全天口径作参考
            vr_close = None
            if vol_same_time:
                v = BP.vol_ratio_ok(vr, vconf) if vconf else False
            else:
                v = None                              # 不可判
                _vc, _vd, _vcc = BP.vol_ratio_close(_m5, today)
                vr_close = _vc if _vcc else None
            ok = bool(t and a and v)
            miss = []
            if not t:
                miss.append("①")
            if not a:
                miss.append("②")
            if v is False:
                miss.append("③")
            elif v is None:
                miss.append("③?")
            _held = code in HELD
            _tag = "、".join(miss) if miss else "无(全满足)"
            if _held:
                _tag += "  ⚠️持仓·不加仓"
            rows.append((name, price, ma60, dev, vr, vconf, (t, a, v), _tag, vr_close))
            if ok and not _held and vol_same_time:
                lo, hi = BP.allowed_price_range(h20, atr, ma60)
                hits.append((name, code, price, ma60, dev, vr, lo, hi))
        except Exception as e:
            rows.append((name, price, None, None, None, None, None, f"计算异常:{type(e).__name__}", None))

    lines.append("逐只明细（①趋势 ②位置 ③缩量）" + ("" if vol_same_time
                 else "  ⚠️ ③为盘后口径，不可判；括号内为全天参考值"))
    lines.append("名称        现价    MA60   偏离  量比(③)  ①②③  卡点")
    for name, price, ma60, dev, vr, vconf, flags, miss, vr_close in rows:
        if price is None:
            lines.append(f"{name:<10} 无数据")
            continue
        fl = flags if flags else (None, None, None)
        # ①② 恒可判；③ 盘中可判 / 盘后不可判（None → 显示 —）
        s = "".join("✅" if x is True else ("—" if x is None else "❌") for x in fl)
        if vol_same_time:
            voltxt = (f"{vr:.2f}" if vr is not None else "n/a")
        else:
            voltxt = ("不可判" + (f"({vr_close:.2f}全天)" if vr_close is not None else ""))
        lines.append("{:<10}{:>7.2f}{:>8}{:>7}{:>9}  {:<6}{}".format(
            name, price,
            f"{ma60:.2f}" if ma60 else "-",
            f"{dev:.2f}" if dev is not None else "-",
            voltxt, s, miss))

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
