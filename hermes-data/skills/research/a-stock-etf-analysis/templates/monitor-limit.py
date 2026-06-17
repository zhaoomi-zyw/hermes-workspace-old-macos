#!/usr/bin/env python3
"""Monitor a fund's daily purchase limit on 天天基金网 for changes.
Usage: python3 monitor-limit.py FUND_CODE FUND_NAME STATE_FILE

Exit codes:
  0 = no change (silent to stdout, info to stderr)
  non-zero = change detected → stdout has alert message
"""

import urllib.request
import re
import json
import os
import sys
from datetime import datetime


def get_current_limit(fund_code):
    """Scrape the daily purchase limit from 天天基金网."""
    url = f"https://fundf10.eastmoney.com/jjgg_{fund_code}.html"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
    })
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[ERROR] Failed to fetch fund page: {e}", file=sys.stderr)
        sys.exit(2)

    # Primary pattern: "单日累计购买上限XXX元"
    m = re.search(r"单日累计购买上限(\d+)\s*元", html)
    if m:
        return int(m.group(1))

    # Fallback: any limit/upper bound with number
    m = re.search(r"(?:申购|购买|限额|限购).*?上限\s*(\d+)\s*元", html)
    if m:
        return int(m.group(1))

    print(f"[ERROR] Could not find purchase limit on page", file=sys.stderr)
    sys.exit(2)


def load_state(state_file):
    if os.path.exists(state_file):
        with open(state_file) as f:
            return json.load(f)
    return {"limit": None, "last_checked": None}


def save_state(state_file, limit, fund_code, fund_name):
    os.makedirs(os.path.dirname(state_file), exist_ok=True)
    state = {
        "limit": limit,
        "last_checked": datetime.now().isoformat(),
        "fund_code": fund_code,
        "fund_name": fund_name,
    }
    with open(state_file, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def main():
    if len(sys.argv) < 4:
        print("Usage: monitor-limit.py FUND_CODE FUND_NAME STATE_FILE", file=sys.stderr)
        sys.exit(2)

    fund_code = sys.argv[1]
    fund_name = sys.argv[2]
    state_file = os.path.expanduser(sys.argv[3])

    state = load_state(state_file)
    old_limit = state.get("limit")

    try:
        new_limit = get_current_limit(fund_code)
    except Exception as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(2)

    save_state(state_file, new_limit, fund_code, fund_name)

    if old_limit is None:
        # First run — establish baseline, silent to stdout
        print(f"[INIT] {fund_name} ({fund_code}) 当前申购上限: {new_limit}元/日", file=sys.stderr)
        sys.exit(0)

    if old_limit != new_limit:
        direction = "上调" if new_limit > old_limit else "下调"
        print(f"⚠️ {fund_name} ({fund_code}) 申购上限变化！")
        print(f"{old_limit}元 → {new_limit}元 ({direction})")
        sys.exit(0)

    # No change — silent
    print(f"[OK] 无变化: {new_limit}元/日", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
