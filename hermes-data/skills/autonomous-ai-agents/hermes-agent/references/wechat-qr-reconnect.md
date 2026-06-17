# WeChat (Weixin) QR Reconnect Reference

## When this happens

Gateway log shows repeated:
```
[Weixin] Session expired; pausing for 10 minutes
```
After several hours, WeChat is completely disconnected — the iLink session token has expired and the gateway is in a retry loop.

## Root cause

The iLink Bot API session token has a limited lifetime. When it expires (errcode=-14), the gateway can no longer send or receive messages, even though the process appears to be running.

**Solution:** Re-authenticate via QR code and update the profile's `.env` with new credentials.

## Complete reconnection workflow

### Step 1 — Stop the current (dead) gateway

```bash
# Find the PID
ps aux | grep "hermes_cli.main.*<profile>" | grep -v grep

# Force kill — the process may be zombie despite appearing alive in ps
kill -9 <pid>
```

### Step 2 — Fetch new QR code

Write and run a script that calls the iLink API directly (the `hermes gateway setup` wizard is interactive-only and cannot be scripted with pipe input):

```python
#!/usr/bin/env python3
"""Fetch a fresh WeChat QR code URL from iLink API and poll for login result."""
import asyncio, json, sys, urllib.request, urllib.error, time

ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"
EP_GET_BOT_QR   = "ilink/bot/get_bot_qrcode"
EP_GET_QR_STATUS = "ilink/bot/get_qrcode_status"

def fetch_qr():
    url = f"{ILINK_BASE_URL}/{EP_GET_BOT_QR}?bot_type=3"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    qrcode_value = data.get("qrcode", "")
    qrcode_url   = data.get("qrcode_img_content", "")
    return qrcode_value, qrcode_url

def poll_status(qrcode_value, timeout=480):
    deadline = time.time() + timeout
    while time.time() < deadline:
        url = f"{ILINK_BASE_URL}/{EP_GET_QR_STATUS}?qrcode={qrcode_value}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            time.sleep(1); continue

        status = data.get("status", "wait")
        print(f"[{time.strftime('%H:%M:%S')}] status={status}", file=sys.stderr)

        if status == "confirmed":
            return data
        elif status == "expired":
            return None
        time.sleep(2)
    return None

if __name__ == "__main__":
    qrcode_value, qrcode_url = fetch_qr()
    print(f"QR URL: {qrcode_url}", file=sys.stderr)
    print(f"Open this URL to scan: {qrcode_url}", file=sys.stdout)  # stdout = the URL for capture
    print("Waiting for scan...", file=sys.stderr)
    result = poll_status(qrcode_value)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))  # stdout: full credentials
```

Run it as a **background process** with output captured to a file:

```bash
python3 weixin_qr_fetch.py > /tmp/weixin_qr_result.json 2>&1 &
```

### Step 3 — Extract credentials from result

Once the user scans and confirms, the result JSON contains:

```json
{
  "ilink_bot_id": "1d3a994e2ef3@im.bot",
  "bot_token": "1d3a994e2ef3@im.bot:060000aa33208110dc5200a6be8ac2cff7a5e8",
  "ilink_user_id": "o9cq80_QqkAnltK8A4P60TrUwZGk@im.wechat",
  "ret": 0,
  "status": "confirmed"
}
```

### Step 4 — Update `.env` (BEFORE restarting the gateway)

```bash
WEIXIN_ACCOUNT_ID=1d3a994e2ef3@im.bot
WEIXIN_TOKEN=1d3a994e2ef3@im.bot:060000aa33208110dc5200a6be8ac2cff7a5e8
```

### Step 5 — Restart gateway

```bash
launchctl start ai.hermes.gateway-<profile>
```

### Step 6 — Verify

```bash
tail -20 ~/.hermes/profiles/<profile>/logs/gateway.log | grep "Connected account="
# Should show the NEW account ID (e.g. 1d3a994e), not the old one
```

Also verify the log file's modification time is recent and `wc -l` increases — the gateway process can appear alive in `ps aux` while being a zombie.

## Key pitfalls

- **Updating `.env` after the process is already dead has no effect.** The gateway reads credentials at startup. Kill and restart fully.
- **`hermes gateway setup` cannot be scripted.** It's a curses TUI. Use the Python API approach above instead.
- **QR code expires after ~480 seconds.** Run the poll in background so you can capture the result when the user scans.
- **The gateway process may be zombie despite appearing in `ps aux`.** Always check `tail gateway.log` and `wc -l gateway.log` to confirm it's actually writing.
