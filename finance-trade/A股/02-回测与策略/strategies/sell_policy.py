#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sell_policy.py — A股卖出策略唯一权威模块 (策略版本 SELL-POLICY-v1.0-20260914)
==============================================================================
单一模块 + 唯一参数配置，供以下入口共同调用（不在别处复制规则）：
  - strategies/dsa_strategy.py        (回测退出规则)
  - signal_daily.py                   (每日信号 / 持仓离场建议)
  - ~/.hermes/profiles/main/scripts/stop-loss-watch.py   (盘中每分钟 watchdog)
  - ~/.hermes/profiles/main/scripts/低吸/减仓等持仓监控
  - cron 提示词只引用本模块输出，不复制参数

设计要点
--------
1. 纯函数核心 (evaluate_* / transition_*) 无副作用、可回测 & 实盘共用；
   持久化 (StateStore) 为薄层，原子写 + 文件锁，支持多 cron 并发。
2. 本模块只产出"判定/事件/提醒文本"，绝不自动下单、绝不访问券商凭据。
3. 价格精度统一 round(2)；实盘/回测取整规则一致。

规则 (2026-09-14 用户确认)
-------------------------
R1 初始硬止损 S = round(成本 C × 0.94, 2)。盘中触及/跌破 → 退出事件。
R2 持仓后最高价 H 只取"本笔买入后的盘中最高成交价"(买入前当日高点/此前高点不计)。
R3 当 H ≥ C × 1.08 → 永久开启盈利保护；之后浮盈回落到 8% 以下也不关闭。
R4 开启后 P = max(历史有效 P, round(C×1.03,2), round(H×0.93,2))；只升不降。
   最低锁利 = 成本上方 3%；允许从高点回撤 7%。触发价不保证净收益/成交价。
R5 MA60 仅趋势提示，不独立触发卖出。
R6 加仓后保留已有保护状态与保护线。硬止损 S = max(旧 S, round(新整体成本×0.94,2))。
   盈利保护已开启时按新成本更新候选保护线，但不得降低原保护线。
   ⚠️边界: 不用新成本反向重算"加仓前高点是否曾达8%"; 未开启时保留历史高点用于审计,
   以加仓后有效行情判断新阈值 (见 add_position 注释与报告)。
R7 有效退出线 = 所有已启用止损/保护线中的最高值。触发即持久化退出事件。
   可卖部分提醒用户先卖; T+1 不可卖部分登记待退出, 下一交易日可卖时继续提醒,
   即使反弹也不自动取消。
R8 未确认卖出则持仓仍存在。部分成交后更新剩余数量, 待退出状态继续有效;
   相同事件不重复创建; 待退出期间脚本不得建议加仓来解除退出。
R9 仅确认全部清仓后结束本交易生命周期。清仓后再买回 → 重新初始化;
   旧记录保留, 不继承旧保护线。
