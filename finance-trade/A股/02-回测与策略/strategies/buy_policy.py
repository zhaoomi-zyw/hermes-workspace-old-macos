#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
买入策略唯一权威模块 — BUY-LOW-v1-20260915
==========================================
规则依据: /Users/omi/workspace/quant-backtest/buy_policy_confirmed_20260915.md
(用户逐项确认版)

职责:
  1) 唯一参数配置(禁止在脚本/cron/提示词中复制参数)
  2) 三买入条件的纯函数计算(供实盘脚本与回测共用)
  3) 资金/风险预算与最大股数
  4) 提醒生命周期状态机: 候选占用 / 15分钟有效期 / 到期需重新核验 /
     清仓后信号失效登记 / 单一待确认建议

状态文件: ~/.hermes/state/buy-policy-state.json (原子写)
与 SELL-POLICY 平行, 互不覆盖。

用法:
  python buy_policy.py --test      # 验收自测
  from buy_policy import ...       # 脚本/回测调用
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, time

# ==================== 唯一参数配置 ====================
POLICY_VERSION = "BUY-LOW-v1-20260915"

# ==================== 数量模式开关（2026-09-16） ====================
# "auto"   : 旧行为 —— 模块计算最大股数，并以 单笔2%/组合4%/单股35%/现金 作为提醒门槛
# "manual" : 新行为 —— **取消"买多少"的一切自动计算与门槛**，数量由用户自行决定。
#            现金不足 / 净资产未知 / 不足一手 / 超2%4%35% 均**不得屏蔽合格信号**。
#            提醒只写信号与价格依据，不写最大股数、不做虚拟资金/风险预算预占。
# 详见 /Users/omi/workspace/quant-backtest/results/manual_sizing_rollout_20260916.md
SIZING_MODE = "manual"
POLICY_VERSION_MANUAL = "BUY-LOW-v1-manual-20260916"

# 手动数量模式下的固定声明（提醒必须包含；不得改写为"资金足够/建议融资"）
MANUAL_SIZE_NOTE = ("买入数量由你自行决定，请在券商端核对可用资金、交易单位与费用。"
                    "（本提醒不判断资金是否足够，也不建议融资）")

# ⚠️ 历史回测冻结配置：v4 引擎(results/confirmed_policy_3y_20260914) 依赖以下数值复现历史结果。
#    **禁止**把它们改成 None / inf 或删除；新手动数量模式不读取这些值作为门槛。
FROZEN_AUTO_CONFIG = {
    "risk_single_pct": 0.02, "risk_port_pct": 0.04, "pos_single_pct": 0.35,
    "hard_stop_pct": 0.06, "alert_ttl_min": 15,
    "fee_buy": 0.00025, "fee_sell": 0.00125,
    "commission_min": 5.0, "stamp_rate_sell": 0.0005, "transfer_rate": 0.00001,
    "note": "冻结于 2026-09-16 手动数量模式上线前; 仅供历史研究复现, 不参与线上提醒判定",
}
POLICY_FILE = "/Users/omi/workspace/quant-backtest/buy_policy_confirmed_20260915.md"

# 条件① 中期趋势
MA60_N = 60
MA60_LOOKBACK = 5          # MA60 相比 5 个交易日前

# 条件② ATR 回调区间
ATR_N = 14
ATR_LOW = 2.5              # (H20-价)/ATR >= 2.5
ATR_HIGH = 4.5             # (H20-价)/ATR <= 4.5
H20_N = 20

# 条件③ 同刻缩量
VOL_RATIO_MAX = 0.80       # 严格小于
VOL_LOOKBACK_DAYS = 5      # 前 5 个交易日同刻

# 资金/风险
HARD_STOP_PCT = 0.06       # 新仓初始硬止损 = 成本 - 6%
RISK_SINGLE_PCT = 0.02     # 单笔计划损失 <= 净资产 2%
RISK_PORT_PCT = 0.04       # 组合计划风险 <= 净资产 4%
POS_SINGLE_PCT = 0.35      # 单股市值 <= 净资产 35%
FEE_BUY = 0.00025          # 买入佣金(万2.5)
FEE_SELL = 0.00025 + 0.001 # 卖出佣金+印花税

