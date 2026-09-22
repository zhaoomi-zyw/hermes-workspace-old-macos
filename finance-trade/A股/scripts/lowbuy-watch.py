#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自选股低吸监控 — BUY-LOW-v1 (实盘入口)
========================================
规则与参数唯一来源: /Users/omi/workspace/quant-backtest/strategies/buy_policy.py
持仓(不加仓判定) <- ~/.hermes/state/sell-policy-state.json

⚠️ 2026-09-16 手动数量模式（用户指令）：**买多少由用户自行决定**。
   · 已取消：自动推荐/计算最大股数；单笔净资产2% / 组合4% / 单股35% 作为提醒门槛；
             现金不足 / 净资产未知 / 不足一手 → 一律**不再屏蔽**合格信号。
   · 提醒内不再出现 最大股数 / 可买股数 / 资金缺口 / 风险预算预占，只给信号与价格依据，
     并固定声明"买入数量由你自行决定，请在券商端核对可用资金、交易单位与费用"。
   · 保留：单一待确认建议（去重，不连续轰炸）、15分钟有效期、到期需重新核验、
           成交/撤单未确认前不擅自释放或改写。

三条件(模块实现):
  ① 价 > 已完成日MA60 且 MA60 > 5交易日前MA60
  ② 2.5 <= (H20-价)/ATR14 <= 4.5 且 价 > MA60
  ③ 当日同刻累计量 / 前5交易日同刻均量 < 0.80 (缺失=>无法确认=>不放行)

