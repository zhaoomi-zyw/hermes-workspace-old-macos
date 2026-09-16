#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trading_execution_guard.py — A股执行风控库 (只做判定/提醒, 绝不下单)
=====================================================================
共享给 buy-signal-watch / ziguang-lowbuy-watch / lowbuy-watch / signal_daily。

⚠️ 2026-09-15 对齐 BUY-LOW-v1-20260915（用户指令）：
- 参数与口径**唯一来源** `strategies/buy_policy.py`，本文件不再硬编码资金/持仓/时段/限额。
- 时段：**09:45-11:30 与 13:00-14:45**（原 09:40-14:20 已废弃）
- 净资产：净资产 = 现金 + 持仓当前市值（原口径是把现金当作可投资金，已修正）
- 风险限额：单笔≤净资产2% / 组合≤净资产4% / 单股≤净资产35%
- 现金/持仓：现金 ← ~/.hermes/state/account.json
             持仓 ← ~/.hermes/state/sell-policy-state.json（含 hard_stop 真值）
- **资金/预算不足不再硬阻断**（与 buy_policy.sizing 一致）：改为 warnings + sizing 明细。
  仅保留硬阻断：非交易日 / 时段外 / 价格与止损位非法。
  需要旧式"直接拦下"的调用方请传 strict=True。

提供:
- evaluate_buy(...)   -> 买入判定(时段/净资产/风险分档/T+1)，返回结构化 dict
- hard_stop_check(...) 硬止损（读 sell-policy 真值）
- get_authoritative_state() 权威现金/持仓快照
- 事件日志 ~/.hermes/state/trading-execution-events.jsonl（不含凭据）

⚠️ 2026-09-15: 原 MIN_RR=1.5 盈亏比门槛**已删除**。BUY-LOW-v1 无 RR 要求，
   止损由 SELL-POLICY 给出、盈利侧为保护线(无固定目标价)，RR 在新体系无自然定义。
   现 rr 仅作信息性数字（调用方传了 stop/target 时照算），**永不作为否决条件**。
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import urllib.request
from typing import Optional

# ---------- 唯一权威模块 ----------
_QP = "/Users/omi/workspace/quant-backtest/strategies"
if _QP not in sys.path:
    sys.path.insert(0, _QP)
import buy_policy as BP  # noqa: E402

LOT = 100
HS300_CODE = "sh000300"
DEFENSE_POOL = 350000.0          # 35万防守池, 独立管理, 明确排除于单股仓位计算
# ⚠️ 2026-09-15: MIN_RR(盈亏比≥1.5)门槛已删除。
# 理由: BUY-LOW-v1-20260915 只定义入场三条件, 止损由 SELL-POLICY 给出(成本×0.94),
# 盈利侧是保护线(H≥成本×1.08 后移动止盈), **不存在固定"目标价"**, RR 在新体系无自然定义,
# 不得作为门槛否决。现 rr 仅作信息性数字(调用方传了 stop/target 时照算)。

# 总仓位纪律(组合层, 非 BUY-LOW 定义)
NORMAL_TOTAL_CAP = 0.75
WEAK_TOTAL_CAP = 0.60

EVENTS_FILE = os.path.expanduser("~/.hermes/state/trading-execution-events.jsonl")


# ---------- 基础 ----------
def now_hhmm(dt: Optional[datetime.datetime] = None) -> int:
    return BP.now_hhmm(dt)


def _ts() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def append_event(evt: dict) -> None:
    try:
        os.makedirs(os.path.dirname(EVENTS_FILE), exist_ok=True)
        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _ts(), **evt}, ensure_ascii=False) + "\n")
    except Exception:
        pass


# ---------- 账户(唯一来源) ----------
def load_holdings() -> dict:
    """{code: (name, qty, cost)} —— 来自 sell-policy-state.json (BP.load_account)。"""
    return BP.load_account()["holdings"]


def load_cash() -> float:
    return float(BP.load_account()["cash"])


def _hard_stop_of(code: str, cost: float) -> float:
    """优先读 sell-policy-state.json 的 hard_stop 真值, 否则按成本×(1-6%)。"""
    try:
        with open(BP.SELL_STATE_FILE) as f:
            sp = json.load(f)
        p = (sp.get("positions") or {}).get(code)
        if p and p.get("hard_stop"):
            return float(p["hard_stop"])
    except Exception:
        pass
    return round(cost * (1 - BP.HARD_STOP_PCT), 2)


