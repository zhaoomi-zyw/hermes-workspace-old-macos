#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DCA 三只基金「当前状态快照」—— 每次都输出，不做变化判定。

与 monitor-dca-limits.py 的区别：
  · monitor-dca-limits.py = watchdog（只在状态变化时推，静默为主）
  · 本脚本 = 快照（每次运行都输出完整状态，用于特定日期确认「今天能不能投」）

用途：2026-09-21（周一）确认天弘 018043 是否仍暂停申购（→ 用户据此决定是否关闭定投）。
"""
import urllib.request
import re
import sys

FUNDS = {
    # 2026-09-22 变更（用户选 B）：国泰 9/28 起暂停 → 100 元挪到宝盈
    "019736": ("宝盈纳斯达克100指数发起(QDII)A", 200, "宝盈纳指100"),
    "160213": ("国泰纳斯达克100指数[9/28起暂停]", 0, "国泰纳指100"),
    "005698": ("华夏全球科技先锋混合(QDII)A", 150, "华夏全球科技"),
}


def fetch(code):
    url = f"https://fundf10.eastmoney.com/jjfl_{code}.html"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0"})
    try:
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        return (None, None, None, None, f"取数失败 {type(e).__name__}")
    txt = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    txt = re.sub(r"<[^>]+>", " ", txt).replace("&nbsp;", " ")
    txt = re.sub(r"\s+", " ", txt)
    sub = re.search(r"申购状态\s*(\S+?)\s*赎回状态\s*(\S+?)\s*定投状态\s*(\S+)", txt)
    buy, red, dca = (sub.group(1), sub.group(2), sub.group(3)) if sub else (None, None, None)
    lim = None
    m = re.search(r"日累计申购限额\s*([\d.]+)\s*元", txt)
    if m:
        lim = float(m.group(1))
    elif "无限额" in txt:
        lim = float("inf")
    return (buy, red, dca, lim, "")


def main():
    lines = ["💊 定投基金状态确认", ""]
    for code, (name, amt, note) in FUNDS.items():
        buy, red, dca, lim, err = fetch(code)
        if err:
            lines.append(f"● {name}（{code}）{note}")
            lines.append(f"   ⚠️ {err}")
            lines.append("")
            continue
        lim_s = "无限额" if lim == float("inf") else (f"{lim:.0f}元" if lim is not None else "?")
        # 结论
        if buy and "暂停" in buy:
            verdict = f"🔴 今天投不了（申购暂停）→ 建议关闭定投"
        elif dca and "不支持" in dca:
            verdict = "🔴 今天投不了（定投不支持）→ 建议关闭定投"
        elif lim is not None and lim != float("inf") and lim < amt:
            verdict = f"🔴 你的{amt}元超限额({lim_s}) → 会被拒"
        elif lim is not None and lim != float("inf") and lim == amt:
            verdict = f"🟠 可以投，但{amt}元正好卡在限额({lim_s})上"
        else:
            verdict = f"✅ 可以正常投 {amt} 元"

        lines.append(f"● {name}（{code}）{note}")
        lines.append(f"   申购={buy}｜赎回={red}｜定投={dca}｜日限额={lim_s}")
        lines.append(f"   你的定投额 {amt} 元/日 → {verdict}")
        lines.append("")
    lines.append(f"登记日定投合计 {sum(v[1] for v in FUNDS.values())} 元/日（宝盈100 + 国泰100 + 华夏150）")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
