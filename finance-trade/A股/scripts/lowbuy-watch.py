#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自选股低吸监控 — BUY-LOW-v1.2 (实盘入口)
=========================================
版本: BUY-LOW-v1.2-20260922  (叠加在 BUY-LOW-v1-manual-20260916 之上)

与 v1.1 的差异（v1.2 新增/变更）:
  1. 只允许 09:45–11:30 / 13:00–14:45 连续竞价时段；扫描频率升为每 5 分钟（由 cron 控制）。
  2. 日线趋势 ①：现价 > 最近完成交易日 MA60，且 MA60 > 5 个完成交易日前 MA60   [复用 BP]
  3. ATR 回调 ②：2.5 <= (H20 - 现价)/ATR14 <= 4.5，ATR14 = Wilder 口径           [复用 BP]
  4. 同刻缩量 ③：当日累计量 / 前 5 个完成交易日同时刻累计量均量，**严格 < 0.70**
     （v1.1 为 < 0.80；用户确认采用缩量阈值 0.70）对齐只用**已完成 5 分钟 bar**，当前未完成 bar 不计入。
  5. ⭐ 新增 相对强度：个股近 20 个完成交易日收益 >= 沪深300 近 20 个完成交易日收益（同日对齐）
  6. ⭐ 新增 开盘跳空门槛：当日开盘 <= 前一交易日收盘 × 1.015；不满足则该股当天不发提醒
  7. ⭐ 新增 市场状态（沪深300，上一完整交易日收盘后计算，次日生效）：
       弱市 = 连续 3 日、每日满足 {收盘<MA60, MA20<=5日前MA20, 距近60日最高收盘回撤>=8%} 中至少 2 项
       恢复正常 = 连续 3 日：收盘>MA20 且 MA20>5日前MA20
       正常市提示「新增总仓位上限75% / 单只目标25%」；弱市提示「新增总仓位上限60% / 单只目标20%」
  8. 跳过已有持仓 + 清仓后的防买回期(§6)；多候选按 20 日相对沪深300收益 降序，只把第 1 名作为可执行提醒
  9. 15 分钟有效期 + 持久化状态 + 原子锁去重；异常/行情缺失/同刻基准不足 => 不发提醒并写日志
 10. 微信文案含：股票/代码/扫描时间/价格/三条件数值/同刻量比/20日相对强度/市场状态/仓位上限/到期时刻

边界（不变）:
  · 只发微信提醒，**不自动下单**；数量由用户自主决定（manual 数量模式）。
  · 不改卖出策略：退出/止损仍由 strategies/sell_policy.py + stop-loss-watch.py 负责。
  · 持仓仅用于「持仓股不加仓」判定；账户不可读不得屏蔽合格信号。
规则真源: /Users/omi/workspace/quant-backtest/strategies/buy_policy.py（本脚本只做 v1.2 叠加层）

数据: 腾讯实时(量=手×100=股) + 腾讯日K(qfq) + 新浪5分钟K(量=股)
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

# 证据状态模块 (2026-09-24 新增) —— 取证失败必须可观测, 不得静默
import importlib.util as _ilu
_ES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "evidence_status.py")
_es_spec = _ilu.spec_from_file_location("evidence_status", _ES_PATH)
ES = _ilu.module_from_spec(_es_spec)
_es_spec.loader.exec_module(ES)

POLICY_VERSION = "BUY-LOW-v1.2-20260922"
POLICY_VERSION_BASE = BP.POLICY_VERSION                 # BUY-LOW-v1-20260915
POLICY_VERSION_SIZE = BP.POLICY_VERSION_MANUAL          # BUY-LOW-v1-manual-20260916
MANUAL_SIZE_NOTE = BP.MANUAL_SIZE_NOTE

# ---------------- v1.2 参数 ----------------
VOL_RATIO_MAX_V12 = 0.70        # ③ 严格小于 0.70（v1.1 为 0.80）
VOL_LOOKBACK_DAYS = BP.VOL_LOOKBACK_DAYS   # 5
RS_LOOKBACK = 20                # 相对强度窗口（完成交易日）
GAP_MAX_PCT = 0.015             # 开盘跳空门槛：开盘 <= 昨收 × 1.015
BENCH_CODE = "sh000300"         # 市场状态 / 相对强度基准
WEAK_DD_PCT = 0.08              # 弱市条件③ 距近60日最高收盘回撤 >= 8%
WEAK_HIGH_LOOKBACK = 60
STREAK_N = 3                    # 弱市判定/恢复均需连续 3 日
REGIME_CAPS = {
    "normal": {"total": 75, "single": 25, "label": "正常市"},
    "weak":   {"total": 60, "single": 20, "label": "弱市"},
}
# 扫描时段（与 BP.SESSIONS 一致，显式写出便于自检）
SESSIONS_V12 = [(945, 1130), (1300, 1445)]