# ---------- 费率明细（⚠️ 未校准：券商费率协议未获取） ----------
# 证据状态（详见 results/cost_calibration_20260915/evidence.md）：
#   · 未找到交割单/对账单或费率协议页面 → 比例费率与印花税无直接凭据
#   · 仅两个间接线索（成本−成交价差）：工业富联 +5.10 元、星网锐捷 +5.00 元
#     → 只能支持"最低档约 5 元"，**不可反推比例费率**（样本全落在最低费档）
#   · 过户费是否收取口径不一致（工业富联样本含 ~0.06，星网样本无）
# 因此以下值为**未校准假定**，回测结果对该块敏感，须在报告中显式标注。
FEE_UNCALIBRATED = True
COMMISSION_MIN = 5.0       # 单笔最低佣金（仅间接线索支持）
STAMP_RATE_SELL = 0.0005   # 印花税(卖出) 2023-08-28 起万5
TRANSFER_RATE = 0.00001    # 过户费(双边) 万0.1

# 时段与有效期
SESSIONS = [(945, 1130), (1300, 1445)]   # 允许新买入提醒
ALERT_TTL_MIN = 15                        # 提醒有效 15 分钟
SESSION_LATEST = 1445                     # 最晚截止 14:45

STATE_FILE = os.path.expanduser("~/.hermes/state/buy-policy-state.json")

# 保护线(与卖出策略一致的对接参数, 供实现参考)
PROTECT_TRIGGER_PCT = 0.08
PROTECT_FLOOR_PCT = 0.03
PROTECT_TRAIL_PCT = 0.07


# ==================== 时间门控 ====================
def in_session(hhmm: int) -> bool:
    return any(a <= hhmm <= b for a, b in SESSIONS)


def now_hhmm(dt: datetime = None) -> int:
    dt = dt or datetime.now()
    return dt.hour * 100 + dt.minute


def alert_expiry(now: datetime) -> datetime:
    exp = now + timedelta(minutes=ALERT_TTL_MIN)
    if exp.hour * 100 + exp.minute > SESSION_LATEST:
        exp = now.replace(hour=SESSION_LATEST // 100,
                          minute=SESSION_LATEST % 100, second=0, microsecond=0)
    return exp


# ==================== 条件① 趋势 ====================
def sma(vals, k):
    return sum(vals[-k:]) / k if len(vals) >= k else None


def ma60_series(closes):
    """按日 MA60(不足60日为 None)。"""
    out = []
    for i in range(len(closes)):
        out.append(sum(closes[i + 1 - MA60_N:i + 1]) / MA60_N if i + 1 >= MA60_N else None)
    return out


def trend_ok(price, ma60_now, ma60_5ago):
    """① 价 > MA60 且 MA60 > 5个交易日前 MA60。"""
    if ma60_now is None or ma60_5ago is None:
        return False
    return price > ma60_now and ma60_now > ma60_5ago


def ma60_change_pct(ma60_now, ma60_5ago):
    if not ma60_now or not ma60_5ago:
        return None
    return (ma60_now / ma60_5ago - 1) * 100


# ==================== 条件② ATR 回调区间 ====================
def true_ranges(rows):
    """rows: 已完成日K [{high,low,close}] 顺序旧→新。"""
    trs = []
    for i in range(1, len(rows)):
        h, l, pc = rows[i]["high"], rows[i]["low"], rows[i - 1]["close"]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return trs


def atr14_wilder(rows):
    """ATR14 Wilder 平滑: 初始=前14个有效TR简单平均, 之后递推。"""
    trs = true_ranges(rows)
    if len(trs) < ATR_N:
        return None
    atr = sum(trs[:ATR_N]) / ATR_N
    for tr in trs[ATR_N:]:
        atr = (atr * (ATR_N - 1) + tr) / ATR_N
    return atr


def h20(highs):
    return max(highs[-H20_N:]) if len(highs) >= 1 else None


def atr_deviation(price, h20_val, atr):
    if not atr or atr <= 0 or h20_val is None:
        return None
    return (h20_val - price) / atr


