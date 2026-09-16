#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
减仓提醒 (no_agent watchdog)
场景: 实盘仓位90.7%已超纪律上限(正常市<=75%), 赤峰单只占71.6%(>单股40%上限)。
逻辑: 持仓反弹到成本线上方时提醒减仓(按档位一次性提醒, 避免重复轰炸)。
档位: 成本线(回本) -> 建议减仓; +2% -> 强化; +3% -> 强化。
输出: 有触发才输出(stdout), 否则静默(空)。
"""
import os, json, datetime, urllib.request

# 持仓: 代码 -> (名称, 股数, 成本, 减仓方案)
# ⚠️ 只放「≥2手(200股)」的持仓 —— 1手(100股)无法真"减仓"(A股最小单位100股),
#    提醒只会变成"全清", 与风控减仓(部分了结/保留敞口)语义不符 → 已移除星网锐捷
#    1手持仓的退出完全交给策略止损线(如星网33.73), 不走减仓提醒
CODES = {
    # 2026-09-16 清空: 赤峰黄金已减至100股(1手) → 全组合3只均1手, "部分减仓"不可行
    # 1手持仓的退出完全交给 SELL-POLICY 止损线(赤峰42.26 / 星网33.73 / 沈飞41.77)
}
# 触发档位: (相对成本的百分比, 标签)
TIERS = [(0.0, "回本"), (2.0, "+2%"), (3.0, "+3%")]

STATE_FILE = os.path.expanduser("~/.hermes/state/reduce-position-watch.json")


def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"fired": {}}


def save_state(st):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(st, f, ensure_ascii=False)


def in_trading_hours(now):
    if now.weekday() >= 5:
        return False
    hm = now.hour * 100 + now.minute
    return (930 <= hm <= 1130) or (1300 <= hm <= 1500)


def calendar_ok():
    """交易日日历门控: 无法判断时放行(不因日历故障漏报)"""
    try:
        import cn_trading_calendar as cal
        st = cal.calendar_status(datetime.date.today())
        s = str(st).upper()
        if "PAUSED" in s or "UNKNOWN" in s:
            return False
    except Exception:
        pass
    return True


def fetch_prices(codes):
    url = "http://qt.gtimg.cn/q=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"Referer": "http://finance.qq.com"})
    raw = urllib.request.urlopen(req, timeout=10).read().decode("gbk")
    out = {}
    for line in raw.strip().split("\n"):
        if '="' not in line:
            continue
        key = line.split("=")[0].replace("v_", "").strip()
        f = line.split('="')[1].split("~")
        if len(f) < 33:
            continue
        try:
            out[key] = {"name": f[1], "price": float(f[3]), "pct": float(f[32])}
        except Exception:
            continue
    return out


def main():
    now = datetime.datetime.now()
    if not in_trading_hours(now) or not calendar_ok():
        return
    today = now.strftime("%Y-%m-%d")
    st = load_state()
    fired = st.get("fired", {})
    if fired.get("_date") != today:
        fired = {"_date": today}

    quotes = fetch_prices(list(CODES.keys()))
    msgs = []
    for code, (name, shares, cost, plan) in CODES.items():
        q = quotes.get(code)
        if not q:
            continue
        price = q["price"]
        gain_pct = (price / cost - 1) * 100
        for thr, label in TIERS:
            key = f"{code}@{thr}"
            if gain_pct >= thr and key not in fired:
                fired[key] = True
                tag = "回到成本" if thr == 0 else f"浮盈{label}"
                msgs.append(
                    f"🔔 减仓提醒：{name} {price:.2f}（{tag}，成本{cost}）\n"
                    f"   建议：{plan}\n"
                    f"   理由：当前仓位90.7%已超纪律上限（正常市≤75%），赤峰单只占71.6%（>单股40%）"
                )

    st["fired"] = fired
    save_state(st)
    if msgs:
        print("📉 减仓提醒（降集中度）")
        print("\n".join(msgs))


if __name__ == "__main__":
    main()
