#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""首批「主动管理 ETF」发行/募集监控（watchdog）· 同花顺数据源版

── 2026-09-21 换源重写 ───────────────────────────────────────────
【为什么换】原版直连东财 push2delay 全量拉 1,614 只 ETF 再按名称筛「主动」，存在三个问题：
   ① 东财 push2* 行情域对本机 IP 已限流（全部 HTTP 000）
   ② 单页上限 100，脚本传 200 → 长期只拉到 800/1614 只（漏一半）
   ③ 笨办法：为了筛几只主动ETF 要拉全市场，请求量大、易触发风控

【新方案 · 同花顺 hithink-finance CLI】
   `fund offerings --subscribe active`   → 在募基金
   `fund offerings --subscribe upcoming` → 即将募集
   `symbol search --q <code>`            → 代码 → 名称
   优点：① 主动ETF 一开始【募集】就会出现（比"上市后"更早预警）
        ② 请求量小（2~n 次），不触发风控
        ③ 走官方 CLI，稳定

【识别规则】沪深交易所业务指引（2026-06-17 起施行）明确要求：
   **主动管理 ETF 的命名需明确标注「主动管理」**
   → 因此筛「名称含 主动」即可（与 18 只上报名单的命名格式一致：
     「易方达品质未来主动管理ETF」「华夏质量价值甄选主动管理ETF」…）

【监控语义 · no_agent watchdog】
   · 首次运行 → 建立基线并输出一次状态
   · 无新增 → 完全静默（空 stdout = 不推送）
   · 出现「含主动」的新代码 → 🚨 推送
   · 出现其他新场内代码 → 记录但不推送（降噪）
   · 连续取数失败 ≥3 次 → 推送一条告警（单次失败静默，exit 0）