def _live_prices(codes) -> dict:
    """腾讯实时价; 失败返回 {}（调用方回退成本价）。"""
    if not codes:
        return {}
    try:
        url = "http://qt.gtimg.cn/q=" + ",".join(codes)
        req = urllib.request.Request(url, headers={"Referer": "http://finance.qq.com"})
        data = urllib.request.urlopen(req, timeout=8).read().decode("gbk")
        out = {}
        for line in data.strip().split(";"):
            if "=" not in line or '="' not in line:
                continue
            payload = line.split('="')[1].rstrip('"').split("~")
            if len(payload) > 33:
                out[line.split("=")[0].strip().replace("v_", "")] = float(payload[3])
        return out
    except Exception:
        return {}


def net_assets(prices: Optional[dict] = None) -> float:
    """净资产 = 现金 + 持仓市值(取实时价, 缺失回退成本)。"""
    acc = BP.load_account()
    prices = prices if prices is not None else _live_prices(list(acc["holdings"].keys()))
    return BP.net_assets(acc["cash"], acc["holdings"], prices)


# ---------- 市况 ----------
def fetch_hs300_pct() -> Optional[float]:
    import urllib.request as _u
    try:
        req = _u.Request("http://qt.gtimg.cn/q=" + HS300_CODE,
                         headers={"Referer": "http://finance.qq.com"})
        data = _u.urlopen(req, timeout=8).read().decode("gbk")
        for line in data.strip().split(";"):
            if "=" not in line or '="' not in line:
                continue
            payload = line.split('="')[1].rstrip('"').split("~")
            if len(payload) > 33:
                return float(payload[32])
    except Exception:
        return None
    return None


def market_weak(hs300_pct: Optional[float]) -> bool:
    return hs300_pct is not None and hs300_pct <= -1.0


def position_limits(hs300_pct: Optional[float]):
    """(total_cap, single_cap)。单股上限统一取 BP.POS_SINGLE_PCT(35% 净资产)。"""
    return (WEAK_TOTAL_CAP if market_weak(hs300_pct) else NORMAL_TOTAL_CAP,
            BP.POS_SINGLE_PCT)


def _rr_info(entry: float, stop: float, target: float) -> tuple:
    """盈亏比**信息性**计算(2026-09-15: 阈值已移除, 永不否决)。
    返回 (rr or None, 说明)。levels 不合法时 rr=None。"""
    if stop >= entry or target <= entry:
        return (None, f"无法计算(entry{entry:.2f} stop{stop:.2f} target{target:.2f} 不合法)")
    return ((target - entry) / (entry - stop), "")


