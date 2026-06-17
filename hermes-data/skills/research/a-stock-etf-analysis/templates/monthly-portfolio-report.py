#!/usr/bin/env python3
"""
Monthly Portfolio Report — generic template.

Customise the FUND config block for the user's holdings, then set up as a
no_agent=True cron job on the last few weekdays of each month.

Schedule example (cron): 30 20 26-31 * 1-5
Delivery: weixin, telegram, or origin

The script:
  1. Checks whether today is the last trading day of the month
  2. Fetches latest NAV via eastmoney fundgz API for each fund
  3. Compares against previous month-end NAV (stored in JSON state file)
  4. Outputs a formatted report with profit/loss per fund and grand total

Customisation points (search for "CUSTOMISE" in this file):
  - CASH_POOL: dict of code → {name, amount_in_yuan}
  - DCA_FUNDS: dict of code → {name, daily_amount}
  - STATE_DIR: where the month-over-month NAV state file lives
  - CASH_POOL_START: date string for baseline (when cash pool was first deployed)
  - DCA_START_INVESTED: cumulative yuan invested as of baseline date
  - is_last_trading_day() logic: adjust if the user's exchange has a different
    holiday calendar

Requirements:
  - Python 3.7+ with `requests`
  - Network access to fund.eastmoney.com
  - Cron runner's working directory should be the user's home or a project dir

See `references/short-debt-cash-pool-allocation.md` in the a-stock-etf-analysis
skill for the fund-selection framework that produces the cash pool choices.

— Created 2026-06-15 from a session with Omi (35万 华富恒稳纯债D + 长城短债D)
"""

import requests, re, json, os, time
from datetime import datetime, date, timedelta

# ── CUSTOMISE: Fund config ─────────────────────────
CASH_POOL = {
    # "code": {"name": "Display name", "amount": total_yuan_invested},
    "020080": {"name": "华富恒稳纯债D",   "amount": 200000},
    "019872": {"name": "长城短债D",        "amount": 150000},
}

DCA_FUNDS = {
    # "code": {"name": "Display name", "daily": yuan_per_trading_day},
    "005698": {"name": "华夏全球科技先锋QDII A", "daily": 150},
    "022979": {"name": "华夏中证A500ETF联接A",   "daily": 150},
}

# ── CUSTOMISE: Baseline dates and initial values ───
CASH_POOL_START = "2026-06-18"       # date cash pool was first deployed
# Cumulative yuan invested in each DCA fund as of CASH_POOL_START
DCA_START_INVESTED = {
    "005698": 1150,
    "022979": 650,
}

# ── CUSTOMISE: State directory ──────────────────────
STATE_DIR = os.path.expanduser("~/.hermes/profiles/main/cron/state")
STATE_FILE = os.path.join(STATE_DIR, "monthly_portfolio.json")

# ── Helpers ─────────────────────────────────────────

def fetch_nav(code, retries=3):
    url = f"https://fundgz.1234567.com.cn/js/{code}.js"
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=10, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://fund.eastmoney.com/"
            })
            m = re.search(r'"jzrq":"(.*?)".*?"dwjz":"(.*?)"', r.text)
            if m:
                return m.group(1), float(m.group(2))
        except:
            time.sleep(1)
    return None, None


def is_last_trading_day():
    """Check whether today is (likely) the last trading day of the month."""
    today = date.today()
    tomorrow = today + timedelta(days=1)
    # Tomorrow is a new month AND today is a weekday
    if tomorrow.month != today.month:
        return today.weekday() < 5
    # Near month-end: if Friday and next Monday is next month
    if today.day >= 25 and today.weekday() == 4:
        next_monday = today + timedelta(days=3)
        if next_monday.month != today.month:
            return True
    return False


