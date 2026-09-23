#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""低吸【全量扫描·诊断口径】—— 逐只输出"卡在哪一条"（不只报合格名单）

用途：线上 lowbuy-watch.py 只推送"6 条全满足"的标的；本脚本额外给出每只卡在哪一条，
     便于人工判断"接近满足"的标的。

⭐⭐ 2026-09-23 重大对齐（本文件的核心设计原则）
   本脚本**不再自行实现任何判定逻辑**，而是：
     ① 从 lowbuy-watch.py（线上权威）导入 WATCHLIST —— 名单单一来源，不再各自维护
     ② 直接调用其 eval_one() 做 6 条门槛判定 —— 门槛/阈值/版本号自动同源
   历史教训：此前本脚本自己实现"3 条门槛 + ③阈值 0.80"，而线上是
   "6 条门槛（①②③⑤⑥+弱市）+ ③阈值 0.70"，导致：
     · 南山铝业 本脚本报 ✅✅✅，线上实际卡⑤（个股 −1.25% < 沪深300 −0.16%）不推
     · 云南铜业 本脚本③报✅(0.89<0.80)，线上因 0.89>0.70 判③❌
   ⇒ 诊断工具与线上口径不一致，比"监控失聪"更隐蔽 —— 它会持续给人错误答案。
   现在：线上收紧阈值，本脚本自动跟上，不会再漂移。

⚠️ ③缩量的 as-of 语义
   same_time_vol_ratio(min5, now) 基准时点取 `now`：盘中=真同刻；盘后双双退化为全天口径。
   （实证 云南铜业 2026-09-23：同刻 11:30=0.967❌ vs 全天=0.659✅，结论相反）
   本脚本盘中/盘后均直接沿用 eval_one 的同刻口径（盘后时 watch 自身也会给出 reason），
   不再另列"全天口径"，避免再次制造第二套口径。

⚠️ 本脚本是【条件显示工具】：有意不过滤持仓 —— 持仓股会照常显示，但行尾标注
   「⚠️持仓·不加仓」（线上会跳过它）。请勿把本脚本的"全满足"直接当成"会推送"。
