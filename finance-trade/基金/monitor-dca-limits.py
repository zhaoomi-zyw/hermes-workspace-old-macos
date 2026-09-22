#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""DCA 基金申购限额监控（实际持仓口径，2026-09-18 校准）

以用户支付宝「我的定投」截图为准（2026-09-18 19:07 截图）：
  2026-09-22 现行：019736 宝盈 200 + 005698 华夏 150 = 350 元/日
  （160213 国泰 100 已于 2026-09-22 公告、9/28 起暂停申购+定投 → 挪至宝盈）

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
    # ⭐ 2026-09-22 变更（用户选 B）：国泰 160213 公告 9/28 起暂停申购+定投
    #    （9/24 15:00 后申请即适用）→ 用户决定把 100 元挪到宝盈
    #    宝盈上限 200，挪后 = 200 → ⚠️ 卡满上限
    #    国泰保留监控（dca 标 0），恢复后由用户改回
    "019736": {"name": "宝盈纳斯达克100指数发起(QDII)A", "dca": 200},
    "160213": {"name": "国泰纳斯达克100指数[9/28起暂停]", "dca": 0},
    "005698": {"name": "华夏全球科技先锋混合(QDII)A", "dca": 150},
}

STATE_FILE = os.path.expanduser("~/.hermes/profiles/main/cron/state/dca_fund_limits.json")


# ============ 公告监控（2026-09-22 新增，用户批准）============
# 背景：国泰 160213 于 2026-09-22 07:40 发布「暂停申购、定期定额投资」公告，
#       但「交易状态」字段要到 9/28 才变 → 只查状态字段会漏报 6 天。
#       本模块直接查公告栏 + 抓 PDF 正文的「暂停起始日」，实现前瞻预警。
ANN_KEYWORDS = ["暂停申购", "暂停定期定额", "暂停大额申购", "限制大额",
                "暂停转换", "恢复申购", "恢复定期定额", "暂停赎回"]
ANN_RECENT_DAYS = 30          # 只关注最近 N 天发布的公告（避免历史公告刷屏）


def _clean(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s)).strip()


def fetch_announcements(code):
    """抓基金详情页公告栏 → [(mmdd, title, url)]，只返回含关键词的。"""
    url = f"https://fund.eastmoney.com/{code}.html"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0",
        "Referer": "https://fund.eastmoney.com/"})
    try:
        html = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
    except Exception:
        return []
    out = []
    for row in re.findall(r"<tr[\s\S]{0,1200}?</tr>", html):
        txt = _clean(row)
        if len(txt) < 15 or "公告" not in txt:
            continue
        if not any(k in txt for k in ["暂停", "恢复", "限额", "定期定额", "申购"]):
            continue
        ds = re.findall(r"(\d{2}-\d{2})", row)
        lk = re.search(r'href="([^"]*news[^"]*)"', row)
        title = re.sub(r"^\s*\d+\s+\d+\s+公告\s*", "", txt)
        title = re.sub(r"基金资讯.*$", "", title).strip()
        if not any(k in title for k in ANN_KEYWORDS):
            continue
        out.append((ds[0] if ds else None, title[:130], lk.group(1) if lk else None))
    return out


def extract_effective_date(url):
    """从公告正文抓 暂停/恢复 起始日。返回 dict。"""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0",
            "Referer": "https://fund.eastmoney.com/"})
        raw = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
    except Exception:
        return {}
    txt = _clean(raw.replace("&nbsp;", " "))
    txt = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", txt)
    res = {}
    pats = [
        ("暂停申购起始日", r"暂停申购业务起始日\s*(20\d\d\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)"),
        ("暂停定投起始日", r"暂停定期定额投资业务起始日\s*(20\d\d\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)"),
        ("最后可投时点", r"如投资者于(20\d\d\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*\d{1,2}\s*点)"),
        ("公告送出日期", r"公告送出日期[：:]\s*(20\d\d\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)"),
        ("恢复起始日", r"自\s*(20\d\d\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日)\s*起恢复"),
    ]
    for label, pat in pats:
        m = re.search(pat, txt)
        if m:
            res[label] = re.sub(r"\s+", "", m.group(1))
    return res