def read_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def write_state(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── Report generator ───────────────────────────────

def generate_report():
    now = datetime.now()
    m_names = ["一月","二月","三月","四月","五月","六月",
               "七月","八月","九月","十月","十一月","十二月"]

    state = read_state()
    prev_navs = state.get("navs", {})
    dca_shares = state.get("dca_shares", {})
    dca_invested = state.get("dca_invested", {})
    cash_baseline = state.get("cash_baseline", {})

    # Initialise baselines on first run
    if not cash_baseline:
        for code in CASH_POOL:
            _, nav = fetch_nav(code)
            if nav:
                cash_baseline[code] = {"nav": nav, "date": CASH_POOL_START}

    if not dca_shares:
        for code in DCA_FUNDS:
            _, nav = fetch_nav(code)
            init_inv = DCA_START_INVESTED.get(code, 0)
            dca_shares[code] = init_inv / nav if (nav and nav > 0) else 0
            dca_invested[code] = init_inv

    # Fetch current NAVs
    cur_navs = {}
    for code in list(CASH_POOL) + list(DCA_FUNDS):
        nd, nv = fetch_nav(code)
        cur_navs[code] = {"nav": nv, "date": nd or "?"}

    lines = []
    lines.append(f"📊 {now.year}年{m_names[now.month-1]}基金月报")
    lines.append(f"📅 {now.strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    total_cost = total_value = 0

    # ── Cash pool ──
    lines.append("━" * 32)
    lines.append("💰 现金池" + (f"（{CASH_POOL_START}起息）" if CASH_POOL_START else ""))
    lines.append("━" * 32)
    cash_cost = cash_value = 0

    for code, info in CASH_POOL.items():
        amt = info["amount"]
        cur = cur_navs[code]
        base = cash_baseline.get(code, {})
        lines.append(f"\n{info['name']}（{code}） 本金：{amt:,}元")
        if cur["nav"] and base.get("nav", 0) > 0:
            ret = (cur["nav"] - base["nav"]) / base["nav"]
            val = amt * (1 + ret)
            lines.append(f"  买入{base['date']}：{base['nav']:.4f} → 最新{cur['date']}：{cur['nav']:.4f}")
            lines.append(f"  累计收益：{val-amt:+,.0f}元（{ret*100:+.2f}%）")
            cash_value += val
        else:
            lines.append(f"  最新净值：{cur['nav'] or '获取失败'}（{cur['date']}）")
            cash_value += amt
        cash_cost += amt

    lines.append(f"\n现金池合计：市值{cash_value:,.0f} / 成本{cash_cost:,} / 收益{cash_value-cash_cost:+,.0f}")
    total_cost += cash_cost
    total_value += cash_value

    # ── DCA ──
    lines.append("")
    lines.append("━" * 32)
    lines.append("📈 定投基金（日定投）")
    lines.append("━" * 32)
    dca_cost = dca_value = 0

    for code, info in DCA_FUNDS.items():
        cur = cur_navs[code]
        lines.append(f"\n{info['name']}（{code}） 日定投：{info['daily']}元")

        old_inv = dca_invested.get(code, DCA_START_INVESTED.get(code, 0))
        extra_days = max(0, (date.today() - date.fromisoformat(CASH_POOL_START)).days)
        extra_td = int(extra_days * 0.7)
        new_inv = old_inv + info["daily"] * extra_td

        if cur["nav"] and cur["nav"] > 0:
            old_sh = dca_shares.get(code, 0)
            new_sh = old_sh + (info["daily"] * extra_td / cur["nav"])
            val = new_sh * cur["nav"]
            lines.append(f"  净值：{cur['nav']:.4f}（{cur['date']}）")
            lines.append(f"  累计投入：{new_inv:,}元 → 市值约{val:,.0f}元")
            lines.append(f"  盈亏：{val-new_inv:+,.0f}元")
            dca_shares[code] = new_sh
            dca_invested[code] = new_inv
        else:
            lines.append(f"  ⚠️ 净值获取失败")
            val = new_inv

        dca_cost += new_inv
        dca_value += val

    lines.append(f"\n定投合计：成本{dca_cost:,} / 市值约{dca_value:,} / {dca_value-dca_cost:+,.0f}")
    total_cost += dca_cost
    total_value += dca_value

    # ── Grand total ──
    lines.append("")
    lines.append("━" * 32)
    lines.append("📋 总资产")
    lines.append("━" * 32)
    gp = total_value - total_cost
    lines.append(f"  总成本：{total_cost:,}元")
    lines.append(f"  总市值：约{total_value:,}元")
    lines.append(f"  总盈亏：{gp:+,.0f}元" + (f"（{gp/total_cost*100:+.2f}%）" if total_cost else ""))

    lines.append("")
    lines.append("— 净值可能有 T+1/T+2 延迟 —")

    # Save state for next month
    write_state({
        "navs": {c: v["nav"] for c, v in cur_navs.items() if v["nav"]},
        "cash_baseline": cash_baseline,
        "dca_shares": dca_shares,
        "dca_invested": dca_invested,
        "last_report": date.today().isoformat(),
    })

    return "\n".join(lines)


# ── Main ────────────────────────────────────────────

if __name__ == "__main__":
    today = date.today()
    if not is_last_trading_day():
        exit(0)

    print("=" * 36)
    print("📊 月度收益报告")
    print("=" * 36)
    print()
    print(generate_report())