def atr_band_ok(price, h20_val, atr, ma60_now):
    """② 2.5 <= dev <= 4.5 且 价 > MA60。"""
    dev = atr_deviation(price, h20_val, atr)
    if dev is None:
        return (False, None)
    return (ATR_LOW <= dev <= ATR_HIGH and price > ma60_now, dev)


def allowed_price_range(h20_val, atr, ma60_now):
    """允许价格区间 = [max(H20-4.5ATR, MA60), H20-2.5ATR]。"""
    lo = max(h20_val - ATR_HIGH * atr, ma60_now)
    hi = h20_val - ATR_LOW * atr
    return (round(lo, 2), round(hi, 2))


# ==================== 条件③ 同刻缩量 ====================
def vol_ratio_ok(ratio, confirmed):
    """③ <0.80 且数据可确认。未确认 => 不放行。"""
    if not confirmed or ratio is None:
        return False
    return ratio < VOL_RATIO_MAX


def same_time_vol_ratio(min5, now_dt):
    """min5: [{dt:datetime, day:'YYYY-MM-DD', volume:股}]。
    返回 (ratio, detail, confirmed)。confirmed=False 表示无法确认(不放行)。"""
    ref = now_dt.replace(second=0, microsecond=0)
    ref = ref - timedelta(minutes=ref.minute % 5)
    ref_t = ref.time()
    today = now_dt.strftime("%Y-%m-%d")
    if not min5:
        return (None, "无分钟数据", False)

    def cum_for_day(day):
        bars = [b for b in min5 if b["day"] == day
                and time(9, 30) <= b["dt"].time() <= ref_t]
        if not bars:
            return None
        if min(b["dt"].time() for b in bars) > time(9, 35):
            return None  # 开盘段不完整
        return sum(b["volume"] for b in bars)

    today_cum = cum_for_day(today)
    if today_cum is None:
        return (None, f"{today} 无截至{ref_t.strftime('%H:%M')}的分钟量", False)
    days = sorted({b["day"] for b in min5 if b["day"] < today}, reverse=True)
    hist, used = [], []
    for d in days:
        c = cum_for_day(d)
        if c is None:
            continue
        hist.append(c)
        used.append(d)
        if len(hist) >= VOL_LOOKBACK_DAYS:
            break
    if len(hist) < VOL_LOOKBACK_DAYS:
        return (None, f"前{VOL_LOOKBACK_DAYS}交易日同刻基准不足(仅{len(hist)}天)", False)
    base = sum(hist) / len(hist)
    if base <= 0:
        return (None, "基准无效(0)", False)
    return (today_cum / base, f"今{today_cum:.0f}/前5均{base:.0f}({used[-1]}~{used[0]})", True)


def vol_ratio_close(min5, day_str):
    """收盘口径缩量(清仓后失效登记用): 该日全天量 / 此前5交易日全天均量。"""
    if not min5:
        return (None, "无分钟数据", False)
    def day_total(d):
        tot = sum(b["volume"] for b in min5 if b["day"] == d)
        return tot if tot > 0 else None
    today_total = day_total(day_str)
    if today_total is None:
        return (None, f"{day_str} 无全天量", False)
    days = sorted({b["day"] for b in min5 if b["day"] < day_str}, reverse=True)[:VOL_LOOKBACK_DAYS]
    if len(days) < VOL_LOOKBACK_DAYS:
        return (None, f"前{VOL_LOOKBACK_DAYS}交易日全天基准不足(仅{len(days)}天)", False)
    tots = [day_total(d) for d in days]
    if any(t is None for t in tots):
        return (None, "基准日数据缺失", False)
    base = sum(tots) / len(tots)
    if base <= 0:
        return (None, "基准无效(0)", False)
    return (today_total / base, f"全天{today_total:.0f}/前5日均{base:.0f}", True)


def close_check_invalidated(price, ma60_now, ma60_5ago, h20_val, atr, vol_ratio_c, vol_confirmed):
    """§6 清仓后信号失效判定(收盘口径): 三条件至少一项不满足 => 失效登记。
    数据缺失不算失效(返回 (False, '数据缺失'))。"""
    if ma60_now is None or ma60_5ago is None or atr is None or h20_val is None:
        return (False, "数据缺失")
    t = trend_ok(price, ma60_now, ma60_5ago)
    a, _ = atr_band_ok(price, h20_val, atr, ma60_now)
    v = vol_ratio_ok(vol_ratio_c, vol_confirmed)
    unmet = []
    if not t:
        unmet.append("①趋势不满足")
    if not a:
        unmet.append("②ATR区间不满足")
    if not v:
        unmet.append("③缩量不满足" if vol_confirmed else "③缩量无法确认")
    if unmet:
        return (True, "、".join(unmet))
    return (False, "三条件仍全部满足")


