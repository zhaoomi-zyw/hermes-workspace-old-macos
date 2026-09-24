#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据状态记录 (evidence-status) — v1 2026-09-24

━━━ 设计动机 ━━━
来自 DSA 论文 (arXiv:2608.26990) 的「证据感知」原则原文：
    "不可用的资金流证据不应变成中性的资金流信号"
（an unavailable capital-flow evidence should not become a neutral capital-flow signal）

本项目的原始缺陷（本次修复对象）：
  · stop-loss-watch.py  `except Exception: return  # 抓取失败静默`
    + `if not q: continue`
    → 持仓股取数失败时【完全静默，连日志都没有】。用户以为"没触发退出线"，
      实际是"根本没在监控" —— 风控链路的致命盲区。
      实例：2026-09-24 赤峰距退出线仅 0.01 元；若当日取数失败，用户无从知晓。
  · lowbuy-watch.py  有 skipped 记录但不推送 → 用户只能事后翻日志。

━━━ 状态词表（与论文对齐） ━━━
    available       正常取得
    fetch_failed    整批取数失败（网络/接口）
    missing         整批成功但该标的无返回
    stale           报价时间戳超新鲜度阈值
    invalid_price   价格 <= 0 或非法

━━━ 告警纪律（防抖，沿用 active-etf-watch.py 的分级思路） ━━━
    · 单次失败 → 静默（网络抖动是常态，不应打扰用户）
    · 连续 N 次失败 → 告警一次（去重，不重复刷屏）
    · 恢复 → 推送一次"已恢复"
    · 全程落盘，便于事后审计

━━━ 使用 ━━━
    import evidence_status as ES            # 与调用方同目录
    run = ES.Run(script="stop-loss-watch", now=now)
    run.add(code, name, ES.AVAILABLE)
    run.add(code, name, ES.MISSING, detail="腾讯未返回该代码")
    run.finish(critical_codes=[...])        # critical=风控相关, 缺失必须告警
    alert = run.alert_text()                # None = 无告警