"""
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

STATE_FILE = os.path.expanduser("~/.hermes/profiles/main/cron/state/active_etf_watch.json")
# ⚠️ cron 的 PATH 可能不含 npm-global/bin → 用绝对路径兜底
CLI = shutil.which("hithink-finance") or "/Users/omi/.npm-global/bin/hithink-finance"
CLI_TIMEOUT = 60            # 单次 CLI 调用超时（秒）
FAIL_ALERT_THRESHOLD = 3    # 连续失败多少次才告警
MAX_NAME_LOOKUPS = 40       # 单次运行最多查多少个新代码的名称（控制请求量）
KEYWORDS = ("主动",)        # 名称命中即告警


# ⚠️ cron 环境可能没有 PATH（干净 env）→ 显式构造，否则 CLI 找不到 node
_NODE = shutil.which("node") or "/usr/local/bin/node"
_ENV = dict(os.environ)
_PATH_DIRS = [os.path.dirname(_NODE), os.path.dirname(CLI),
              "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin",
              os.path.expanduser("~/.npm-global/bin"), "/opt/homebrew/bin"]
_ENV["PATH"] = ":".join(d for i, d in enumerate(_PATH_DIRS) if d and d not in _PATH_DIRS[:i])


def run_cli(args, timeout=CLI_TIMEOUT):
    """执行 hithink-finance，返回 (ok, data_dict_or_None, raw_text)"""
    try:
        p = subprocess.run([CLI] + args, capture_output=True, text=True,
                           timeout=timeout, env=_ENV)
        out = (p.stdout or "").strip()
        if not out:
            return False, None, (p.stderr or "")[:300]
        d = json.loads(out)
        if d.get("ok"):
            return True, d.get("data") or {}, out
        return False, None, json.dumps(d.get("error") or {}, ensure_ascii=False)[:300]
    except subprocess.TimeoutExpired:
        return False, None, "CLI timeout"
    except Exception as e:
        return False, None, f"{type(e).__name__}: {e}"[:300]


def fetch_offerings():
    """返回 (items, err)。items = [{thscode,ticker,status,start_ms,end_ms}]"""
    items = []
    errs = []
    for st in ("active", "upcoming"):
        ok, data, raw = run_cli(["fund", "offerings", "--subscribe", st,
                                 "--format", "json", "--source", "remote"])
        if not ok:
            errs.append(f"{st}: {raw}")
            continue
        for x in (data.get("item") or []):
            x = dict(x)
            x["_status"] = st
            items.append(x)
        time.sleep(0.5)
    return items, errs


def is_onsite(code):
    """场内代码（可在交易所交易）"""
    return str(code or "").endswith((".SH", ".SZ"))


def lookup_name(code):
    """代码 → 名称（走 symbol search）"""
    ok, data, raw = run_cli(["symbol", "search", "--q", str(code).split(".")[0],
                             "--format", "json", "--source", "remote"])
    if not ok:
        return None
    for x in (data.get("item") or []):
        if x.get("thscode") == code:
            return x.get("name")
    it = data.get("item") or []
    return it[0].get("name") if it else None


def load_state():
    try:
        return json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:
        return {}


def save_state(st):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    json.dump(st, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    os.replace(tmp, STATE_FILE)


def main():
    prev = load_state()
    items, errs = fetch_offerings()

    # ---------- 取数失败 ----------
    if not items:
        fails = int(prev.get("consecutive_failures") or 0) + 1
        prev["consecutive_failures"] = fails
        prev["last_failure"] = datetime.now().isoformat()
        prev["last_failure_detail"] = "; ".join(errs)[:400]
        save_state(prev)
        if fails >= FAIL_ALERT_THRESHOLD:
            print(f"⚠️ 主动ETF监控：连续 {fails} 次取数失败")
            print(f"   上次成功：{prev.get('last_checked') or '从未'}")
            print(f"   错误：{'; '.join(errs)[:300]}")
            print("   → 排查：hithink-finance doctor / auth status")
            print("   → 手工复现：hithink-finance fund offerings --subscribe active --format json --source remote")
            sys.exit(0)
        sys.exit(0)   # 单次失败静默

    # ---------- 取数成功 ----------
    onsite = {}
    for x in items:
        c = x.get("thscode")
        if is_onsite(c):
            onsite[c] = {"ticker": x.get("ticker"), "status": x.get("_status"),
                         "start_ms": x.get("subscription_start_ms"),
                         "end_ms": x.get("subscription_end_ms")}

    prev_codes = set(prev.get("onsite_codes") or [])
    cur_codes = set(onsite)
    new_codes = cur_codes - prev_codes

    # 只对「新增代码」查名称（控制请求量）
    names = dict(prev.get("onsite_names") or {})
    to_lookup = sorted(new_codes)[:MAX_NAME_LOOKUPS]
    for c in to_lookup:
        nm = lookup_name(c)
        if nm:
            names[c] = nm
        time.sleep(0.6)

    active_hits = [(c, names.get(c) or "?") for c in cur_codes
                   if any(k in (names.get(c) or "") for k in KEYWORDS)]

    state = {
        "source": "hithink-finance fund offerings",
        "onsite_codes": sorted(cur_codes),
        "onsite_names": names,
        "offerings_total": len(items),
        "onsite_total": len(onsite),
        "active_etf_codes": sorted(c for c, _ in active_hits),
        "active_etf_names": sorted(nm for _, nm in active_hits),
        "last_checked": datetime.now().isoformat(),
        "consecutive_failures": 0,
    }
    save_state(state)

    first_run = not prev.get("onsite_codes")

    if first_run:
        print("📡 主动管理ETF 募集监控 · 基线建立（同花顺数据源）")
        print(f"   在募/即将募集基金 {len(items)} 只，其中场内代码 {len(onsite)} 只")
        print(f"   名称含「主动」：{len(active_hits)} 只" +
              ("（尚未启动募集 ✓ 与预期一致）" if not active_hits else ""))
        if active_hits:
            print("   ⚠️ 已出现：")
            for c, nm in active_hits:
                print(f"      {c}  {nm}")
        return

    # ---------- 变化检测 ----------
    new_active = [(c, names.get(c) or "?") for c, nm in active_hits if c in new_codes]

    if new_active:
        print("🚨 主动管理ETF 出现新品种！")
        for c, nm in new_active:
            info = onsite.get(c, {})
            st = "募集在售" if info.get("status") == "active" else "即将募集"
            print(f"   ● {c}  {nm}")
            print(f"     状态：{st}")
            if info.get("start_ms"):
                print(f"     募集开始：{datetime.fromtimestamp(info['start_ms']/1000):%Y-%m-%d}")
        print("\n   → 券商 App 搜索该代码确认可交易性")
        print("   → 对比模板：Obsidian 04-Trading/主动管理ETF-18只对比模板.md")
    else:
        # 无新增主动ETF：仅当场内新增数量异常（≥5，可能预示批次上市）时提示
        if len(new_codes) >= 5:
            print(f"📈 场内基金新增 {len(new_codes)} 只（在募/待募）")
            print(f"   主动管理ETF 仍为 {len(active_hits)} 只")
            for c in sorted(new_codes)[:10]:
                print(f"      {c}  {names.get(c) or '?'}")
        # 否则完全静默


if __name__ == "__main__":
    main()