# ---------- 主判定 ----------
def evaluate_buy(
    price: float,
    stop: float,
    target: float,
    *,
    context: str = "intraday_entry",
    now_dt: Optional[datetime.datetime] = None,
    hs300_pct: Optional[float] = None,
    shares: int = LOT,
    strict: bool = False,
) -> dict:
    """
    综合买入判定。返回 allowed / reasons / warnings / sizing /
    net_assets / rr / overnight_stress_loss / t_plus_one / ...

    context:
      - "intraday_entry"(默认): 盘中实时, 严格 09:45-11:30 / 13:00-14:45 时段。
      - "daily_plan": 收盘后生成次日候选, 不套当前钟点, 仅提示次日时段。

    strict=False(默认): 资金/预算/组合风险不足 → 记录到 warnings 与 sizing, 不阻断。
    strict=True: 上述不足按旧行为直接 BLOCKED。
    本函数绝不下单。
    """
    dt = now_dt or datetime.datetime.now()
    hh = now_hhmm(dt)
    reasons, warnings = [], []
    blocked = None
    allowed = True

    # 1) 交易日
    if dt.weekday() >= 5:
        if context == "daily_plan":
            reasons.append("周末生成次日(下一交易日)计划")
        else:
            blocked = {"allowed": False, "code": "WEEKEND", "reason": "非交易日(周末)"}

    # 2) 时段 (BP.SESSIONS: 09:45-11:30 / 13:00-14:45)
    if blocked is None:
        sess_txt = "、".join(f"{a//100:02d}:{a%100:02d}-{b//100:02d}:{b%100:02d}" for a, b in BP.SESSIONS)
        if context == "daily_plan":
            reasons.append(f"次日仅 {sess_txt} 经盘中确认后可执行")
        elif not BP.in_session(hh):
            blocked = {"allowed": False, "code": "TIME_GATE",
                       "reason": f"非买入时段({hh//100:02d}:{hh%100:02d}, 允许 {sess_txt})"}
        else:
            reasons.append(f"时段内({hh//100:02d}:{hh%100:02d}) ✓ {sess_txt}")

    # 3) 市况
    if hs300_pct is None:
        hs300_pct = fetch_hs300_pct()
    weak = market_weak(hs300_pct)
    reasons.append(f"沪深300 {hs300_pct:+.2f}% → {'弱市' if weak else '正常市'}"
                   if hs300_pct is not None
                   else "沪深300数据缺失, 按正常仓位上限评估(需人工复核市况)")

    # 4) 数量 / 资金 / 风险分档
    #    2026-09-16 手动数量模式: 取消一切自动数量计算与资金/风险门槛。
    #    仅当 SIZING_MODE="auto"(历史/兼容) 时才计算分档并可能阻断。
    MANUAL = BP.is_manual_mode()
    holdings = load_holdings()
    cash = load_cash()
    prices = _live_prices(list(holdings.keys()))
    net = BP.net_assets(cash, holdings, prices)
    tc, sc = position_limits(hs300_pct)
    if MANUAL:
        sz = None
        one_lot_cost = None
        port_risk = None
        reasons.append("数量: 由用户自行决定（本判定不计算股数、不设资金/风险门槛；"
                       "现金/净资产未知也不影响信号有效性）")
    else:
        sz = BP.sizing(price, net, cash)
        one_lot_cost = price * LOT * (1 + BP.FEE_BUY)
        if not sz["buyable"]:
            warnings.append("资金/预算不足: " + "、".join(sz["blockers"]))
            if sz["cash_shortfall"] > 0:
                warnings.append(f"现金缺口 ¥{sz['cash_shortfall']:.2f} 才能买一手")
            if strict:
                blocked = {"allowed": False, "code": "BUDGET_BLOCKED",
                           "reason": " | ".join(warnings)}
        # 5) 组合计划风险 4%
        port_risk = BP.portfolio_risk(holdings, prices)
        if not BP.portfolio_risk_ok(port_risk, net):
            msg = f"组合计划风险{port_risk:.0f}元 > 上限{net*BP.RISK_PORT_PCT:.0f}元(净资产4%)"
            warnings.append(msg)
            if strict and blocked is None:
                blocked = {"allowed": False, "code": "PORTFOLIO_RISK", "reason": msg}

    # 6) 盈亏比 —— 纯信息性 (2026-09-15: 阈值门槛已删除, BUY-LOW-v1 无 RR 要求, 永不否决)
    rr, rr_note = _rr_info(price, stop, target)
    if rr is None and rr_note:
        warnings.append("RR " + rr_note)

    # 7) T+1 / 隔夜压力
    t_plus_one = {"same_day_stop_available": False, "note": "T+1: 今日买入次日才能卖"}
    # 隔夜压力损失依赖"一手"股数 → 手动数量模式不计算（数量由用户决定）
    overnight_stress_loss = None if MANUAL else round(price * LOT * 0.05, 2)

    allowed = blocked is None
    if not MANUAL:
        reasons.append(f"净资产 {net:.2f} 元 (现金 {cash:.2f} + 持仓市值)")
        reasons.append(f"风险基准: 单笔≤2%={net*BP.RISK_SINGLE_PCT:.0f}元 "
                       f"组合≤4%={net*BP.RISK_PORT_PCT:.0f}元 单股≤{sc*100:.0f}%={net*sc:.0f}元")
        reasons.append(f"一手成本≈{one_lot_cost:.2f}元; 可买股数 风险{sz['by_risk']}/现金{sz['by_cash']}/"
                       f"单股{sz['by_cap']} → {sz['shares']}")
        reasons.append(f"隔夜-5%压力损失≈{overnight_stress_loss:.0f}元")
    else:
        reasons.append(BP.MANUAL_SIZE_NOTE)
    reasons.append(f"总仓位纪律上限 {tc*100:.0f}%(弱市下调); 防守池 {DEFENSE_POOL:.0f} 元独立管理, 不计入")
    if blocked:
        reasons.append("BLOCKED: " + blocked["reason"])

    append_event({"event": "BUY_GATE", "action": "BLOCKED" if not allowed else "ALLOWED",
                  "code": blocked["code"] if blocked else None, "context": context,
                  "price": price, "stop": stop, "target": target,
                  "rr": round(rr, 2) if rr else None, "hs300_pct": hs300_pct,
                  "market_weak": weak, "net_assets": round(net, 2),
                  "sizing_mode": BP.SIZING_MODE,
                  "sizing_shares": (sz["shares"] if sz else None),
                  "warnings": warnings})

    return {
        "allowed": allowed,
        "reasons": reasons,
        "warnings": warnings,
        "sizing_mode": BP.SIZING_MODE,
        "sizing": sz,                      # 手动模式为 None（不计算股数）
        "net_assets": round(net, 2),
        "position_after": (None if MANUAL else
                           {"shares": shares if allowed else 0,
                            "cost_basis": price if allowed else None,
                            "value": round(shares * price, 2) if allowed else 0}),
        "single_position_after": (None if MANUAL else
                                  {"ratio": round((shares * price) / net, 4) if net else 0,
                                   "max_single_value": round(net * sc, 2)}),
        "rr": rr,
        "overnight_stress_loss": overnight_stress_loss,   # 手动模式为 None
        "t_plus_one": t_plus_one,
        "hs300_pct": hs300_pct,
        "market_weak": weak,
        "context": context,
        "policy_version": (BP.POLICY_VERSION_MANUAL if MANUAL else BP.POLICY_VERSION),
        "hard_stop": None,
    }