"""
from __future__ import annotations

import json
import os
import datetime

STATE_FILE = os.path.expanduser("~/.hermes/state/evidence-status.json")

# ── 状态词表 ────────────────────────────────────────────────────────────
AVAILABLE = "available"
FETCH_FAILED = "fetch_failed"
MISSING = "missing"
STALE = "stale"
INVALID_PRICE = "invalid_price"

DEGRADED = (FETCH_FAILED, MISSING, STALE, INVALID_PRICE)

# 连续失败多少次才告警（防抖）
ALERT_AFTER_N = 3
# 低吸类监控：缺失比例超过此值视为"监控整体失效"（而非个别标的缺数据）
DEGRADED_RATIO_ALERT = 0.5


def _load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    return {}


def _save_state(d: dict) -> None:
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        tmp = STATE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=1)
        os.replace(tmp, STATE_FILE)
    except Exception:
        pass


class Run:
    """一次监控运行的证据记录。

    两种告警触发条件（二者任一）：
      A. critical 标的（如持仓股）出现任何非 available 状态 → 记一次失败
      B. 整体降级比例 >= DEGRADED_RATIO_ALERT → 记一次失败
    连续 ALERT_AFTER_N 次失败才真正告警。
    """

    def __init__(self, script: str, now: datetime.datetime = None,
                 expected_total: int = None):
        self.script = script
        self.now = now or datetime.datetime.now()
        self.expected_total = expected_total
        self.entries: list[dict] = []

    # ── 记录 ─────────────────────────────────────────────────────────
    def add(self, code: str, name: str, state: str, detail: str = "") -> None:
        self.entries.append({"code": code, "name": name,
                             "state": state, "detail": detail[:160]})

    def fail_batch(self, detail: str) -> None:
        """整批取数失败：无法逐只记录，用哨兵条目表示。"""
        self.entries.append({"code": "_BATCH_", "name": "(整批)", "state": FETCH_FAILED,
                             "detail": detail[:160]})

    # ── 统计 ─────────────────────────────────────────────────────────
    @property
    def degraded(self) -> list[dict]:
        return [e for e in self.entries if e["state"] in DEGRADED]

    @property
    def total(self) -> int:
        """分母一律 = 实际记录条数（entries）。

        ⚠️ 2026-09-24 修正：原实现返回 max(len(entries), expected_total)，
        但 degraded_ratio 却用 len(entries) —— 两者不一致会让"比例"失真。
        例：17 只中仅 5 只走到 add()（其余在 add 之前 continue，如持仓股），
        expected_total=18 会把分母撑大，让真实降级比例被稀释。
        现在统一以 entries 为准：只对"实际取证过"的标的计算降级比例。
        """
        return len(self.entries)

    @property
    def degraded_ratio(self) -> float:
        return (len(self.degraded) / len(self.entries)) if self.entries else 0.0

    def degraded_names(self, critical_codes=None) -> str:
        if critical_codes:
            hit = [e for e in self.degraded
                   if e["code"] in critical_codes or e["code"] == "_BATCH_"]
        else:
            hit = self.degraded
        return "、".join(f"{e['name']}({e['state']})" for e in hit) or "无"

    # ── 收尾 + 告警 ──────────────────────────────────────────────────
    def finish(self, critical_codes=None, critical: bool = False):
        """落盘并返回 (need_alert, alert_text, reason)。

        critical=True  → 只要 critical 标的降级就记失败（风控链路，严）
        critical=False → 仅当整体降级比例超阈值才记失败（研究链路，宽）
        """
        st = _load_state()
        rec = st.setdefault(self.script, {
            "consecutive_failures": 0, "alerted": False,
            "last_alert_at": None, "history": []})

        crit_deg = [e for e in self.degraded
                    if (e["code"] in (critical_codes or set())) or e["code"] == "_BATCH_"]
        if critical:
            is_fail = bool(crit_deg)
        else:
            is_fail = self.degraded_ratio >= DEGRADED_RATIO_ALERT and bool(self.degraded)

        if is_fail:
            rec["consecutive_failures"] = int(rec.get("consecutive_failures", 0)) + 1
            reason = (f"关键标的降级 {len(crit_deg)} 只" if critical
                      else f"降级比例 {self.degraded_ratio:.0%}")
        else:
            rec["consecutive_failures"] = 0
            reason = ""

        n = rec["consecutive_failures"]
        need_alert, text = False, None

        if is_fail and n >= ALERT_AFTER_N and not rec.get("alerted"):
            need_alert = True
            head = "🔴 监控取证异常" if critical else "🟠 监控取证降级"
            lines = [f"{head} · {self.script}",
                     f"连续 {n} 次未取得可用证据（{reason}）",
                     f"时间 {self.now:%Y-%m-%d %H:%M}"
                     f"｜正常 {len(self.entries) - len(self.degraded)}/{len(self.entries)}"]
            for e in self.degraded[:6]:
                lines.append(f"   · {e['name']}({e['code']}) = {e['state']}"
                             + (f" — {e['detail']}" if e["detail"] else ""))
            if critical:
                lines.append("")
                lines.append("⚠️ 风控链路取证失败 = 退出线监控当前【可能处于盲区】。")
                lines.append("   请人工确认持仓报价，不要假设‘没推送=没触发’。")
            else:
                lines.append("")
                lines.append("⚠️ 监控整体降级，本轮的‘无信号’可能只是取数失败。")
            text = "\n".join(lines)
            rec["alerted"] = True
            rec["last_alert_at"] = self.now.strftime("%Y-%m-%d %H:%M")

        if not is_fail and rec.get("alerted"):
            rec["alerted"] = False
            need_alert = True
            text = (f"✅ 监控取证已恢复 · {self.script}\n"
                    f"   {self.now:%Y-%m-%d %H:%M}｜正常 "
                    f"{len(self.entries) - len(self.degraded)}/{len(self.entries)}")

        # 历史（保留最近 40 条，避免无限增长）
        hist = rec.setdefault("history", [])
        hist.append({
            "at": self.now.strftime("%Y-%m-%d %H:%M:%S"),
            "total": len(self.entries),
            "degraded": len(self.degraded),
            "states": {s: sum(1 for e in self.entries if e["state"] == s)
                       for s in {e["state"] for e in self.entries}},
            "consecutive_failures": n,
        })
        rec["history"] = hist[-40:]
        rec["last_run_at"] = self.now.strftime("%Y-%m-%d %H:%M:%S")
        st[self.script] = rec
        _save_state(st)
        return need_alert, text, reason


def summary_for_log(run: "Run") -> str:
    """一行式摘要，便于写进既有日志文件。"""
    st = {}
    for e in run.entries:
        st[e["state"]] = st.get(e["state"], 0) + 1
    parts = [f"{k}={v}" for k, v in sorted(st.items())]
    return f"EVIDENCE total={len(run.entries)} " + " ".join(parts)