"""
import os
import sys
import json
import datetime
import urllib.request
import importlib.util

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
WATCH_SCRIPT = os.path.join(SCRIPTS_DIR, "lowbuy-watch.py")
sys.path.insert(0, "/Users/omi/workspace/quant-backtest/strategies")
import buy_policy as BP  # noqa: E402


def load_watch():
    """加载线上 lowbuy-watch.py（文件名含连字符 → 必须用 importlib）。
    ⚠️ 只加载模块，绝不调用其 main()。"""
    spec = importlib.util.spec_from_file_location("lowbuy_watch_src", WATCH_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_holdings():
    """读当前持仓（sell-policy-state 权威）→ 用于标注「持仓股不加仓」"""
    try:
        p = os.path.expanduser("~/.hermes/state/sell-policy-state.json")
        sp = json.load(open(p, encoding="utf-8"))
        return {c: (v.get("name"), v.get("total_qty"))
                for c, v in (sp.get("positions") or {}).items()}
    except Exception:
        return {}


# 卡点解析：把 eval_one 的 reason 归类到门槛编号，便于按列展示
GATE_MARK = [("⑥", "⑥跳空"), ("①", "①趋势"), ("②", "②ATR回调"),
             ("③", "③同刻缩量"), ("⑤", "⑤相对强度"), ("弱市", "弱市条件")]


def gate_of(reason):
    """从 reason 文本提取卡住的门槛标记。返回 (mark, 简短说明)。"""
    if not reason:
        return ("", "")
    for mk, label in GATE_MARK:
        if reason.startswith(mk) or mk in reason[:6]:
            return (mk, label)
    return ("?", reason[:40])


def main():
    now = datetime.datetime.now()
    try:
        W = load_watch()
    except Exception as e:
        print(f"[扫描失败] 无法加载线上脚本 {WATCH_SCRIPT}: {type(e).__name__}: {e}")
        return
    WATCHLIST = W.WATCHLIST
    in_sess = W.BP.in_session(W.BP.now_hhmm(now))

    lines = [f"📊 低吸全量扫描【诊断口径·与线上同源】  {now:%Y-%m-%d %H:%M}",
             f"线上策略 {W.POLICY_VERSION}（base {W.POLICY_VERSION_BASE}）"
             f"｜时段内 {'✅' if in_sess else '⚠️否（结论仅供参考）'}",
             f"名单来源 lowbuy-watch.py ｜ 范围 {len(WATCHLIST)} 只"
             f"｜门槛 {len(GATE_MARK)} 条（①②③⑤⑥+弱市）",
             ""]

    # 加载沪深300基准（⑤相对强度需要）；线上 cron 自带缓存，这里手工灌入
    try:
        bench = W.fetch_day_kline(W.BENCH_CODE)
        W._BENCH_CACHE["rows"] = bench
        bench_note = f"基准 {W.BENCH_CODE} {len(bench)} 根（最新 {bench[-1]['date']}）"
    except Exception as e:
        bench_note = f"⚠️ 基准获取失败（⑤将判「无法确认」）: {str(e)[:50]}"
    lines.append(bench_note)
    lines.append("")

    try:
        rt = W.fetch_realtime(list(WATCHLIST.keys()))
    except Exception as e:
        print(f"[扫描失败] 行情抓取异常 {type(e).__name__}: {e}")
        return
    if not rt:
        print("[扫描失败] 行情为空")
        return

    HELD = _load_holdings()
    rows, hits = [], []
    for code, name in WATCHLIST.items():
        q = rt.get(code)
        if not q:
            rows.append((name, None, None, "", "无行情"))
            continue
        try:
            cand, reason = W.eval_one(code, name, q, now.strftime("%Y-%m-%d"), now)
        except Exception as e:
            rows.append((name, q.get("price"), None, "!", f"计算异常 {type(e).__name__}: {str(e)[:60]}"))
            continue
        held = code in HELD
        if cand:
            tag = "无(全满足)"
            if held:
                tag += "  ⚠️持仓·不加仓"
            rows.append((name, q.get("price"), cand, "🎯", tag))
            if not held:
                hits.append((name, code, cand))
        else:
            mk, label = gate_of(reason)
            tag = f"{label} ｜ {str(reason)[:70]}"
            if held:
                tag += "  ⚠️持仓·不加仓"
            rows.append((name, q.get("price"), None, mk, tag))

    lines.append("逐只明细（判定＝线上 lowbuy-watch.py 的 6 条门槛，非本脚本自算）")
    lines.append("名称         现价   卡点   说明")
    lines.append("-" * 100)
    order = {"🎯": 0, "⑥": 1, "①": 2, "②": 3, "③": 4, "⑤": 5, "落市": 6, "弱市": 6}
    rows.sort(key=lambda r: (order.get(r[3], 9), r[0]))
    for name, price, cand, mk, tag in rows:
        ptxt = f"{price:.2f}" if isinstance(price, (int, float)) else "-"
        lines.append("{:<11}{:>8}   {:<3}   {}".format(name, ptxt, mk, tag))

    lines.append("")
    if hits:
        lines.append("🎯 6 条门槛全满足（线上会推送；仍受 pending/当日去重/持仓豁免约束）：")
        for name, code, c in hits:
            lines.append(f"  {name}({code[2:]}) 现价 {c['price']:.2f}")
            lines.append(f"    ①价>MA60 {c['ma60']:.2f} ✓  ②偏离 {c['dev']:.2f} ✓  ③量比 {c['vol_ratio']:.2f} ✓")
            lines.append(f"    ⑤相对强度 {c['rs20'] * 100:+.2f}%"
                         f"（个股 {c['stock_ret20'] * 100:+.2f}% vs 沪深300 {c['bench_ret20'] * 100:+.2f}%）")
            lines.append(f"    参考限价区间 {c['lo']:.2f} ~ {c['hi']:.2f}")
        lines.append("")
    else:
        lines.append("🎯 6 条门槛全满足：无")
        near = [r for r in rows if r[3] in ("③", "⑤")]
        if near:
            lines.append("")
            lines.append("⚠️ 接近满足（只差 ③缩量 或 ⑤相对强度 一项）：")
            for r in near:
                lines.append(f"  {r[0]}  只差 {r[3]}")

    lines.append("")
    lines.append("⚠️ 本扫描为条件显示，非买入建议；数量由你自行决定。")
    lines.append("⚠️ 本工具【有意不过滤持仓】；线上会跳过持仓股 —— 产物勿直接当作推送预览。")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