LOCK_FILE = os.path.expanduser("~/.hermes/state/lowbuy-watch.lock")
LOCK_STALE_SEC = 120
LOG_FILE = os.path.expanduser("~/.hermes/state/lowbuy-watch.log")

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
    # ⭐ 2026-09-22 用户明确批准加入（第17只）—— 半导体材料（CMP抛光垫/半导体材料），一级缺口补充
    #    基本面最优：营收+11.15%/净利+70.21%/毛利率58.83%(持续升)/ROE9.76%/负债38.82%/无商誉
    #    ATR 3.83%(≤5%✅)；与现有科技簇相关性 +0.63（偏高，加它加重科技敞口，非分散）
    #    ⚠️ 单股上限例外：一手7,107元 = 净值52%，超常规40%阈值(5,461元)，经用户批准放宽
    "sz300054": "鼎龙股份",
}


# ==================== 日志 / 锁 ====================
def log_line(msg):
    """诊断日志：异常、行情缺失、基准不足、去重跳过等一律落盘。"""
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(f"[{datetime.datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass


class AtomicLock:
    """跨进程原子锁（O_EXCL），防两个扫描进程同时写状态导致重复推送。"""

    def __init__(self, path=LOCK_FILE, stale_sec=LOCK_STALE_SEC):
        self.path = path
        self.stale_sec = stale_sec
        self.fd = None

    def __enter__(self):
        for _ in range(2):
            try:
                self.fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(self.fd, str(os.getpid()).encode())
                return self
            except FileExistsError:
                try:
                    age = datetime.datetime.now().timestamp() - os.path.getmtime(self.path)
                except OSError:
                    age = 0
                if age > self.stale_sec:
                    log_line(f"LOCK_STALE 清理陈旧锁(age={age:.0f}s) path={self.path}")
                    try:
                        os.unlink(self.path)
                    except OSError:
                        pass
                    continue
                return None
            except Exception as e:  # noqa: BLE001
                log_line(f"LOCK_ERROR {e!r}")
                return None
        return None

    def __exit__(self, *exc):
        try:
            if self.fd is not None:
                os.close(self.fd)
        except Exception:
            pass
        try:
            os.unlink(self.path)
        except OSError:
            pass
        return False


# ==================== 时段 ====================
def in_window(now):
    """09:45–11:30 / 13:00–14:45 连续竞价时段；其余（09:00–09:44、11:35–12:59、14:50 后）不发信号。"""
    hhmm = now.hour * 100 + now.minute
    for lo, hi in SESSIONS_V12:
        if lo <= hhmm <= hi:
            return True
    return False


def calendar_gate():
    try:
        import cn_trading_calendar as cal
        st = cal.calendar_status(datetime.date.today())
        if st and not st.get("is_trading", False):
            return False
    except Exception:
        pass
    return True


# ==================== 数据 ====================
def _http(url, headers, timeout=15):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=headers), timeout=timeout).read()


def fetch_realtime(codes):
    """腾讯实时。f[3]=现价 f[4]=昨收 f[5]=今开 f[33]=最高 f[34]=最低 f[6]=量(手)"""
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
            out[code] = {
                "name": f[1], "price": float(f[3]), "prev": float(f[4]),
                "open": float(f[5]), "high": float(f[33]), "low": float(f[34]),
                "pct": float(f[32]), "vol": float(f[6]) * 100, "time": f[30],
            }
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