# ==================== 资金/风险 ====================
def net_assets(cash, holdings, prices):
    """净资产 = 现金 + Σ(持仓股数 × 现价)。holdings: {code:(name,qty,cost)}"""
    total = cash
    for code, (_n, qty, cost) in holdings.items():
        px = prices.get(code)
        total += qty * (px if px and px > 0 else cost)
    return total


def max_shares(price, net, cash, cur_holding_value=0.0):
    """取 单笔2%风险 / 现金 / 单股35% 三者最小, 整手向下取整。
    返回 (股数, 明细)。最低一手超预算 => 0。"""
    stop = price * (1 - HARD_STOP_PCT)
    loss_per_share = (price - stop) + price * FEE_BUY + stop * FEE_SELL
    if loss_per_share <= 0:
        return (0, "止损价差<=0")
    by_risk = int((net * RISK_SINGLE_PCT) / loss_per_share // 100) * 100
    by_cash = int(cash / (price * (1 + FEE_BUY)) // 100) * 100
    avail_val = max(0.0, net * POS_SINGLE_PCT - cur_holding_value)
    by_cap = int(avail_val / (price * (1 + FEE_BUY)) // 100) * 100
    n = max(0, min(by_risk, by_cash, by_cap))
    return (n, f"风险{by_risk}/现金{by_cash}/单股35%{by_cap}")


def portfolio_risk(holdings, prices):
    """现有持仓计划风险 = Σ max(0, 价-硬止损)×数量 + 卖出费。
    浮盈不能抵扣其他持仓风险(此处只累加正距离)。"""
    risk = 0.0
    for code, (_n, qty, cost) in holdings.items():
        px = prices.get(code)
        if not px:
            continue
        stop = cost * (1 - HARD_STOP_PCT)
        if px > stop:
            risk += (px - stop) * qty + px * qty * FEE_SELL
    return risk


def portfolio_risk_ok(risk, net):
    return risk <= net * RISK_PORT_PCT


def planned_loss(price, shares):
    """新买入计划损失(含买入费与卖出费)。"""
    stop = price * (1 - HARD_STOP_PCT)
    return (price - stop) * shares + price * shares * FEE_BUY + stop * shares * FEE_SELL


def rank_key(cand):
    """排序: MA60 5日涨幅% 降序; 并列代码升序(确定性)。"""
    return (-(cand.get("ma60_chg") or -1e9), cand.get("code", ""))


ACCOUNT_FILE = os.path.expanduser("~/.hermes/state/account.json")
SELL_STATE_FILE = os.path.expanduser("~/.hermes/state/sell-policy-state.json")

# 仅当权威文件不可读时的兜底(过期值, 会打 stale 标记)
FALLBACK_CASH = 1287.47
FALLBACK_HOLDINGS = {"sh600988": ("赤峰黄金", 200, 44.735),
                     "sz002396": ("星网锐捷", 100, 35.880)}


def load_account():
    """现金 <- account.json (用户按券商截图维护, 脚本只读);
       持仓 <- sell-policy-state.json (持仓数量/成本的权威源)。
       返回 {cash, holdings{code:(name,qty,cost)}, updated_at, source, warnings[], stale}"""
    acc = {"cash": None, "holdings": {}, "updated_at": None, "source": None,
           "warnings": [], "stale": False}
    try:
        with open(ACCOUNT_FILE) as f:
            a = json.load(f)
        if a.get("cash") is not None:
            acc["cash"] = float(a["cash"])
        acc["updated_at"] = a.get("updated_at")
        acc["source"] = a.get("source")
    except Exception as e:
        acc["warnings"].append(f"账户文件不可读: {e}")
    try:
        with open(SELL_STATE_FILE) as f:
            sp = json.load(f)
        for code, p in (sp.get("positions") or {}).items():
            acc["holdings"][code] = (p.get("name", code),
                                     int(p.get("total_qty") or 0),
                                     float(p.get("cost") or 0.0))
    except Exception as e:
        acc["warnings"].append(f"卖出状态文件不可读: {e}")
    if acc["cash"] is None:
        acc["cash"] = FALLBACK_CASH
        acc["stale"] = True
        acc["warnings"].append(f"现金回退内置常量 {FALLBACK_CASH}(可能过期)")
    if not acc["holdings"]:
        acc["holdings"] = dict(FALLBACK_HOLDINGS)
        acc["stale"] = True
        acc["warnings"].append("持仓回退内置常量(可能过期)")
    return acc


def account_age_days(updated_at, today=None):
    """账户文件数据距今天数; 解析失败返回 None。"""
    if not updated_at:
        return None
    try:
        d = datetime.strptime(str(updated_at)[:10], "%Y-%m-%d").date()
    except Exception:
        return None
    t = today or datetime.now().date()
    return (t - d).days


def sizing(price, net, cash, cur_holding_value=0.0):
    """资金分档。**不再返回'是否可买'作为提醒门槛** —— 提醒一律发出,
    本函数只回答'能买多少'与'被什么卡住'。"""
    stop = price * (1 - HARD_STOP_PCT)
    loss_per_share = (price - stop) + price * FEE_BUY + stop * FEE_SELL
    risk_budget = net * RISK_SINGLE_PCT
    by_risk = int(risk_budget / loss_per_share // 100) * 100 if loss_per_share > 0 else 0
    by_cash = int(cash / (price * (1 + FEE_BUY)) // 100) * 100
    avail_val = max(0.0, net * POS_SINGLE_PCT - cur_holding_value)
    by_cap = int(avail_val / (price * (1 + FEE_BUY)) // 100) * 100
    shares = max(0, min(by_risk, by_cash, by_cap))
    one_lot_cost = price * 100 * (1 + FEE_BUY)
    blockers = []
    if by_cash < 100:
        blockers.append("现金不足")
    if by_risk < 100:
        blockers.append("单笔2%风险预算不足")
    if by_cap < 100:
        blockers.append("单股35%上限不足")
    return {"shares": shares, "by_risk": by_risk, "by_cash": by_cash, "by_cap": by_cap,
            "one_lot_cost": round(one_lot_cost, 2), "risk_budget": round(risk_budget, 2),
            "cash": round(cash, 2), "net": round(net, 2),
            "buyable": shares >= 100, "blockers": blockers,
            "cash_shortfall": round(max(0.0, one_lot_cost - cash), 2)}


def max_shares(price, net, cash, cur_holding_value=0.0):
    """兼容旧调用: 返回 (股数, 明细)。"""
    s = sizing(price, net, cash, cur_holding_value)
    return (s["shares"], f"风险{s['by_risk']}/现金{s['by_cash']}/单股35%{s['by_cap']}")


# ==================== 提醒生命周期状态 ====================
def _default_state():
    return {
        "version": POLICY_VERSION,
        "pending": None,          # 单一待确认建议(占用预算)
        "fired": {},              # {date: [codes]} 当日去重
        "invalidated": {},        # {code: {date, evidence}} 清仓后信号失效登记
        "history": [],            # 审计日志(最近若干条)
    }


def load_state(path=STATE_FILE):
    try:
        with open(path) as f:
            st = json.load(f)
    except Exception:
        st = _default_state()
    base = _default_state()
    for k, v in base.items():
        st.setdefault(k, v)
    st["version"] = POLICY_VERSION
    return st


def save_state(st, path=STATE_FILE):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def _log(st, kind, **kw):
    rec = {"ts": datetime.now().isoformat(timespec="seconds"), "event": kind}
    rec.update(kw)
    st.setdefault("history", []).append(rec)
    st["history"] = st["history"][-200:]


def roll_day(st, today):
    """跨日: 重置当日去重; pending 跨日则标记需重新核验(不自动释放)。"""
    if st.get("pending") and st["pending"].get("date") != today:
        st["pending"]["status"] = "needs_recheck"
        st["pending"]["released"] = False
        _log(st, "pending_carry_over", code=st["pending"].get("code"), date=today)
    return st


def day_fired(st, today):
    f = st.setdefault("fired", {})
    return set(f.get(today, []))


def mark_fired(st, today, code):
    st.setdefault("fired", {}).setdefault(today, [])
    if code not in st["fired"][today]:
        st["fired"][today].append(code)


def pending_active(st):
    """是否存在占用预算的待确认建议(含到期未释放)。"""
    p = st.get("pending")
    return bool(p and not p.get("released"))


def pending_expired(st, now=None):
    p = st.get("pending")
    if not p:
        return False
    now = now or datetime.now()
    return now.strftime("%H:%M") > p.get("expires", "00:00")


def mark_needs_recheck(st, now=None):
    """到期标记需重新核验; 不自动释放预算。"""
    p = st.get("pending")
    if p and not p.get("released") and pending_expired(st, now):
        if p.get("status") != "needs_recheck":
            p["status"] = "needs_recheck"
            _log(st, "expired_needs_recheck", code=p.get("code"))
    return st


def is_manual_mode() -> bool:
    """数量是否由用户自行决定（取消一切自动数量/资金门槛）。"""
    return SIZING_MODE == "manual"


def issue_alert(st, today, code, price, lo, hi, now=None, detail=None, shares=None):
    """发出**单一待确认建议**并做通知去重。

    2026-09-16 手动数量模式：不再需要/不再记录推荐股数，也**不做虚拟资金或风险预算预占**。
    仍然：同一时刻只保留一个待确认建议（防连续轰炸）；当日同股去重；
          成交/撤单状态未确认前不擅自释放或改写。
    已有待确认建议时返回 None（调用方应保持静默，而不是重复推送）。"""
    if pending_active(st):
        return None
    now = now or datetime.now()
    exp = alert_expiry(now)
    rec = {
        "date": today, "code": code, "at": now.strftime("%H:%M:%S"),
        "expires": exp.strftime("%H:%M"), "status": "active", "released": False,
        "price": price, "range": [lo, hi], "detail": detail,
        "sizing_mode": SIZING_MODE,
        "note": ("手动数量模式：数量由用户决定，本记录不占用资金/风险预算；"
                 "成交或撤单状态未确认前不释放；到期标记需重新核验"),
    }
    if shares is not None:          # 仅历史/自动模式兼容写入；手动模式不再产生
        rec["shares"] = shares
    st["pending"] = rec
    mark_fired(st, today, code)
    _log(st, "alert_issued", code=code, sizing_mode=SIZING_MODE, price=price)
    return rec


def release_pending(st, reason, confirmed_by_user=False):
    """**仅在用户确认成交/撤单**时释放待确认建议。
    绝不擅自把旧建议标成已成交或已撤单。"""
    p = st.get("pending")
    if not p:
        return False
    p["released"] = True
    p["release_reason"] = reason
    p["released_at"] = datetime.now().isoformat(timespec="seconds")
    st["pending"] = None
    _log(st, "pending_released", code=p.get("code"), reason=reason, user=confirmed_by_user)
    return True


def can_recommend(st, today, code):
    """是否可推荐该股: 无待确认建议 + 当日未推过 + 未被清仓后失效阻断。"""
    if pending_active(st):
        return (False, "已有待确认建议(未确认成交/撤单前不重复推送)")
    if code in day_fired(st, today):
        return (False, "当日已推送过")
    if is_blocked_after_exit(st, today, code):
        return (False, "清仓后未登记信号失效")
    return (True, "")


def is_blocked_after_exit(st, today, code):
    """§6: 清仓后不得因原信号仍成立就买回。
    - 无失效登记且曾清仓 => 阻断
    - 有失效登记 => 仅从登记次一交易日起放行
    (以 invalidated 记录存在且已过登记日为准)"""
    inv = st.get("invalidated", {}).get(code)
    if not inv:
        return bool(st.get("ever_exited", {}).get(code))
    return today <= inv.get("date", "")


def mark_exited(st, code, date=None):
    """登记该股曾清仓(进入 '需先确认信号失效' 状态)。"""
    st.setdefault("ever_exited", {})[code] = date or datetime.now().strftime("%Y-%m-%d")
    _log(st, "position_exited", code=code)
    return st


def register_invalidation(st, code, date, evidence):
    """登记收盘确认的信号失效(§6)。次一交易日起才可再提醒。"""
    st.setdefault("invalidated", {})[code] = {"date": date, "evidence": evidence}
    _log(st, "signal_invalidated", code=code, date=date, evidence=evidence)
    return st


# ==================== 自测 ====================
def _test():
    ok = fail = 0
    def chk(cond, name):
        nonlocal ok, fail
        if cond:
            ok += 1
        else:
            fail += 1
            print("  FAIL:", name)

    # 条件① 趋势
    chk(trend_ok(110, 100, 98) is True, "① 价>MA60且MA60上行")
    chk(trend_ok(90, 100, 98) is False, "① 价<MA60 否决")
    chk(trend_ok(110, 100, 101) is False, "① MA60下行 否决")
    chk(trend_ok(110, 100, 100) is False, "① MA60持平 否决(需严格>)")

    # 条件② ATR 区间(边界闭区间)
    chk(atr_band_ok(100, 0, 0, 90) == (False, None), "② atr=0 无法计算")
    # dev = (H20-price)/atr ; 构造 H20=1000, atr=100 => dev=2.5 边界
    chk(atr_band_ok(750, 1000, 100, 700)[0] is True, "② dev=2.5 边界通过")
    chk(atr_band_ok(550, 1000, 100, 500)[0] is True, "② dev=4.5 边界通过")
    chk(atr_band_ok(1000 - 249.9, 1000, 100, 700)[0] is False, "② dev<2.5 否决")
    chk(atr_band_ok(1000 - 450.1, 1000, 100, 500)[0] is False, "② dev>4.5 否决")
    chk(atr_band_ok(650, 1000, 100, 700)[0] is False, "② 价<MA60 否决")

    # 条件③ 缩量
    chk(vol_ratio_ok(0.79, True) is True, "③ 0.79 通过")
    chk(vol_ratio_ok(0.80, True) is False, "③ 0.80 不通过(严格<)")
    chk(vol_ratio_ok(0.5, False) is False, "③ 数据未确认 不放行")
    chk(vol_ratio_ok(None, True) is False, "③ ratio=None 不放行")

    # ATR Wilder: 常数TR => ATR=该常数
    rows = [{"high": 10, "low": 9, "close": 9.5}] + [{"high": 10, "low": 9, "close": 9.5}] * 20
    a = atr14_wilder(rows)
    chk(abs(a - 1.0) < 1e-9, f"ATR Wilder 常数TR=1 => {a}")

    # MA60 序列
    closes = list(range(1, 71))
    ms = ma60_series(closes)
    chk(ms[-1] == sum(range(11, 71)) / 60, "MA60 序列末值")

    # 资金/风险
    n, d = max_shares(44.80, 13525, 13525)
    chk(n == 0, f"单笔2%下 44.8元股=>0手(实得{n})")
    n2, _ = max_shares(4.72, 13525, 13525)
    chk(n2 >= 100 and n2 % 100 == 0, f"低价股可取整手(实得{n2})")
    n3, _ = max_shares(44.80, 13525, 100)  # 现金不足
    chk(n3 == 0, f"现金不足=>0(实得{n3})")
    r = portfolio_risk({"a": ("x", 100, 100.0)}, {"a": 110.0})
    chk(r > 0, "组合风险为正")
    chk(portfolio_risk_ok(r, 100000) is True, "组合风险 在限额内")
    chk(portfolio_risk_ok(1e9, 1000) is False, "组合风险 超限")

    # 排序
    cs = [{"code": "b", "ma60_chg": 1.0}, {"code": "a", "ma60_chg": 1.0},
          {"code": "c", "ma60_chg": 3.0}]
    cs.sort(key=rank_key)
    chk([c["code"] for c in cs] == ["c", "a", "b"], "排序: 涨幅降序+并列代码升序")

    # 时段
    chk(in_session(945) and in_session(1130), "时段 09:45-11:30 含端点")
    chk(not in_session(944) and not in_session(1131), "时段外")
    chk(in_session(1300) and in_session(1445), "时段 13:00-14:45 含端点")
    chk(not in_session(1200), "午休不触发")

    # 状态机
    st = _default_state()
    today = "2026-09-15"
    import tempfile
    tmpf = tempfile.mktemp(suffix=".json")
    chk(pending_active(st) is False, "初始无待确认")
    chk(can_recommend(st, today, "600760")[0] is True, "初始可推荐")
    chk(is_manual_mode() is True, "数量模式=manual(用户自主)")
    rec = issue_alert(st, today, "600760", 44.8, 43.5, 46.2,
                      now=datetime(2026, 9, 15, 10, 30))
    chk(rec is not None and pending_active(st) is True, "发出后进入待确认")
    chk("shares" not in rec, "手动模式不写入推荐股数")
    chk(rec.get("sizing_mode") == "manual", "待确认记录带 sizing_mode=manual")
    chk(issue_alert(st, today, "600219", 4.7, 4.5, 4.8,
                    now=datetime(2026, 9, 15, 10, 31)) is None, "有待确认时拒绝第二只")
    chk(can_recommend(st, today, "600760")[0] is False, "当日已推过")
    # 到期 => 需重新核验, 不自动释放
    mark_needs_recheck(st, now=datetime(2026, 9, 15, 10, 50))
    chk(st["pending"]["status"] == "needs_recheck", "到期标记需重新核验")
    chk(pending_active(st) is True, "到期仍待确认(不自动释放)")
    # 只有用户确认成交/撤单才释放
    chk(release_pending(st, "用户确认未成交", True) is True, "显式释放")
    chk(pending_active(st) is False, "释放后可再推荐")
    # 跨日 carry over
    st2 = _default_state()
    issue_alert(st2, today, "600760", 44.8, 43.5, 46.2, now=datetime(2026, 9, 15, 14, 0))
    roll_day(st2, "2026-09-16")
    chk(st2["pending"]["status"] == "needs_recheck" and pending_active(st2) is True,
        "跨日=>需重新核验且仍待确认")
    # 旧记录(含 shares 的历史条目)不得被擅自改写状态
    st_old = _default_state()
    st_old["pending"] = {"date": today, "code": "600760", "shares": 100,
                         "expires": "10:45", "status": "active", "released": False}
    roll_day(st_old, "2026-09-16")
    chk(st_old["pending"]["status"] == "needs_recheck"
        and st_old["pending"].get("release_reason") is None,
        "旧待确认建议不被擅自标成撤单/成交")
    # 清仓后失效登记
    st3 = _default_state()
    mark_exited(st3, "600760", "2026-09-15")
    chk(is_blocked_after_exit(st3, "2026-09-16", "600760") is True, "清仓后未登记失效=>阻断")
    register_invalidation(st3, "600760", "2026-09-16", "收盘②ATR区间不满足")
    chk(is_blocked_after_exit(st3, "2026-09-16", "600760") is True, "登记当日仍阻断")
    chk(is_blocked_after_exit(st3, "2026-09-17", "600760") is False, "次交易日起放行")
    # 收盘失效判定
    inv, why = close_check_invalidated(100, 90, 88, 120, 5, 0.5, True)
    chk(inv is False, f"三条件全满足=>不失效 ({why})")
    inv2, why2 = close_check_invalidated(80, 90, 88, 120, 5, 0.5, True)
    chk(inv2 is True, f"①不满足=>失效 ({why2})")
    inv3, why3 = close_check_invalidated(100, None, 88, 120, 5, 0.5, True)
    chk(inv3 is False, "数据缺失不算失效")
    # 持久化
    save_state(st3, tmpf)
    chk(load_state(tmpf)["invalidated"]["600760"]["date"] == "2026-09-16", "状态持久化/读回")
    os.remove(tmpf)

    print(f"\n{'='*46}")
    print(f"BUY-LOW-v1 自测: {ok}/{ok+fail} 通过")
    print(f"版本 {POLICY_VERSION}")
    print("=" * 46)
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    if "--test" in sys.argv:
        sys.exit(_test())
    print(f"{POLICY_VERSION}\n规则依据: {POLICY_FILE}\n状态文件: {STATE_FILE}")
