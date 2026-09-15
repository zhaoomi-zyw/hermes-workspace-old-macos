#!/usr/bin/env python3
"""
Monitor purchase limits for DCA funds.
005698 华夏全球科技先锋QDII A — daily DCA 150元
022979 华夏中证A500ETF联接A — daily DCA 150元

Silent when limit unchanged. Alerts on change.
Limit below 150元 = 🔴 CRITICAL (DCA would be blocked)
"""
import requests, re, json, os, sys
from datetime import datetime

FUNDS = {
    "005698": {"name": "华夏全球科技先锋QDII A", "dca": 150},
    "022979": {"name": "华夏中证A500ETF联接A", "dca": 150},
}

STATE_DIR = os.path.expanduser("~/.hermes/profiles/main/cron/state")
STATE_FILE = os.path.join(STATE_DIR, "dca_fund_limits.json")

def fetch_limit(code):
    """Fetch current purchase limit."""
    try:
        txt = requests.get(
            f"https://fundf10.eastmoney.com/jjgg_{code}.html",
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"}
        ).text
        # Look for limit text
        m = re.search(r'单日累计购买上限([\d.]+)万', txt)
        if m:
            return float(m.group(1)) * 10000
        m = re.search(r'单日累计购买上限(\d+)元', txt)
        if m:
            return float(m.group(1))
        if '开放申购' in txt and '暂停申购' not in txt:
            return float('inf')  # No limit
        if '暂停申购' in txt:
            return 0  # Suspended
    except:
        return None
    return float('inf')

def main():
    state = {}
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    
    changes = []
    
    for code, info in FUNDS.items():
        old_limit = state.get(code)
        new_limit = fetch_limit(code)
        
        if new_limit is None:
            changes.append(f"⚠️ {info['name']}（{code}）：获取限额失败")
            state[code] = None
            continue
        
        # Derive status class: 'ok' | 'low' | 'critical' | 'suspended'
        if new_limit == 0:
            new_status = "suspended"
        elif new_limit != float('inf') and new_limit < info['dca']:
            new_status = "critical"
        elif new_limit != float('inf') and new_limit < info['dca'] * 2:
            new_status = "low"
        else:
            new_status = "ok"
        
        old_status = state.get(f"{code}_status")
        
        # Notify only when limit value OR status actually changed
        # Skip alert on first-ever run (no old_status) — just initialize silently
        if old_status is not None and (old_limit != new_limit or old_status != new_status):
            # Limit value change
            if new_limit != old_limit:
                old_str = f"{old_limit:,.0f}元" if old_limit != float('inf') else "开放申购"
                new_str = f"{new_limit:,.0f}元" if new_limit != float('inf') else "开放申购"
                if new_limit == 0:
                    new_str = "暂停申购"
                changes.append(f"🔔 {info['name']}（{code}）限额变更：{old_str} → {new_str}")
            else:
                # Same limit but status changed (e.g. from ok to low due to DCA amount change)
                status_labels = {"suspended": "暂停申购", "critical": "低于定投额", "low": "接近定投额", "ok": "正常"}
                changes.append(f"📌 {info['name']}（{code}）状态变化：{status_labels.get(old_status, '未知')} → {status_labels.get(new_status, '未知')}")
            
            # Additional severity alert
            if new_status == "suspended":
                changes.append(f"🔴 紧急：{info['name']}（{code}）已暂停申购，定投将中断！")
            elif new_status == "critical":
                changes.append(f"🔴 临界：{info['name']}（{code}）限额{new_limit:,.0f}元，低于日定投{info['dca']}元！")
            elif new_status == "low":
                changes.append(f"🟡 关注：{info['name']}（{code}）限额{new_limit:,.0f}元，接近日定投{info['dca']}元")
        
        # Store new limit and status
        state[code] = new_limit
        state[f"{code}_status"] = new_status
    
    # Save state
    os.makedirs(STATE_DIR, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    
    if changes:
        print("📊 定投基金申购限额监控")
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        print(f"📅 {now}")
        print()
        for c in changes:
            print(c)
    else:
        print("[SILENT]")  # No changes, suppress delivery

if __name__ == "__main__":
    main()