# ==================== v1.2 规则 ====================
def ret20_aligned(stock_rows, bench_rows, today):
    """个股近 20 个完成交易日收益 vs 沪深300 同期收益（按同一批日期对齐）。
    返回 (stock_ret, bench_ret, used_from, used_to) 或 (None,None,None,None)。"""
    s = [r for r in stock_rows if r["date"] < today]
    if len(s) < RS_LOOKBACK + 1:
        return (None, None, None, None)
    win = s[-(RS_LOOKBACK + 1):]                    # 21 个完成交易日 = 20 个收益区间
    bmap = {r["date"]: r["close"] for r in bench_rows if r["date"] < today}
    d0, d1 = win[0]["date"], win[-1]["date"]
    if d0 not in bmap or d1 not in bmap:
        return (None, None, None, None)             # 基准同日缺失 => 无法确认 => 不放行
    if win[0]["close"] <= 0 or bmap[d0] <= 0:
        return (None, None, None, None)
    return (win[-1]["close"] / win[0]["close"] - 1.0,
            bmap[d1] / bmap[d0] - 1.0, d0, d1)


def gap_ok(today_open, prev_close):
    """开盘跳空门槛：今开 <= 昨收 × 1.015。缺数据 => False(不放行)。

    注：浮点边界加 1e-9 容差。否则 100.00×1.015 = 101.49999999999999，
        恰好等于阈值的 101.50 会被判不通过（会把恰在门槛上的标的误跳过）。"""
    if not today_open or not prev_close or prev_close <= 0:
        return False
    return today_open <= prev_close * (1.0 + GAP_MAX_PCT) + 1e-9


def _sma_series(vals, k):
    out = [None] * len(vals)
    if k <= 0 or len(vals) < k:
        return out
    run = 0.0
    for i, v in enumerate(vals):
        run += v
        if i >= k:
            run -= vals[i - k]
        if i >= k - 1:
            out[i] = run / k
    return out


def compute_regime(bench_rows, today):
    """沪深300 市场状态：用**上一完整交易日及之前**的收盘计算，次日生效。
    返回 dict(regime, weak_streak, normal_streak, conditions, as_of, detail) 或 None(数据不足)。"""
    comp = [r for r in bench_rows if r["date"] < today]
    if len(comp) < WEAK_HIGH_LOOKBACK + 6:
        return None
    closes = [r["close"] for r in comp]
    ma20 = _sma_series(closes, 20)
    ma60 = _sma_series(closes, 60)
    weak_days, normal_days, conds = 0, 0, []
    for d in range(1, STREAK_N + 1):
        i = len(closes) - d
        if i - 5 < 0 or ma20[i] is None or ma60[i] is None:
            return None
        c = closes[i]
        c1 = c < ma60[i]
        c2 = ma20[i] <= ma20[i - 5]
        win = closes[max(0, i - WEAK_HIGH_LOOKBACK + 1): i + 1]
        peak = max(win)
        dd = (peak - c) / peak if peak > 0 else 0.0
        c3 = dd >= WEAK_DD_PCT
        n_true = sum([c1, c2, c3])
        conds.append({"date": comp[i]["date"], "close": round(c, 2),
                      "c1_close_lt_ma60": c1, "c2_ma20_down": c2,
                      "c3_drawdown": round(dd, 4), "n_true": n_true})
        if n_true >= 2:
            weak_days += 1
        if (not c1) and c > ma20[i] and ma20[i] > ma20[i - 5]:
            normal_days += 1
    if weak_days == STREAK_N:
        regime = "weak"
    elif normal_days == STREAK_N:
        regime = "normal"
    else:
        regime = None                       # 两侧都未达成 => 维持既有状态
    return {"regime": regime, "weak_streak": weak_days, "normal_streak": normal_days,
            "as_of": comp[-1]["date"], "conditions": conds}


def regime_effective(st, today, bench_rows):
    """市场状态：持久化 + 按 as_of 缓存；未达成新状态时沿用上一状态（默认 normal）。"""
    cached = st.get("market_regime") or {}
    comp = [r for r in bench_rows if r["date"] < today]
    as_of = comp[-1]["date"] if comp else None
    if cached.get("as_of") == as_of and cached.get("regime"):
        return cached
    info = compute_regime(bench_rows, today)
    if info is None:
        log_line(f"REGIME_UNAVAILABLE 沪深300数据不足或 MA 缺失，沿用上一状态 "
                 f"(prev={cached.get('regime')})")
        if cached.get("regime"):
            return cached
        info = {"regime": None, "weak_streak": 0, "normal_streak": 0,
                "as_of": as_of, "conditions": []}
    prev = cached.get("regime") or "normal"
    res = {
        "as_of": as_of,
        "regime": info["regime"] or prev,
        "decided": info["regime"],
        "weak_streak": info["weak_streak"],
        "normal_streak": info["normal_streak"],
        "conditions": info["conditions"],
        "effective_for": today,          # 次日生效：本次计算用于 today 的扫描（基于上一完整交易日）
    }
    st["market_regime"] = res
    log_line(f"REGIME 基准日={as_of} 判定={info['regime'] or '维持'} 生效={res['regime']} "
             f"弱市计数={info['weak_streak']}/3 恢复计数={info['normal_streak']}/3")
    return res


