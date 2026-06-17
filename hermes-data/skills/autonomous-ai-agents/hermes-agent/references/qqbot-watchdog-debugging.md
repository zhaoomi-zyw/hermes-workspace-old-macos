# QQBot Watchdog Debugging Notes (2026-05-20)

## Problem

pet-competitor and sakura profiles: QQBot goes offline daily. QQ platform WebSocket disconnects every ~60 seconds (QQ's heartbeat policy). Hermes qqbot adapter reconnects but eventually hangs; state shows "connected" but WebSocket is dead.

## Key Diagnostic Findings

### 1. gateway_state.json is the source of truth
- `gateway.pid` file is NOT always updated when a new process starts — **do not rely on it**
- Always read PID from `gateway_state.json["pid"]`
- `gateway_state.json["platforms"]["qqbot"]["updated_at"]` tells you last activity timestamp

### 2. State vs Reality
- `gateway_state.json` can show `"state": "connected"` while the WebSocket is actually dead
- The `updated_at` timestamp is what actually matters — if it's stale, the connection is dead
- `gateway_state.json["gateway_state"]` can be "running" while qqbot is dead

### 3. Process States
- A gateway process in state `U` (uninterruptible, usually I/O wait) won't respond to `kill` gracefully
- Must use `kill -9` on stuck processes
- Multiple background `terminal()` calls can leave orphaned bash wrapper processes

### 4. How to Diagnose
```bash
# Check state
cat ~/.hermes/profiles/<profile>/gateway_state.json | python3 -m json.tool

# Check last activity (unix timestamp)
python3 -c "
from datetime import datetime
import json
with open('/Users/omi/.hermes/profiles/<profile>/gateway_state.json') as f:
    d = json.load(f)
ts = d['platforms']['qqbot']['updated_at']
print('Last qqbot activity:', ts)
"

# Check actual process
ps aux | grep hermes | grep -v grep
```

## Watchdog Solution

Script: `~/.hermes/scripts/watchdog_qqbot.sh`
Cron job: `hermes cron list` → ID `287f6e53c900`

Logic:
1. Read PID from `gateway_state.json` (NOT gateway.pid)
2. Check `ps -p $pid` — if dead, restart
3. Check `qqbot.updated_at` timestamp — if >10 minutes old, restart
4. Use `setsid` to prevent signal inheritance when launching

Key bash pattern — read PID from JSON reliably:
```bash
get_pid() {
    python3 -c "
import json
with open('/Users/omi/.hermes/profiles/${1}/gateway_state.json') as f:
    print(json.load(f).get('pid', ''))
"
}
```

## Files Created

- `/Users/omi/.hermes/scripts/watchdog_qqbot.sh` — watchdog script
- Cron job `qqbot-watchdog` (287f6e53c900) — runs every 5 minutes
