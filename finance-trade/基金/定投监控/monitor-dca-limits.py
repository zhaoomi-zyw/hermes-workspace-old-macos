#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DCA 基金申购限额监控（实际持仓口径，2026-09-18 校准）

以用户支付宝「我的定投」截图为准（2026-09-18 19:07 截图）：
  018043 天弘纳斯达克100指数(QDII)A      日定投 100 元
  005698 华夏全球科技先锋混合(QDII)A     日定投 150 元
  019736 宝盈纳斯达克100指数发起(QDII)A  日定投 200 元
  合计 450 元/日，均自 2026-09-21 起从建设银行储蓄卡(8564)扣款

⚠️ 旧版盯的是 005698 + 022979（022979 已不在"进行中"列表，可能属"已暂停(3)"）。
   本版以实际在投的 3 只为准。

规则：
  - 限额 < 日定投额          → 🔴 会被拒（扣款失败）
  - 限额 == 日定投额         → 🟠 卡在上限（一旦下调即失败）
  - 暂停申购 / 不支持定投     → 🔴 立即失败
  - 限额未变                 → 静默（watchdog 模式）
"""
import urllib.request
import re
import json
import os
import sys
from datetime import datetime

FUNDS = {
    "018043": {"name": "天弘纳斯达克100指数(QDII)A",  "dca": 100},
    "005698": {"name": "华夏全球科技先锋混合(QDII)A", "dca": 150},
    "019736": {"name": "宝盈纳斯达克100指数发起(QDII)A", "dca": 200},
}

STATE_FILE = os.path.expanduser("~/.hermes/profiles/main/cron/state/dca_fund_limits.json")


def fetch_status(code):
    """返回 (申购状态, 赎回状态, 定投状态, 日限额元/None)。"""
    url = f"https://fundf10.eastmoney.com/jjfl_{code}.html"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0"})
    try:
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        return (None, None, None, None)
    txt = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt)
    txt = txt.replace("&nbsp;", " ")
    txt = re.sub(r"\s+", " ", txt)

    sub = re.search(r"申购状态\s*(\S+?)\s*赎回状态\s*(\S+?)\s*定投状态\s*(\S+)", txt)
    buy, red, dca = (sub.group(1), sub.group(2), sub.group(3)) if sub else (None, None, None)

    lim = None
    m = re.search(r"日累计申购限额\s*([\d.]+)\s*元", txt)
    if m:
        lim = float(m.group(1))
    elif "无限额" in txt:
        lim = float("inf")
    return (buy, red, dca, lim)


def main():
    try:
        state = json.load(open(STATE_FILE, encoding="utf-8"))
    except Exception:
        state = {}

    alerts, silent = [], []
    for code, info in FUNDS.items():
        buy, red, dca, lim = fetch_status(code)
        prev = state.get(code, {})
        if not isinstance(prev, dict):   # 兼容旧版 state（裸数字格式）
            prev = {}
        cur = {"buy": buy, "dca": dca, "limit": lim,
               "last_checked": datetime.now().isoformat()}

        if buy is None:
            state[code] = cur
            silent.append(f"{info['name']}: 取数失败")
            continue

        dca_amt = info["dca"]
        problems = []

        if buy and "暂停" in buy:
            problems.append(f"🔴 申购已暂停 → {dca_amt}元/日定投会被拒")
        if dca and "不支持" in dca:
            problems.append("🔴 定投状态=不支持")
        if lim is not None and lim != float("inf"):
            if lim < dca_amt:
                problems.append(f"🔴 日限额{lim:.0f}元 < 你的{dca_amt}元 → 会被拒")
            elif lim == dca_amt:
                problems.append(f"🟠 日限额{lim:.0f}元 = 你的{dca_amt}元（卡上限，一旦下调即失败）")

        # ⭐ 按「问题指纹」去重：同一问题只推一次；问题消失后再出现则重新推。
        #    （旧版按"限额数字变化"去重 → 暂停申购时数字仍是100 → 永远静默，是本次漏报的根因）
        fingerprint = "|".join(sorted(problems)) if problems else "OK"
        prev_fp = prev.get("fp")
        changed = (prev.get("buy") != buy) or (prev.get("dca") != dca) or (prev.get("limit") != lim)
        cur["fp"] = fingerprint
        state[code] = cur

        if problems and fingerprint != prev_fp:
            head = "状态变化" if (prev and changed) else "检测到问题"
            alerts.append(f"● {info['name']}（{code}）{head}\n"
                          f"   申购={buy}｜赎回={red}｜定投={dca}｜日限额={lim}\n"
                          f"   你的定投 {dca_amt} 元/日\n"
                          + "\n".join("   " + p for p in problems))
        elif not problems and prev_fp not in (None, "OK"):
            alerts.append(f"● {info['name']}（{code}）✅ 问题已解除\n"
                          f"   申购={buy}｜定投={dca}｜日限额={lim}\n"
                          f"   你的定投 {dca_amt} 元/日 可正常投")

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    if alerts:
        print("💊 定投基金限额监控\n")
        print("\n\n".join(alerts))
        print("\n合计日定投 450 元（天弘100 + 华夏全球科技150 + 宝盈200）")


if __name__ == "__main__":
    main()