def vol_ratio_ok_v12(ratio, confirmed):
    """③ v1.2：严格 < 0.70 且数据可确认；未确认 => 不放行。"""
    if not confirmed or ratio is None:
        return False
    return ratio < VOL_RATIO_MAX_V12


def eval_one(code, name, q, today, now):
    """单股 v1.2 评估。返回 (cand|None, reason)。reason 用于日志(不发提醒的原因)。"""
    price = q["price"]
    # ⑥ 开盘跳空门槛（先判，省算力）
    if not gap_ok(q.get("open"), q.get("prev")):
        gap_pct = ((q["open"] / q["prev"] - 1) * 100) if q.get("prev") else float("nan")
        return (None, f"⑥跳空不满足: 今开{q.get('open')} vs 昨收{q.get('prev')} "
                      f"({gap_pct:+.2f}% > +1.50%)")
    day = fetch_day_kline(code)
    comp = [r for r in day if r["date"] != today]
    if len(comp) < BP.MA60_N + BP.MA60_LOOKBACK + 1:
        return (None, f"日K不足({len(comp)}根)")
    closes = [r["close"] for r in comp]
    highs = [r["high"] for r in comp]
    ms = BP.ma60_series(closes)
    ma60_now, ma60_5ago = ms[-1], ms[-1 - BP.MA60_LOOKBACK]
    # ② 趋势
    if not BP.trend_ok(price, ma60_now, ma60_5ago):
        return (None, f"①趋势不满足: 价{price} vs MA60 {ma60_now} / 5日前 {ma60_5ago}")
    atr = BP.atr14_wilder(comp)
    h20 = BP.h20(highs)
    band_ok, dev = BP.atr_band_ok(price, h20, atr, ma60_now)
    if not band_ok:
        return (None, f"②ATR回调不满足: 偏离={dev} (需 2.5~4.5)")
    # ③ 同刻缩量
    min5 = fetch_min5(code)
    ratio, detail, confirmed = BP.same_time_vol_ratio(min5, now)
    if not vol_ratio_ok_v12(ratio, confirmed):
        return (None, f"③同刻量比不满足/无法确认: ratio={ratio} confirmed={confirmed} [{detail}]")
    # ⑤ 相对强度
    bench_rows = _BENCH_CACHE.get("rows") or []
    s_ret, b_ret, d0, d1 = ret20_aligned(day, bench_rows, today)
    if s_ret is None:
        return (None, "⑤相对强度无法确认(基准同日缺失或样本不足)")
    if s_ret < b_ret:
        return (None, f"⑤相对强度不足: 个股{s_ret * 100:+.2f}% < 沪深300 {b_ret * 100:+.2f}%")
    lo, hi = BP.allowed_price_range(h20, atr, ma60_now)
    return ({"code": code, "name": name, "price": price, "ma60": ma60_now,
             "ma60_chg": BP.ma60_change_pct(ma60_now, ma60_5ago), "atr": atr,
             "h20": h20, "dev": dev, "vol_ratio": ratio, "vol_detail": detail,
             "stock_ret20": s_ret, "bench_ret20": b_ret, "rs20": s_ret - b_ret,
             "rs_span": f"{d0}~{d1}", "open": q.get("open"), "prev": q.get("prev"),
             "lo": lo, "hi": hi}, "")


_BENCH_CACHE = {}