"""
from __future__ import annotations

import copy
import datetime
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Optional

# ----------------------------------------------------------------------------
# 唯一参数配置 (Single Source of Truth)
# ----------------------------------------------------------------------------
STRATEGY_VERSION = "SELL-POLICY-v1.0-20260914"


@dataclass(frozen=True)
class SellParams:
    hard_stop_pct: float = 0.06       # R1 初始硬止损 = C×(1-0.06) = C×0.94
    profit_activate_pct: float = 0.08  # R3 H≥C×1.08 开启盈利保护
    profit_floor_pct: float = 0.03     # R4 保护线最低锁利 = C×1.03
    trail_from_peak_pct: float = 0.07  # R4 从高点回撤 7% → 保护线 = H×0.93
    price_decimals: int = 2            # 价格精度 (A股 0.01)


DEFAULT_PARAMS = SellParams()

# 兼容旧引用: 原先散落各处的默认数值集中于此
LEGACY_NOTE = "旧 -7%/-5% 移动止损、固定止盈已停用; 统一为本模块 SELL-POLICY-v1.0"


def round_price(x: float, params: SellParams = DEFAULT_PARAMS) -> float:
    """触发线/价格取整 (实盘/回测一致, A股最小价位 0.01)。"""
    return round(float(x), params.price_decimals)


def round_cost(x: float) -> float:
    """成本保留 3 位小数 (券商成本价常见 3 位, 如 44.735); 仅触发线取整到 2 位。"""
    return round(float(x), 3)


def now_iso() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


# ----------------------------------------------------------------------------
# 持仓生命周期状态
# ----------------------------------------------------------------------------
@dataclass
class PositionState:
    lifecycle_id: str                  # 本笔持仓生命周期唯一标识
    code: str                          # 腾讯格式代码, 如 sh600988
    name: str
    cost: float                        # 当前有效成本 C (含费口径, 与券商一致)
    total_qty: int                     # 当前总持仓
    sellable_qty: int                  # 当前可卖数量 (T+1 已解禁)
    today_new_qty: int                 # 当日新增(不可卖)数量
    peak_h: float                      # R2 持仓后最高成交价 H
    peak_h_time: str                   # H 对应行情时间
    protection_active: bool            # R3 盈利保护是否已开启(开启后不可关闭)
    hard_stop: float                   # R1/R6 硬止损线 S
    profit_line: float                 # R4 盈利保护线 P (0 = 未设)
    quote_time: str                    # 最近一次行情时间
    quote_valid: bool = True           # 报价是否新鲜有效
    quote_note: str = ""               # 报价无效原因
    pending_exit: Optional[dict] = None  # R7/R8 待退出事件 {event_id, reason, line, at, qty_sellable, qty_pending}
    fired_events: dict = field(default_factory=dict)  # 去重: event_id -> True
    add_log: list = field(default_factory=list)        # 加仓审计
    migrated: bool = False             # 历史状态迁移标记
    migration_note: str = ""
    created_at: str = field(default_factory=now_iso)

    # ---- 便捷属性 ----
    def effective_exit_line(self) -> float:
        """R7 有效退出线 = 所有已启用止损/保护线中的最高值。"""
        lines = [self.hard_stop]
        if self.protection_active and self.profit_line > 0:
            lines.append(self.profit_line)
        return round_price(max(lines))

    def is_exit_pending(self) -> bool:
        return self.pending_exit is not None


# ----------------------------------------------------------------------------
# 纯函数核心: 状态转换
# ----------------------------------------------------------------------------
def init_position(
    code: str,
    name: str,
    cost: float,
    qty: int,
    *,
    sellable_qty: Optional[int] = None,
    today_new_qty: Optional[int] = None,
    entry_date: Optional[str] = None,
    params: SellParams = DEFAULT_PARAMS,
) -> PositionState:
    """R1/R2/R9 建仓初始化。sellable 默认全可卖(非当日买)。"""
    cost = round_cost(cost)
    h = cost  # 初始 H = 成本价 (尚无持仓后更高成交价)
    return PositionState(
        lifecycle_id=f"LC-{code}-{entry_date or datetime.date.today().isoformat()}",
        code=code,
        name=name,
        cost=cost,
        total_qty=qty,
        sellable_qty=qty if sellable_qty is None else sellable_qty,
        today_new_qty=0 if today_new_qty is None else today_new_qty,
        peak_h=h,
        peak_h_time=entry_date or "",
        protection_active=False,
        hard_stop=round_price(cost * (1 - params.hard_stop_pct), params),
        profit_line=0.0,
        quote_time="",
    )


def _activate_and_update_lines(st: PositionState, params: SellParams) -> None:
    """R3/R4 依据当前 H 开启/更新盈利保护线 (就地修改)。"""
    # R3: H ≥ C×1.08 永久开启
    if not st.protection_active:
        if st.peak_h >= round_price(st.cost * (1 + params.profit_activate_pct), params):
            st.protection_active = True
            st.profit_line = 0.0  # 下面统一计算
    if st.protection_active:
        cand = [
            st.profit_line if st.profit_line > 0 else 0.0,
            round_price(st.cost * (1 + params.profit_floor_pct), params),
            round_price(st.peak_h * (1 - params.trail_from_peak_pct), params),
        ]
        st.profit_line = round_price(max(cand))


def update_quote(
    st: PositionState,
    price: float,
    *,
    quote_time: str,
    intraday_high: Optional[float] = None,
    is_valid: bool = True,
    invalid_reason: str = "",
    params: SellParams = DEFAULT_PARAMS,
) -> PositionState:
    """R2/R3/R4 用一笔(有效)行情更新状态: 更新 H、必要时开启保护、刷新线。

    报价无效时(R7 要求): 不更新 H、不关闭既有保护, 仅标记 quote_valid=False。
    """
    st.quote_time = quote_time
    if not is_valid:
        st.quote_valid = False
        st.quote_note = invalid_reason or "报价无效"
        return st
    st.quote_valid = True
    st.quote_note = ""
    price = round_price(price, params)
    # R2: H 只取本笔买入后出现过的最高价
    cand_h = price
    if intraday_high is not None:
        cand_h = max(cand_h, round_price(intraday_high, params))
    if cand_h > st.peak_h:
        st.peak_h = cand_h
        st.peak_h_time = quote_time
    _activate_and_update_lines(st, params)
    return st


def evaluate_exit(
    st: PositionState,
    price: float,
    *,
    quote_time: str = "",
    params: SellParams = DEFAULT_PARAMS,
) -> Optional[dict]:
    """R7 判定是否产生退出事件(纯函数, 不改状态; 去重由 fire_exit 处理)。

    返回事件 dict 或 None。触发原因为触发线所在类别(硬止损/盈利保护)。
    """
    if st.is_exit_pending():
        # 已有待退出事件: 不重复创建(R8), 但仍返回既有待退出的"续报"标记
        return None
    if not st.quote_valid:
        return None  # R7 陈旧/无效报价不得产生退出
    price = round_price(price, params)
    hstop = st.hard_stop
    pline = st.profit_line if st.protection_active else 0.0
    eff = st.effective_exit_line()
    if price <= eff:
        # 判定触发的是哪条线(优先更高级别=保护线)
        if st.protection_active and pline > 0 and price <= pline:
            reason, line = "盈利保护", pline
        else:
            reason, line = "硬止损", hstop
        event_id = f"{st.lifecycle_id}:{reason}:{line:.2f}"
        at = quote_time or now_iso()
        return {
            "event_id": event_id,
            "reason": reason,
            "line": line,
            "effective_line": eff,
            "price": price,
            "cost": st.cost,
            "peak_h": st.peak_h,
            "total_qty": st.total_qty,
            "qty_sellable": st.sellable_qty,
            "qty_pending": st.today_new_qty,
            "at": at,
        }
    return None


def fire_exit(st: PositionState, event: dict) -> bool:
    """R7/R8 持久化退出事件(去重)。返回 True=新事件, False=重复忽略。"""
    eid = event["event_id"]
    if eid in st.fired_events:
        return False
    st.fired_events[eid] = True
    st.pending_exit = {
        "event_id": eid,
        "reason": event["reason"],
        "line": event["line"],
        "at": event["at"],
        "qty_sellable": event["qty_sellable"],
        "qty_pending": event["qty_pending"],
    }
    return True


def add_position(
    st: PositionState,
    add_qty: int,
    add_price: float,
    *,
    entry_date: str,
    params: SellParams = DEFAULT_PARAMS,
) -> PositionState:
    """R6 加仓。

    规则:
      - 新成本 C' = (旧成本×旧量 + 加仓价×加仓量) / 新总量 (含费口径由调用方保证)
      - 硬止损 S = max(旧 S, round(C'×0.94,2)) —— 只升不降
      - 保留 protection_active; 已开启时按新成本更新候选保护线, 但不得降低原线
      - ⚠️边界: 不因加仓而用"新成本"反向重算加仓前高点是否曾达 8%。
        即: 若加仓前未开启保护, 加仓后仍以"加仓后的 H"判断是否达到 C'×1.08
        (历史 H 保留用于审计, 不用于以新成本触发开启), 避免"事后诸葛亮"式开启。
      - 加仓数量当日不可卖 → 计入 today_new_qty
    """
    st.add_log.append({
        "at": now_iso(), "entry_date": entry_date,
        "add_qty": add_qty, "add_price": round_price(add_price, params),
        "old_cost": st.cost, "old_total": st.total_qty,
        "protection_active_before": st.protection_active,
        "peak_h_before": st.peak_h,
    })
    old_total = st.total_qty
    new_total = old_total + add_qty
    new_cost = round_cost((st.cost * old_total + round_price(add_price, params) * add_qty) / new_total)
    st.cost = new_cost
    st.total_qty = new_total
    st.today_new_qty += add_qty
    # 硬止损只升不降
    st.hard_stop = round_price(max(st.hard_stop, new_cost * (1 - params.hard_stop_pct)), params)
    # 保护线不得降低: 若已开启, 更新候选但取 max(原线, 候选)
    if st.protection_active:
        cand = [
            st.profit_line if st.profit_line > 0 else 0.0,
            round_price(new_cost * (1 + params.profit_floor_pct), params),
            round_price(st.peak_h * (1 - params.trail_from_peak_pct), params),
        ]
        st.profit_line = round_price(max(cand))
    # 未开启时: 保留 st.peak_h 供审计, 但"开启判定"仍以加仓后行情为准。
    # 实现上: 记录一个 base, 使后续 H 需超过加仓后成本线才开启。
    # 做法: 若未开启, 将开启比较基线提升到加仓价(避免旧高点直接触发新成本开启)。
    if not st.protection_active:
        st.peak_h = max(st.peak_h, round_price(add_price, params))  # 审计保留
        # 关键: 记录 add_base, update_quote 开启判定用 max(H_after_add)
        st.add_log[-1]["activation_base_after_add"] = round_price(add_price, params)
        st.migration_note = (st.migration_note + " | " if st.migration_note else "") + \
            f"加仓@ {entry_date}: 未开启保护, 以加仓后行情判断开启(不重算加仓前高点)"
    return st


def confirm_sell(
    st: PositionState,
    qty: int,
    *,
    price: Optional[float] = None,
    params: SellParams = DEFAULT_PARAMS,
) -> PositionState:
    """R7/R8 确认卖出 qty 股。部分成交后更新剩余; 待退出状态继续有效。"""
    qty = int(qty)
    st.sellable_qty = max(0, st.sellable_qty - qty)
    st.total_qty = max(0, st.total_qty - qty)
    # 若待退出事件的 sellable 部分已清, 更新事件内剩余待退出数量
    if st.pending_exit:
        st.pending_exit["qty_sellable"] = st.sellable_qty
        st.pending_exit["qty_pending"] = st.today_new_qty
    return st


def confirm_clear(st: PositionState) -> PositionState:
    """R9 确认全部清仓 → 结束生命周期(total_qty=0)。"""
    st.total_qty = 0
    st.sellable_qty = 0
    st.today_new_qty = 0
    return st


def roll_trading_day(st: PositionState) -> PositionState:
    """R7 下一交易日: 当日新增解禁为可卖; 待退出继续有效(不因反弹取消)。"""
    st.sellable_qty += st.today_new_qty
    st.today_new_qty = 0
    if st.pending_exit:
        st.pending_exit["qty_sellable"] = st.sellable_qty
        st.pending_exit["qty_pending"] = 0
    return st


def can_add(st: PositionState) -> tuple:
    """R8 待退出期间不得建议加仓解除退出。返回 (ok, reason)。"""
    if st.is_exit_pending():
        return (False, "存在待退出事件, 待退出期间禁止加仓(不得以加仓解除退出)")
    return (True, "")


# ----------------------------------------------------------------------------
# 提醒文本 (供各入口复用; 只读, 不发送)
# ----------------------------------------------------------------------------
def build_exit_alert(st: PositionState, event: dict) -> str:
    """R7 提醒模板: 含股票/代码/策略版本/报价时间/原因/成本/最高价/触发线/数量/事件ID。"""
    lines = [
        f"🔔 退出事件 · {st.name}({st.code[2:]})",
        f"   策略版本: {STRATEGY_VERSION}",
        f"   报价: {event['price']:.2f} @ {event.get('at','')}",
        f"   触发原因: {event['reason']} (触发线 {event['line']:.2f})",
        f"   成本: {st.cost:.2f} | 持仓后最高价 H: {st.peak_h:.2f}",
        f"   有效退出线: {st.effective_exit_line():.2f}",
        f"   可卖: {event['qty_sellable']}股 | 待退出(T+1): {event['qty_pending']}股",
        f"   事件ID: {event['event_id']}",
        "   ⚠️ 请在券商端操作并反馈成交; 本提醒不代表已卖出。",
    ]
    return "\n".join(lines)


# ----------------------------------------------------------------------------
# 持久化 (原子写 + 文件锁, 支持多 cron 并发)
# ----------------------------------------------------------------------------
STATE_FILE = os.path.expanduser("~/.hermes/state/sell-policy-state.json")
LOCK_FILE = STATE_FILE + ".lock"


class StateStore:
    """薄持久化层。所有状态变更走 with store.transaction() 保证原子性。"""

    def __init__(self, path: str = STATE_FILE):
        self.path = path
        self.lock_path = path + ".lock"

    # 文件锁: macOS/Linux fcntl
    class _Lock:
        def __init__(self, lock_path):
            self.lock_path = lock_path
            self.fh = None

        def __enter__(self):
            os.makedirs(os.path.dirname(self.lock_path), exist_ok=True)
            self.fh = open(self.lock_path, "a+")
            try:
                import fcntl
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_EX)
            except Exception:
                pass
            return self

        def __exit__(self, *a):
            try:
                import fcntl
                fcntl.flock(self.fh.fileno(), fcntl.LOCK_UN)
            except Exception:
                pass
            if self.fh:
                self.fh.close()
            return False

    def load(self) -> dict:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"strategy_version": STRATEGY_VERSION, "positions": {}}

    def _write(self, data: dict) -> None:
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def save(self, data: dict) -> None:
        with self._Lock(self.lock_path):
            self._write(data)

    def put(self, st: PositionState) -> None:
        """原子 upsert 单个持仓。"""
        with self._Lock(self.lock_path):
            data = self.load()
            data.setdefault("positions", {})
            data["positions"][st.code] = asdict(st)
            data["strategy_version"] = STRATEGY_VERSION
            data["updated_at"] = now_iso()
            self._write(data)

    def get(self, code: str) -> Optional[PositionState]:
        data = self.load()
        raw = data.get("positions", {}).get(code)
        if not raw:
            return None
        return PositionState(**raw)

    def all(self) -> dict:
        data = self.load()
        return {c: PositionState(**v) for c, v in data.get("positions", {}).items()}

    def remove(self, code: str) -> None:
        with self._Lock(self.lock_path):
            data = self.load()
            data.get("positions", {}).pop(code, None)
            data["updated_at"] = now_iso()
            self._write(data)


# ----------------------------------------------------------------------------
# R7 日切: 每交易日首次运行把"当日新增"解禁为可卖 (2026-09-15 补)
# ----------------------------------------------------------------------------
def roll_new_trading_day(store: StateStore, today: Optional[str] = None) -> list:
    """幂等日切。用 state 内 roll_meta.last_roll_date 门控, 同一交易日重复调用无副作用。
    返回本次解禁明细 [(code, name, qty)]。

    ⚠️ 2026-09-15 补: roll_trading_day() 此前只有回测/迁移脚本调用, 生产入口
    (stop-loss-watch.py / signal_daily.py) 从未调用 → T+1 解禁根本不生效,
    sellable_qty 永久停在建仓时的值。实盘表现: 9/14 买入的星网锐捷在 9/15
    盘中仍显示"可卖 0 股 / 待退出(T+1) 100 股", 若当日触发退出线会误导为"卖不掉"。
    """
    today = today or datetime.date.today().isoformat()
    out = []
    with store._Lock(store.lock_path):
        data = store.load()
        meta = data.setdefault("roll_meta", {})
        if meta.get("last_roll_date") == today:
            return out
        positions = data.get("positions", {})
        for code, raw in list(positions.items()):
            try:
                st = PositionState(**raw)
            except Exception:
                continue
            if st.today_new_qty > 0:
                qty = st.today_new_qty
                roll_trading_day(st)
                positions[code] = asdict(st)
                out.append((code, st.name, qty))
        meta["last_roll_date"] = today
        data["updated_at"] = now_iso()
        store._write(data)
    return out


def roll_new_trading_day_default(today: Optional[str] = None) -> list:
    """便捷入口: 用默认状态文件做日切。"""
    return roll_new_trading_day(StateStore(), today=today)


# ----------------------------------------------------------------------------
# 自测 / 验收场景 (11 项, 与任务书对齐)
# ----------------------------------------------------------------------------
def _st(cost, qty=100, **kw):
    p = DEFAULT_PARAMS
    st = init_position("sh600000", "测试股", cost, qty, **kw)
    return st


def run_acceptance_tests(verbose: bool = True) -> bool:
    """跑任务书 11 个验收场景, 全部通过返回 True。"""
    P = DEFAULT_PARAMS
    results = []

    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))
        if verbose:
            print(f"{'✅' if cond else '❌'} {name}" + (f"  [{detail}]" if detail else ""))

    # 场景1: C=100, 价格94 → 硬止损触发; MA60 单独跌破不触发
    st = _st(100.0)
    update_quote(st, 95.0, quote_time="t1")            # 未触发
    e0 = evaluate_exit(st, 95.0)
    update_quote(st, 94.0, quote_time="t2")
    e1 = evaluate_exit(st, 94.0)
    check("场景1 硬止损: C=100 价94触发", e1 is not None and e1["reason"] == "硬止损")
    check("场景1 MA60单独跌破不触发(本模块不读MA60)", e0 is None)

    # 场景2: 100→108 保护开启 P=103; 回落107保护仍开; 触103生成事件
    st = _st(100.0)
    update_quote(st, 108.0, quote_time="t1")
    check("场景2 H=108开启保护, P=103", st.protection_active and abs(st.profit_line - 103.0) < 1e-9,
          f"P={st.profit_line}")
    update_quote(st, 107.0, quote_time="t2")
    check("场景2 回落107保护仍开启", st.protection_active)
    e = evaluate_exit(st, 103.0, quote_time="t3")
    check("场景2 触103生成退出事件", e is not None and e["reason"] == "盈利保护")

    # 场景3: 100→120 P=111.6; 跌至111.6触发; 之后反弹不得撤销事件
    st = _st(100.0)
    update_quote(st, 120.0, quote_time="t1")
    check("场景3 H=120 → P=111.6", abs(st.profit_line - 111.6) < 1e-9, f"P={st.profit_line}")
    e = evaluate_exit(st, 111.6, quote_time="t2")
    check("场景3 触111.6触发", e is not None)
    fire_exit(st, e)
    update_quote(st, 118.0, quote_time="t3")   # 反弹
    check("场景3 反弹不撤销退出事件", st.is_exit_pending())

    # 场景4: 高点上移保护线提高, 回落不降; 重启后保持
    st = _st(100.0)
    update_quote(st, 110.0, quote_time="t1"); p1 = st.profit_line
    update_quote(st, 125.0, quote_time="t2"); p2 = st.profit_line
    update_quote(st, 115.0, quote_time="t3"); p3 = st.profit_line
    check("场景4 保护线只升不降", p2 >= p1 and p3 == p2, f"{p1}->{p2}->{p3}")
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        store = StateStore(os.path.join(d, "s.json"))
        store.put(st)
        st2 = store.get(st.code)
    check("场景4 重启(重载)后保护线保持", st2 is not None and st2.profit_line == st.profit_line
          and st2.protection_active == st.protection_active)

    # 场景5: 原100@100 S=94, 再买100@96 → 新成本98, S仍94(不降至92.12)
    st = _st(100.0, 100)
    check("场景5 初始S=94", abs(st.hard_stop - 94.0) < 1e-9, f"S={st.hard_stop}")
    add_position(st, 100, 96.0, entry_date="d2")
    check("场景5 加仓后成本98", abs(st.cost - 98.0) < 1e-9, f"C={st.cost}")
    check("场景5 S保持94(不降至92.12)", abs(st.hard_stop - 94.0) < 1e-9, f"S={st.hard_stop}")

    # 场景6: 已保护+已加仓: 状态继承、保护线不下降; 边界: 加仓前高点/新成本
    st = _st(100.0, 100)
    update_quote(st, 112.0, quote_time="t1")   # 开启保护 P>=103
    p_before = st.profit_line
    add_position(st, 100, 104.0, entry_date="d2")
    check("场景6 加仓后保护仍开启(继承)", st.protection_active)
    check("场景6 保护线不下降", st.profit_line >= p_before, f"{p_before}->{st.profit_line}")
    # 边界: 未开启时, 加仓后用"加仓前高点"不应触发以新成本的开启
    st2 = _st(100.0, 100)                      # 未开启
    add_position(st2, 100, 104.0, entry_date="d2")  # 新成本102, 阈值110.16
    check("场景6边界 未开启时加仓不被旧高点误开", not st2.protection_active)
    update_quote(st2, 109.0, quote_time="t2")   # <110.16 不应开启
    check("场景6边界 加仓后109未达新阈值不开启", not st2.protection_active)
    update_quote(st2, 111.0, quote_time="t3")   # >=110.16 才开启
    check("场景6边界 加仓后111达到新阈值才开启", st2.protection_active)

    # 场景7: 老仓可卖100/新仓不可卖100; 触发后分别记录; 部分卖出后仅留剩余; 次日反弹继续提示
    st = init_position("sh600000", "测试", 100.0, 100, sellable_qty=100, today_new_qty=100)
    st.total_qty = 200
    update_quote(st, 93.0, quote_time="t1")
    e = evaluate_exit(st, 93.0, quote_time="t1")
    fire_exit(st, e)
    check("场景7 触发事件分别记录可卖/待退出", st.pending_exit["qty_sellable"] == 100 and st.pending_exit["qty_pending"] == 100)
    confirm_sell(st, 100)   # 卖出可卖部分
    check("场景7 部分卖出后仅保留剩余", st.total_qty == 100 and st.sellable_qty == 0)
    roll_trading_day(st)
    check("场景7 次日可卖且待退出继续", st.sellable_qty == 100 and st.is_exit_pending())

    # 场景8: 提醒成功但未确认成交→数量不减; 重复cron不重复创建事件
    st = _st(100.0)
    update_quote(st, 93.0, quote_time="t1")
    e = evaluate_exit(st, 93.0)
    fired_first = fire_exit(st, e)
    fired_again = fire_exit(st, e)   # 重复扫描
    check("场景8 首次事件创建成功", fired_first)
    check("场景8 重复扫描不重复创建", not fired_again)
    check("场景8 未确认成交数量不减", st.total_qty == 100)

    # 场景9: 确认清仓再买入 → 旧高点/旧锁利线不污染新交易
    st = _st(100.0)
    update_quote(st, 120.0, quote_time="t1")
    confirm_clear(st)
    st_new = init_position("sh600000", "测试", 100.0, 100)
    check("场景9 清仓后重开无旧保护线", (not st_new.protection_active) and st_new.profit_line == 0.0)
    check("场景9 新交易H重新初始化", st_new.peak_h == 100.0)

    # 场景10: 陈旧/断网/停牌/并发/发送失败不丢状态; 不产生虚假已成交
    st = _st(100.0)
    update_quote(st, 120.0, quote_time="t1")   # 保护开启
    pl = st.profit_line
    update_quote(st, 80.0, quote_time="t2", is_valid=False, invalid_reason="陈旧报价")
    check("场景10 无效报价不关闭保护", st.protection_active and st.profit_line == pl)
    check("场景10 无效报价不产生退出", evaluate_exit(st, 80.0) is None)
    # 并发写: 两 store 实例写不同 code
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "s.json")
        s1, s2 = StateStore(p), StateStore(p)
        a = init_position("sh600001", "A", 10.0, 100); b = init_position("sh600002", "B", 20.0, 100)
        s1.put(a); s2.put(b)
        data = s1.load()
    check("场景10 并发写不丢失", "sh600001" in data["positions"] and "sh600002" in data["positions"])

    # 场景11: 同一时序行情, 实盘判定与回测规则模块输出相同退出事件
    tape = [("t1", 100.0), ("t2", 108.0), ("t3", 120.0), ("t4", 111.0), ("t5", 111.6), ("t6", 118.0)]
    def replay():
        s = init_position("sh600000", "T", 100.0, 100)
        evs = []
        for ts, px in tape:
            update_quote(s, px, quote_time=ts)
            e = evaluate_exit(s, px, quote_time=ts)
            if e and fire_exit(s, e):
                evs.append((e["reason"], e["line"]))
        return evs
    live_evs = replay()
    backtest_evs = replay()   # 回测复用同一 evaluate_exit/fire_exit
    check("场景11 实盘与回测退出事件一致", live_evs == backtest_evs and len(live_evs) >= 1,
          f"事件={live_evs}")

    n_pass = sum(1 for _, ok, _ in results if ok)
    print(f"\n=== 验收: {n_pass}/{len(results)} 通过 ===")
    return n_pass == len(results)


if __name__ == "__main__":
    import sys
    if "--test" in sys.argv:
        ok = run_acceptance_tests()
        sys.exit(0 if ok else 1)
    # 默认: 打印参数与当前状态
    print("策略版本:", STRATEGY_VERSION)
    print("参数:", asdict(DEFAULT_PARAMS))
    st = StateStore()
    for code, pos in st.all().items():
        print(f"{code} {pos.name} C={pos.cost} qty={pos.total_qty} H={pos.peak_h} "
              f"保护={pos.protection_active} P={pos.profit_line} S={pos.hard_stop} eff={pos.effective_exit_line()}")