def check_announcements(code, info, prev):
    """检查公告 → (告警文本 or None, 新指纹)。"""
    anns = fetch_announcements(code)
    if not anns:
        return None, prev.get("ann_fp")
    now_md = datetime.now()
    today = now_md.date()
    fresh = []
    for mmdd, title, url in anns:
        if not mmdd:
            continue
        try:
            mo, dy = int(mmdd[:2]), int(mmdd[3:])
            d = datetime(now_md.year, mo, dy).date()
            if (today - d).days > ANN_RECENT_DAYS:
                continue
        except Exception:
            continue
        fresh.append((mmdd, title, url))
    if not fresh:
        return None, prev.get("ann_fp")

    fp = "|".join(sorted(f"{a[0]}::{a[1][:40]}" for a in fresh))
    if fp == prev.get("ann_fp"):
        return None, fp          # 已推过 → 静默

    lines = []
    for mmdd, title, url in fresh[:2]:
        lines.append(f"   📢 [{mmdd}] {title}")
        if url:
            eff = extract_effective_date(url)
            for k, v in eff.items():
                lines.append(f"        ★ {k} = {v}")
    dca_amt = info["dca"]
    if dca_amt > 0:
        lines.append(f"   ⚠️ 你的定投 {dca_amt} 元/日 → 请提前安排（暂停后申请会被拒）")
    else:
        lines.append("   ℹ️ 该基金当前不在你的定投计划中（dca=0），仅作监控")
    return "\n".join(lines), fp


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
    if not sub:  # 部分老基金（如LOF）页面结构不同
        sub = re.search(r"申购状态\s*(\S+?)\s*(?:赎回状态|定投状态)\s*(\S+?)\s*定投状态\s*(\S+)", txt)
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
        # ⭐ 公告监控（独立于状态字段，提前预警）
        ann_msg, ann_fp = check_announcements(code, info, prev)
        cur["ann_fp"] = ann_fp

        fingerprint = "|".join(sorted(problems)) if problems else "OK"
        prev_fp = prev.get("fp")
        changed = (prev.get("buy") != buy) or (prev.get("dca") != dca) or (prev.get("limit") != lim)
        cur["fp"] = fingerprint
        state[code] = cur

        if problems and fingerprint != prev_fp:
            head = "状态变化" if (prev and changed) else "检测到问题"
            block = (f"● {info['name']}（{code}）{head}\n"
                     f"   申购={buy}｜赎回={red}｜定投={dca}｜日限额={lim}\n"
                     f"   你的定投 {dca_amt} 元/日\n"
                     + "\n".join("   " + p for p in problems))
            if ann_msg:
                block += "\n" + ann_msg
            alerts.append(block)
        elif ann_msg:
            # 状态字段还没变，但公告已出 → 单独预警（这正是本次漏报的场景）
            alerts.append(f"● {info['name']}（{code}）📢 公告预警（状态字段尚未更新）\n"
                          f"   当前：申购={buy}｜定投={dca}｜日限额={lim}\n"
                          + ann_msg)
        elif not problems and prev_fp not in (None, "OK"):
            alerts.append(f"● {info['name']}（{code}）✅ 问题已解除\n"
                          f"   申购={buy}｜定投={dca}｜日限额={lim}\n"
                          f"   你的定投 {dca_amt} 元/日 可正常投")

    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    json.dump(state, open(STATE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    if alerts:
        print("💊 定投基金限额监控\n")
        print("\n\n".join(alerts))
        acts = " + ".join(f"{v['name'].split('(')[0][:8]}{v['dca']}" for v in FUNDS.values())
        print(f"\n登记日定投合计 {sum(v['dca'] for v in FUNDS.values())} 元/日（{acts}）")


if __name__ == "__main__":
    main()