def build_alert_text(c, rec, regime, now, others):
    cap = REGIME_CAPS.get(regime["regime"], REGIME_CAPS["normal"])
    lines = [
        f"【自选股低吸提醒 · {now.strftime('%H:%M')}】{POLICY_VERSION}",
        "",
        f"🟢 低吸条件满足 {c['name']}({c['code'][2:]})",
        f"  扫描时间 {now.strftime('%Y-%m-%d %H:%M')}｜现价 {c['price']:.2f}",
        "",
        f"  ①趋势: 价 {c['price']:.2f} > MA60 {c['ma60']:.2f}，"
        f"MA60 较 5 日前 {c['ma60_chg']:+.2f}% ✓",
        f"  ②ATR回调: (H20 {c['h20']:.2f} − 价 {c['price']:.2f}) / ATR14 {c['atr']:.2f}"
        f" = {c['dev']:.2f}  (需 2.5~4.5) ✓",
        f"  ③同刻缩量: 量比 {c['vol_ratio']:.2f}  (需 < 0.70) ✓  [{c['vol_detail']}]",
        f"  ⑤相对强度: 个股20日 {c['stock_ret20'] * 100:+.2f}% ≥ "
        f"沪深300 {c['bench_ret20'] * 100:+.2f}%  → 超额 {c['rs20'] * 100:+.2f}% ✓ "
        f"({c['rs_span']})",
        f"  ⑥跳空门槛: 今开 {c['open']:.2f} ≤ 昨收 {c['prev']:.2f} × 1.015 ✓",
        "",
        f"  市场状态: {cap['label']}（沪深300，基准日 {regime['as_of']}，次日生效）",
        f"    · 新增总仓位上限 {cap['total']}%｜单只目标 {cap['single']}%",
        f"    · 弱市计数 {regime['weak_streak']}/3｜恢复计数 {regime['normal_streak']}/3",
        "",
        f"  允许价格区间: {c['lo']:.2f} ~ {c['hi']:.2f}",
        f"  参考限价: {c['price']:.2f}",
        f"  止损参考 -6% = {c['price'] * (1 - BP.HARD_STOP_PCT):.2f}"
        f"（持仓后按 SELL-POLICY 执行）",
        f"  ⏳ 有效期至 {rec['expires']}（15 分钟；超时需重新核验价格与全部条件）",
        "",
        f"  {MANUAL_SIZE_NOTE}",
        "",
        "⚠️ 仅为策略提醒，不自动下单；数量与下单由用户自主，若下单请在券商端限价委托。",
    ]
    if others:
        lines += ["", "本次未获选候选（仅记录，不单独提醒）: " +
                  "、".join(f"{x['name']}({x['rs20'] * 100:+.2f}%)" for x in others)]
    return "\n".join(lines)


