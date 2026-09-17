#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
止损监控 (sell-policy 统一退出监控) — v3 (2026-09-14)
=====================================================
no_agent cron script (cron 解析路径 = ~/.hermes/profiles/main/scripts/)。

本脚本不再自持卖出参数, 全部委托给唯一权威模块:
    strategies/sell_policy.py  (SELL-POLICY-v1.0-20260914)

规则 (模块内实现, 此处不复制):
  R1 初始硬止损 = 成本×0.94
  R3 H≥成本×1.08 永久开启盈利保护
  R4 保护线 P = max(旧P, 成本×1.03, H×0.93), 只升不降
  R5 MA60 仅趋势提示, 不独立触发
  R7 有效退出线 = 所有已启用线的最高值; 触发即持久化退出事件(去重)
  R7 T+1 不可卖部分登记待退出, 次日继续提醒
  R8 未确认卖出持仓不变; 重复扫描不重复发

行为:
- 交易时段(09:30-15:00)每分钟检查; 非交易时段/周末/节假日静默。
- 有效退出线触发 → 输出提醒(微信), 同事件去重。
- 无事件 → 空 stdout → 静默。
- 绝不自动下单; 提醒仅为条件提示。

状态: ~/.hermes/state/sell-policy-state.json (原子写+文件锁, 与其它入口共享)
事件: 追加 ~/.hermes/state/trading-execution-events.jsonl (不含凭据)
"""
from __future__ import annotations

import datetime
import importlib.util
import json
import os
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(path: str, name: str):
    import sys as _sys
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    _sys.modules[name] = m  # 必须先注册, 否则 dataclass(frozen) + future annotations 解析失败
    spec.loader.exec_module(m)
    return m


# 统一卖出策略模块 (唯一权威)
_SELL_POLICY_PATH = os.environ.get(
    "SELL_POLICY_PATH",
    "/Users/omi/workspace/quant-backtest/strategies/sell_policy.py",
)
sellp = _load(_SELL_POLICY_PATH, "sell_policy")

# 事件日志 (复用既有 guard 的 append 语义, 但不依赖 guard 的过期 HOLDINGS)
EVENTS_FILE = os.path.expanduser("~/.hermes/state/trading-execution-events.jsonl")

# 交易窗口 09:30-15:00
TRADING_WINDOW = (930, 1500)

# 报价新鲜度阈值(秒): 腾讯报价时间戳与会话时间差超过此值 → 视为陈旧
QUOTE_STALE_SECONDS = 180

# ── 日内低点提示 (2026-09-16 新增, 用户指令) ────────────────────────────
# 目的: 条件单口径下"盘中触及止损即成交", 而 evaluate_exit 只用【现价】判定
#       → 会出现"实盘应已成交、系统却不提醒"的盲区(2026-09-16 赤峰 43.10 触及 43.26)。
# 原则: 【只提示, 不改判定】——
#   · 不调用 fire_exit, 不写入 pending_exit, 不产生 SELL_EXIT 事件
#   · 不修改 R1/R3/R4 任何语义; 现价触发仍走原有路径
#   · 每只每交易日最多提示一次(独立去重文件, 不污染 sell-policy-state.json)
TOUCH_STATE_FILE = os.path.expanduser("~/.hermes/state/intraday-touch-alert.json")
TOUCH_ALERT_ENABLED = True

# ============================================================================
# 退出线【上移】提醒 (2026-09-16 新增)
#   目的: 保护线会随持仓最高价 H 抬升 (P = max(旧P, C*1.03, H*0.93))。
#         系统知道新线, 但用户的券商【条件单】是静态的 → 不同步就会过早卖出。
#   行为: 当有效退出线【上移】且幅度 >= 阈值时, 主动推送一次, 提示用户更新条件单。
#   只提示, 不改判定、不触发卖出 (与 INTRADAY_TOUCH 同语义)。
# ============================================================================
LINE_NOTIFY_ENABLED = True
LINE_NOTIFY_STATE_FILE = os.path.expanduser("~/.hermes/state/exit-line-notify.json")
LINE_NOTIFY_MIN_PCT = 0.005   # 线变化 >= 0.5% 才推送(避免每一分钱都打扰)


def _load_line_notify() -> dict:
    if os.path.exists(LINE_NOTIFY_STATE_FILE):
        try:
            with open(LINE_NOTIFY_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_line_notify(d: dict) -> None:
    try:
        os.makedirs(os.path.dirname(LINE_NOTIFY_STATE_FILE), exist_ok=True)
        tmp = LINE_NOTIFY_STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, LINE_NOTIFY_STATE_FILE)
    except Exception:
        pass


# ============================================================================
# 反弹减仓参考位提醒 (2026-09-17 新增，Omi 批准)
#   用途: 三只各1手→减仓=清仓。价位来自日K阻力(MA20/近10日高/前高/保护激活线)。
#   行为: 现价 >= 某档目标位时推送一次(每档每只一次)，标注"主动减仓参考·非规则触发"。
#   只提示，不判定、不调 fire_exit、不写 sell-policy-state.json。
# ============================================================================
REDUCE_ALERT_ENABLED = True
REDUCE_TARGETS_FILE = os.path.expanduser("~/.hermes/state/reduce-targets.json")
REDUCE_ALERT_STATE_FILE = os.path.expanduser("~/.hermes/state/reduce-target-alert.json")


def _load_json(path: str, default: dict) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _save_json(path: str, d: dict) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, path)
    except Exception:
        pass


def build_reduce_alert(st, tier: dict, price: float, cost: float) -> str:
    gain = (price / cost - 1) * 100 if cost else 0.0
    return (
        f"🎯 反弹减仓参考位触及（主动减仓·非规则触发）\n"
        f"{st.name} {st.code}\n"
        f"  现价　　：{price:.2f}\n"
        f"  触及档位：第{tier['level']}档 {tier['price']:.2f}（{tier['label']}）\n"
        f"  风控成本：{cost:.3f}　→　浮盈 {gain:+.2f}%\n"
        f"  当前退出线：{st.effective_exit_line():.2f}（SELL-POLICY 规则线，未变）\n"
        f"  ⚠️ 1手=清仓，卖出将登记为 R8 主动减仓\n"
        f"  → 供决策参考，不是策略触发的卖出信号"
    )


def build_line_update_alert(st, old_eff: float, new_eff: float, price: float,
                            reason: str) -> str:
    d = new_eff - old_eff
    pct = (d / old_eff * 100) if old_eff else 0.0
    return (
        f"📈 退出线上移（请同步券商条件单）\n"
        f"{st.name} {st.code}\n"
        f"  旧退出线：{old_eff:.2f}\n"
        f"  新退出线：{new_eff:.2f}   ({d:+.2f}, {pct:+.2f}%)\n"
        f"  当前价　：{price:.2f}\n"
        f"  原因　　：{reason}\n"
        f"  → 建议把条件单从 {old_eff:.2f} 改为 {new_eff:.2f}"
    )


def load_touch_state() -> dict:
    try:
        with open(TOUCH_STATE_FILE, encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def save_touch_state(d: dict) -> None:
    try:
        os.makedirs(os.path.dirname(TOUCH_STATE_FILE), exist_ok=True)
        tmp = TOUCH_STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, TOUCH_STATE_FILE)
    except Exception:
        pass


def build_touch_alert(st, eff: float, low: float, price: float, now) -> str:
    gap = eff - low
    back = price - eff
    return (
        f"🟠 日内触及提示（非触发）\n"
        f"  {st.name}  {st.total_qty}股  成本 {st.cost}\n"
        f"  有效退出线 {eff:.2f}  |  日内最低 {low:.2f}（盘中曾低于线 {gap:.2f} 元）\n"
        f"  现价 {price:.2f}（已收回线上 {back:+.2f}）\n"
        f"  ⚠️ 按现价口径【未触发】；若你挂了条件单，盘中可能已成交。\n"
        f"     请核对券商成交记录；本提示只报事实，不判定成交。\n"
        f"  时间 {now.strftime('%H:%M')}  |  {sellp.STRATEGY_VERSION}"
    )


def now_hhmm(dt=None):
    dt = dt or datetime.datetime.now()
    return dt.hour * 100 + dt.minute


def in_window():
    hh = now_hhmm()
    return TRADING_WINDOW[0] <= hh <= TRADING_WINDOW[1]


def append_event(evt: dict) -> None:
    try:
        os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
        rec = {"ts": sellp.now_iso(), **evt}
        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass


def fetch_quotes(codes):
    """批量取腾讯实时报价。返回 {code: {price, pct, high, low, ytime, ok}}。"""
    if not codes:
        return {}
    url = "http://qt.gtimg.cn/q=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"Referer": "http://finance.qq.com"})
    data = urllib.request.urlopen(req, timeout=10).read().decode("gbk", "ignore")
    out = {}
    for line in data.strip().split(";"):
        line = line.strip()
        if not line or "=" not in line or '="' not in line:
            continue
        code = line.split("=")[0].replace("v_", "")
        f = line.split('="')[1].rstrip('"').split("~")
        if len(f) < 35:
            continue
        try:
            out[code] = {
                "price": float(f[3]),
                "prev": float(f[4]),
                "pct": float(f[32]),
                "high": float(f[33]),
                "low": float(f[34]),
                "ytime": f[30],  # 形如 20260914145954
            }
        except (ValueError, IndexError):
            continue
    return out


def _quote_fresh(ytime: str, now: datetime.datetime) -> bool:
    """校验报价时间戳新鲜度。ytime=YYYYMMDDHHMMSS。"""
    try:
        dt = datetime.datetime.strptime(ytime.strip(), "%Y%m%d%H%M%S")
    except Exception:
        return False
    return abs((now - dt).total_seconds()) <= QUOTE_STALE_SECONDS


def main():
    now = datetime.datetime.now()
    if now.weekday() >= 5:
        return
    if not in_window():
        return

    store = sellp.StateStore()
    # R7 日切 (2026-09-15 补): 每交易日首次运行把"当日新增"解禁为可卖。
    # 此前 roll_trading_day() 在生产入口无人调用 → T+1 解禁失效。
    try:
        rolled = sellp.roll_new_trading_day(store)
        if rolled:
            append_event({"event": "T1_ROLL", "detail": [
                {"code": c, "name": n, "qty": q} for c, n, q in rolled]})
    except Exception:
        pass
    positions = store.all()
    if not positions:
        return  # 无持仓 → 静默

    codes = list(positions.keys())
    try:
        quotes = fetch_quotes(codes)
    except Exception:
        return  # 抓取失败静默(不误报, 不丢状态)

    alerts = []
    touch_alerts = []
    line_alerts = []
    linea_dirty = False
    line_notify = _load_line_notify() if LINE_NOTIFY_ENABLED else {}
    reduce_alerts = []
    reduce_dirty = False
    reduce_targets = _load_json(REDUCE_TARGETS_FILE, {}) if REDUCE_ALERT_ENABLED else {}
    reduce_fired = _load_json(REDUCE_ALERT_STATE_FILE, {"_fired": {}}).get("_fired", {})
    touch_state = load_touch_state()
    today = now.strftime("%Y-%m-%d")
    if touch_state.get("_date") != today:
        touch_state = {"_date": today}
    touched = touch_state.setdefault("touched", {})

    for code, st in positions.items():
        if st.total_qty <= 0:
            continue
        q = quotes.get(code)
        if not q:
            continue
        fresh = _quote_fresh(q["ytime"], now)
        # 用有效报价更新状态(含 H); 无效报价不更新、不关保护(R7)
        if fresh:
            sellp.update_quote(st, q["price"], quote_time=q["ytime"],
                               intraday_high=q["high"])
        else:
            sellp.update_quote(st, q["price"], quote_time=q["ytime"],
                               is_valid=False, invalid_reason="报价陈旧(超阈值)")

        ev = sellp.evaluate_exit(st, q["price"], quote_time=q["ytime"])
        if ev:
            if sellp.fire_exit(st, ev):  # 去重: 仅新事件才提醒
                alerts.append(sellp.build_exit_alert(st, ev))
                append_event({
                    "event": "SELL_EXIT", "code": code, "name": st.name,
                    "reason": ev["reason"], "line": ev["line"], "price": ev["price"],
                    "event_id": ev["event_id"], "strategy": sellp.STRATEGY_VERSION,
                })
        # 待退出事件的"续报"(次一交易日可卖时)由日/盘中入口汇总, 此处不重复轰炸(R7/R8)

        eff = st.effective_exit_line()   # 当前有效退出线(硬止损 与 保护线 取高)

        # ── 退出线【上移】提醒: 保护线随 H 抬升时, 提示用户同步券商条件单 ──
        if LINE_NOTIFY_ENABLED:
            _rec = line_notify.get(code) or {}
            _old = _rec.get("line")
            _new = eff
            if _old is None:
                # 首次登记基线, 不推送
                line_notify[code] = {"line": _new, "name": st.name,
                                     "first_seen": now.strftime("%Y-%m-%d %H:%M")}
                linea_dirty = True
            elif _new > _old + 1e-9 and (_new - _old) / _old >= LINE_NOTIFY_MIN_PCT:
                _p = sellp.DEFAULT_PARAMS
                _floor = round(st.cost * (1 + _p.profit_floor_pct), 2)
                _trail = round(st.peak_h * (1 - _p.trail_from_peak_pct), 2)
                if _new >= _floor - 1e-9 and _floor >= _trail:
                    _why = ("盈利保护·最低锁利兜底 (成本×%.2f = %.2f)"
                            % (1 + _p.profit_floor_pct, _floor))
                elif st.protection_active:
                    _why = ("盈利保护·随最高价 H 抬升 (H %.2f×%.2f = %.2f)"
                            % (st.peak_h, 1 - _p.trail_from_peak_pct, _trail))
                elif _new > st.hard_stop + 1e-9:
                    _why = "盈利保护线更新"
                else:
                    _why = "硬止损上移"
                line_alerts.append(
                    build_line_update_alert(st, _old, _new, q["price"], _why))
                append_event({"event": "EXIT_LINE_UPDATE", "code": code,
                              "name": st.name, "old_line": _old, "new_line": _new,
                              "price": q["price"]})
                line_notify[code] = {"line": _new, "name": st.name,
                                     "notified_at": now.strftime("%Y-%m-%d %H:%M")}
                linea_dirty = True

        # ── 反弹减仓参考位（主动减仓 R8 参考·非规则触发）──
        if REDUCE_ALERT_ENABLED and fresh:
            _tgt = (reduce_targets.get("positions") or {}).get(code)
            if _tgt and reduce_targets.get("enabled", True):
                _rcost = _tgt.get("cost") or st.risk_cost()
                for _tier in sorted(_tgt.get("tiers") or [], key=lambda x: x.get("level", 99)):
                    _key = f"{code}:{_tier['level']}"
                    if q["price"] >= float(_tier["price"]) and _key not in reduce_fired:
                        reduce_alerts.append(build_reduce_alert(st, _tier, q["price"], _rcost))
                        reduce_fired[_key] = {
                            "at": now.strftime("%Y-%m-%d %H:%M"),
                            "price": q["price"], "level": _tier["level"],
                            "target": _tier["price"],
                        }
                        reduce_dirty = True

        # ── 日内低点提示 (只提示, 不判定, 每只每交易日一次) ──
        if TOUCH_ALERT_ENABLED and fresh and not ev and not touched.get(code):
            low = q.get("low")
            if low is not None and low <= eff and q["price"] > eff:
                touched[code] = {"at": now.strftime("%H:%M"), "low": low,
                                 "line": eff, "price": q["price"]}
                touch_alerts.append(build_touch_alert(st, eff, low, q["price"], now))
                append_event({"event": "INTRADAY_TOUCH", "code": code, "name": st.name,
                              "line": eff, "low": low, "price": q["price"],
                              "note": "仅提示, 未判定触发", "strategy": sellp.STRATEGY_VERSION})

        store.put(st)  # 原子持久化(含 H / 保护线 / 待退出)

    if line_alerts:
        if alerts or touch_alerts:
            print()
        print("⚠️ 退出线更新 (sell-policy)")
        print("=" * 22)
        print("\n\n".join(line_alerts))
    if linea_dirty:
        _save_line_notify(line_notify)
    if reduce_alerts:
        if alerts or touch_alerts or line_alerts:
            print()
        print("🎯 反弹减仓参考位 (主动减仓·非规则触发)")
        print("=" * 22)
        print("\n\n".join(reduce_alerts))
    if reduce_dirty:
        _save_json(REDUCE_ALERT_STATE_FILE, {"_fired": reduce_fired,
                                             "_updated": now.strftime("%Y-%m-%d %H:%M")})
    if touch_alerts:
        save_touch_state(touch_state)

    if alerts:
        print("⚠️ 退出监控 (sell-policy)")
        print("=" * 22)
        print("\n\n".join(alerts))
    if touch_alerts:
        if alerts:
            print()
        print("=" * 22)
        print("\n\n".join(touch_alerts))
    # 无事件 → 空 stdout → 静默


if __name__ == "__main__":
    main()