时段 09:45-11:30 / 13:00-14:45; 排序 MA60 5日涨幅降序只取第一。
数据: 腾讯实时(量=手×100=股) + 新浪5分钟K(量=股)
"""
from __future__ import annotations

import datetime
import json
import os
import re
import sys
import urllib.request

_QP = "/Users/omi/workspace/quant-backtest/strategies"
if _QP not in sys.path:
    sys.path.insert(0, _QP)

import buy_policy as BP  # noqa: E402

POLICY_VERSION = BP.POLICY_VERSION

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
}


def calendar_gate():
    try:
        import cn_trading_calendar as cal
        st = cal.calendar_status(datetime.date.today())
        if st and not st.get("is_trading", False):
            return False
    except Exception:
        pass
    return True


def _http(url, headers, timeout=15):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=timeout).read()


def fetch_realtime(codes):
    data = _http("http://qt.gtimg.cn/q=" + ",".join(codes),
                 {"Referer": "http://finance.qq.com"}).decode("gbk")
    out = {}
    for line in data.strip().split(";"):
        line = line.strip()
        if not line or "=" not in line or '="' not in line:
            continue
        key = line.split("=")[0].strip()
        code = key[2:] if key.startswith("v_") else key
        f = line.split('="')[1].rstrip('"').split("~")
        if len(f) < 35:
            continue
        try:
            out[code] = {"name": f[1], "price": float(f[3]), "prev": float(f[4]),
                         "pct": float(f[32]), "vol": float(f[36]) * 100, "time": f[30]}
        except (ValueError, IndexError):
            continue
    return out


def fetch_day_kline(code, n=160):
    url = f"http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={code},day,,,{n},qfq"
    j = json.loads(_http(url, {"Referer": "http://finance.qq.com"}).decode("utf-8"))
    c = (j.get("data") or {}).get(code) or {}
    rows = c.get("qfqday") or c.get("day") or []
    out = []
    for r in rows:
        try:
            out.append({"date": r[0], "open": float(r[1]), "close": float(r[2]),
                        "high": float(r[3]), "low": float(r[4]), "volume": float(r[5])})
        except (ValueError, IndexError):
            continue
    return out


def fetch_min5(code, datalen=600):
    url = ("https://quotes.sina.cn/cn/api/jsonp_v2.php/x/"
           f"CN_MarketDataService.getKLineData?symbol={code}&scale=5&ma=no&datalen={datalen}")
    txt = _http(url, {"Referer": "https://finance.sina.com.cn"}, timeout=25).decode("utf-8", "ignore")
    m = re.search(r"x\((.*)\)", txt, re.S)
    if not m:
        return []
    out = []
    for b in json.loads(m.group(1)):
        try:
            out.append({"dt": datetime.datetime.strptime(b["day"], "%Y-%m-%d %H:%M:%S"),
                        "day": b["day"][:10], "high": float(b["high"]),
                        "low": float(b["low"]), "close": float(b["close"]),
                        "volume": float(b["volume"])})
        except Exception:
            continue
    return out


def eval_one(code, name, price, today, now):
    day = fetch_day_kline(code)
    comp = [r for r in day if r["date"] != today]
    if len(comp) < BP.MA60_N + BP.MA60_LOOKBACK + 1:
        return None
    closes = [r["close"] for r in comp]
    highs = [r["high"] for r in comp]
    ms = BP.ma60_series(closes)
    ma60_now, ma60_5ago = ms[-1], ms[-1 - BP.MA60_LOOKBACK]
    if not BP.trend_ok(price, ma60_now, ma60_5ago):
        return None
    atr = BP.atr14_wilder(comp)
    h20 = BP.h20(highs)
    band_ok, dev = BP.atr_band_ok(price, h20, atr, ma60_now)
    if not band_ok:
        return None
    min5 = fetch_min5(code)
    ratio, detail, confirmed = BP.same_time_vol_ratio(min5, now)
    if not BP.vol_ratio_ok(ratio, confirmed):
        return None
    lo, hi = BP.allowed_price_range(h20, atr, ma60_now)
    return {"code": code, "name": name, "price": price, "ma60": ma60_now,
            "ma60_chg": BP.ma60_change_pct(ma60_now, ma60_5ago), "atr": atr,
            "h20": h20, "dev": dev, "vol_ratio": ratio, "vol_detail": detail,
            "lo": lo, "hi": hi}


def main():
    now = datetime.datetime.now()
    if now.weekday() > 4 or not BP.in_session(BP.now_hhmm(now)):
        return
    if not calendar_gate():
        return

    # 持仓仅用于"持仓股不加仓"判定; 账户/净资产不可读**不得屏蔽合格信号**(2026-09-16)
    try:
        acc = BP.load_account()
        holdings = acc.get("holdings") or {}
    except Exception:
        holdings = {}

    try:
        rt = fetch_realtime(list(WATCHLIST.keys()))
    except Exception:
        return
    today = now.strftime("%Y-%m-%d")

    st = BP.load_state()
    BP.roll_day(st, today)
    BP.mark_needs_recheck(st, now)
    if BP.pending_active(st):
        BP.save_state(st)
        return

    cands = []
    for code, name in WATCHLIST.items():
        if code in holdings:
            continue
        q = rt.get(code)
        if not q or q["price"] <= 0:
            continue
        try:
            c = eval_one(code, name, q["price"], today, now)
        except Exception:
            c = None
        if c:
            cands.append(c)
    if not cands:
        BP.save_state(st)
        return

    cands.sort(key=BP.rank_key)

    # ⚠️ 2026-09-16 手动数量模式（用户指令）：
    #   只提醒排序第一；**买多少由用户自行决定**。
    #   不再计算最大股数；不再以 现金/净资产/单笔2%/组合4%/单股35%/不足一手 作门槛（全部取消）。
    #   不做虚拟资金或风险预算预占；仍保留单一待确认建议 + 通知去重 + 成交确认。
    chosen = cands[0]
    can, why = BP.can_recommend(st, today, chosen["code"])
    if not can:
        BP.save_state(st)
        return

    rec = BP.issue_alert(st, today, chosen["code"], chosen["price"],
                         chosen["lo"], chosen["hi"], now=now)
    BP.save_state(st)
    if not rec:
        return

    c = chosen
    out = [
        f"【自选股低吸提醒 {now.strftime('%H:%M')}】{BP.POLICY_VERSION_MANUAL}",
        "",
        f"🟢 低吸条件满足 {c['name']}({c['code'][2:]})",
        f"  现价 {c['price']:.2f}  数据时间 {now.strftime('%H:%M')}",
        f"  ①趋势: 价>MA60({c['ma60']:.2f}) 且 MA60较5日前 {c['ma60_chg']:+.2f}% ✓",
        f"  ②ATR回调: (H20 {c['h20']:.2f} − 价)/ATR14 {c['atr']:.2f} = {c['dev']:.2f} (2.5~4.5) ✓",
        f"  ③缩量: 同刻量比 {c['vol_ratio']:.2f} (<0.80) ✓  [{c['vol_detail']}]",
        "",
        f"  允许价格区间: {c['lo']:.2f} ~ {c['hi']:.2f}",
        f"  参考限价: {c['price']:.2f}",
        f"  止损参考 -6% = {c['price'] * (1 - BP.HARD_STOP_PCT):.2f} (持仓后按 SELL-POLICY 执行)",
        f"  有效期: 至 {rec['expires']} (15分钟; 超时需重新核验价格与三条件)",
        "",
        f"  {BP.MANUAL_SIZE_NOTE}",
        "",
        "⚠️ 仅为条件提醒, 不代表成交; 若下单请在券商端手动限价买入。",
    ]
    others = [f"{x['name']}" for x in cands[1:]]
    if others:
        out += ["", "其他合格候选(本次未推): " + "、".join(others)]
    print("\n".join(out))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            import traceback
            log = os.path.expanduser("~/.hermes/state/lowbuy-watch.err.log")
            os.makedirs(os.path.dirname(log), exist_ok=True)
            with open(log, "a") as f:
                f.write(f"[{datetime.datetime.now().isoformat()}] {e}\n{traceback.format_exc()}\n")
        except Exception:
            pass