# ==================== 主流程 ====================
def main():
    now = datetime.datetime.now()
    if now.weekday() > 4:
        return
    if not in_window(now):
        return                                   # 时段外静默（09:00–09:44 / 11:35–12:59 / 14:50 后）
    if not calendar_gate():
        return

    lock = AtomicLock()
    with lock as held:
        if held is None:
            log_line("SKIP 未取得原子锁（另一扫描进程在运行），本轮不处理以防重复推送")
            return

        today = now.strftime("%Y-%m-%d")
        st = BP.load_state()
        BP.roll_day(st, today)
        BP.mark_needs_recheck(st, now)
        if BP.pending_active(st):
            BP.save_state(st)
            return

        # 持仓（仅用于不加仓判定）
        try:
            acc = BP.load_account()
            holdings = acc.get("holdings") or {}
        except Exception as e:  # noqa: BLE001
            log_line(f"ACCOUNT_UNREADABLE {e!r}（不屏蔽合格信号，仅跳过持仓判定）")
            holdings = {}

        # ── 证据取证 (2026-09-24): 取数失败不得静默 ──────────────────────
        # 原文缺陷: 失败只写日志不推送 → 用户以为"今天没信号",
        #   实际可能是"整批取数失败、监控根本跑了个空转"。
        ev_run = ES.Run(script="lowbuy-watch", now=now,
                        expected_total=len(WATCHLIST) + 1)   # +1 = 沪深300基准
        _ev_finished = {"v": False}

        def _ev_finish():
            """统一收尾: 落盘 + 必要时输出告警 (cron 的 stdout = 推送内容)。"""
            if _ev_finished["v"]:
                return
            _ev_finished["v"] = True
            _need, _txt, _r = ev_run.finish(critical=False)
            if _need and _txt:
                print(_txt)
            if ev_run.degraded:
                log_line(ES.summary_for_log(ev_run))

        try:
            bench_rows = fetch_day_kline(BENCH_CODE)
            _BENCH_CACHE["rows"] = bench_rows
        except Exception as e:  # noqa: BLE001
            log_line(f"BENCH_FETCH_FAIL {e!r} => 本轮不产生买入提醒")
            ev_run.fail_batch(f"基准{BENCH_CODE}取数失败 {type(e).__name__}: {e}")
            BP.save_state(st)
            _ev_finish()
            return
        if not bench_rows:
            log_line("BENCH_EMPTY 沪深300 日K 为空 => 本轮不产生买入提醒")
            ev_run.fail_batch(f"基准{BENCH_CODE}日K为空")
            BP.save_state(st)
            _ev_finish()
            return

        regime = regime_effective(st, today, bench_rows)

        try:
            rt = fetch_realtime(list(WATCHLIST.keys()))
        except Exception as e:  # noqa: BLE001
            log_line(f"QUOTE_FETCH_FAIL {e!r} => 本轮不产生买入提醒")
            ev_run.fail_batch(f"实时行情取数失败 {type(e).__name__}: {e}")
            BP.save_state(st)
            _ev_finish()
            return
        if not rt:
            log_line("QUOTE_EMPTY 实时行情为空 => 本轮不产生买入提醒")
            ev_run.fail_batch("实时行情返回空")
            BP.save_state(st)
            _ev_finish()
            return

        cands, skipped = [], []
        for code, name in WATCHLIST.items():
            if code in holdings:
                skipped.append((name, "已持仓（不加仓）"))
                continue
            q = rt.get(code)
            if not q:
                skipped.append((name, "行情缺失/价格无效"))
                ev_run.add(code, name, ES.MISSING, "腾讯实时行情未返回该代码")
                continue
            if q["price"] <= 0:
                skipped.append((name, "行情缺失/价格无效"))
                ev_run.add(code, name, ES.INVALID_PRICE, f"price={q['price']}")
                continue
            ev_run.add(code, name, ES.AVAILABLE)
            if BP.is_blocked_after_exit(st, today, code):
                skipped.append((name, "清仓后防买回期(§6 未登记失效)"))
                continue
            try:
                c, why = eval_one(code, name, q, today, now)
            except Exception as e:  # noqa: BLE001
                skipped.append((name, f"评估异常 {type(e).__name__}"))
                log_line(f"EVAL_ERROR {code} {name} {e!r}")
                continue
            if c:
                cands.append(c)
            else:
                skipped.append((name, why))

        if not cands:
            log_line(f"NO_CANDIDATE 扫描 {len(WATCHLIST)} 只；市场状态={regime['regime']}；"
                     f"跳过原因=" + " | ".join(f"{n}:{w}" for n, w in skipped))
            BP.save_state(st)
            _ev_finish()
            return

        # ⑧ 多候选按 20 日相对强度降序，只取第 1 名
        cands.sort(key=lambda x: (-x["rs20"], x["code"]))
        chosen, others = cands[0], cands[1:]

        can, why = BP.can_recommend(st, today, chosen["code"])
        if not can:
            log_line(f"SUPPRESS {chosen['name']} 不推送原因: {why}")
            BP.save_state(st)
            _ev_finish()
            return

        rec = BP.issue_alert(st, today, chosen["code"], chosen["price"],
                             chosen["lo"], chosen["hi"], now=now,
                             detail={"vol_ratio": chosen["vol_ratio"],
                                     "rs20": chosen["rs20"],
                                     "regime": regime["regime"]})
        BP.save_state(st)
        if not rec:
            log_line("SUPPRESS issue_alert 返回空（已有待确认建议）")
            _ev_finish()
            return

        log_line(f"ALERT_ISSUED {chosen['name']} {chosen['code']} 价={chosen['price']} "
                 f"量比={chosen['vol_ratio']:.2f} rs20={chosen['rs20'] * 100:+.2f}% "
                 f"市场={regime['regime']} 到期={rec['expires']}")
        print(build_alert_text(chosen, rec, regime, now, others))
        # 证据告警若存在, 追加在提醒之后（同一笔推送里告知"部分标的未取到数"）
        _ev_finish()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log_line(f"FATAL {e!r}")
        # ⚠️ 顶层异常同样属于"取证/执行失败", 记一次, 否则连续失败计数不推进
        try:
            _r = ES.Run(script="lowbuy-watch")
            _r.fail_batch(f"FATAL {type(e).__name__}: {e}")
            _n, _tx, _ = _r.finish(critical=False)
            if _n and _tx:
                print(_tx)
        except Exception:
            pass
        try:
            import traceback
            log_line(traceback.format_exc().replace("\n", " | "))
        except Exception:
            pass
        # 异常时不发买入提醒（stdout 为空）