def hard_stop_check(code: str, price: float, now_dt: Optional[datetime.datetime] = None) -> dict:
    """硬止损判定(读 sell-policy 真值)。price <= hard_stop 即触发。"""
    holdings = load_holdings()
    h = holdings.get(code)
    if not h:
        return {"triggered": False, "known": False}
    name, qty, cost = h
    hard_stop = _hard_stop_of(code, cost)
    triggered = price <= hard_stop
    # ⚠️ 2026-09-16 修复: 原为无条件写事件 → 每次自测/未触发调用都写一条,
    #    导致 events.jsonl 单日积累 270~540 条 HARD_STOP 噪音(淹没真实事件)。
    #    现改为【仅在触发时】记录。未触发不写(判定结果由调用方返回)。
    if triggered:
        append_event({"event": "HARD_STOP", "code": code, "triggered": True,
                      "price": price, "hard_stop": hard_stop, "cost": cost})
    return {"triggered": triggered, "hard_stop": hard_stop, "cost": cost,
            "name": name, "shares": qty, "known": True,
            "loss_approx": round((price - cost) * qty, 2)}


def get_authoritative_state() -> dict:
    """权威现金/持仓/防守池快照(不含凭据)。"""
    acc = BP.load_account()
    return {
        "policy_version": BP.POLICY_VERSION,
        "cash": acc["cash"],
        "cash_note": "来自 account.json (用户按券商截图维护)",
        "cash_updated_at": acc.get("updated_at"),
        "account_stale": acc.get("stale"),
        "account_warnings": acc.get("warnings", []),
        "defense_pool": DEFENSE_POOL,
        "holdings": {c: {"name": n, "shares": q, "cost": ct,
                         "hard_stop": _hard_stop_of(c, ct)}
                     for c, (n, q, ct) in acc["holdings"].items()},
    }


if __name__ == "__main__":
    print("== 权威状态 ==")
    print(json.dumps(get_authoritative_state(), ensure_ascii=False, indent=1))
    print()
    print("== 自测 ==")
    cases = [
        ("09:35 时段外(应 BLOCKED)", datetime.datetime(2026, 9, 15, 9, 35)),
        ("09:50 时段内", datetime.datetime(2026, 9, 15, 9, 50)),
        ("11:35 午休(应 BLOCKED)", datetime.datetime(2026, 9, 15, 11, 35)),
        ("13:30 时段内", datetime.datetime(2026, 9, 15, 13, 30)),
        ("14:50 时段外(应 BLOCKED)", datetime.datetime(2026, 9, 15, 14, 50)),
        ("周六(应 BLOCKED)", datetime.datetime(2026, 9, 19, 10, 0)),
    ]
    for label, dt in cases:
        r = evaluate_buy(44.80, 42.11, 50.00, now_dt=dt, hs300_pct=0.0)
        code = next((x for x in r["reasons"] if x.startswith("BLOCKED")), "—")
        print(f"  {label}: allowed={r['allowed']} | {code}")
    print()
    r = evaluate_buy(44.80, 42.11, 50.00, now_dt=datetime.datetime(2026, 9, 15, 10, 0), hs300_pct=0.0)
    print("  资金不足应为 warnings 而非阻断:", r["warnings"])
    print("  sizing:", json.dumps(r["sizing"], ensure_ascii=False))
    print("  净资产:", r["net_assets"])
    print()
    print("  硬止损 赤峰:", hard_stop_check("sh600988", 43.5))
