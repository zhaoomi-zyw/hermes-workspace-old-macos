# WeChat (Weixin) Session Reconnection — QR Login Procedure

## Symptoms

Gateway log shows repeated:
```
ERROR gateway.platforms.weixin: [Weixin] Session expired; pausing for 10 minutes
```

Or send failures with `errcode=-14, errmsg=session timeout`.

This means the iLink session token has expired. The bot can no longer send or receive messages. QR re-login is required.

## Fast Path: Direct API Script (avoids interactive menu)

Write a script that hits the iLink API directly:

```python
#!/usr/bin/env python3
"""Fetch WeChat QR code URL and poll for scan confirmation."""
import json, urllib.request, urllib.error, time, sys

BASE = "https://ilinkai.weixin.qq.com"

def fetch_qr():
    url = f"{BASE}/ilink/bot/get_bot_qrcode?bot_type=3"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    qrcode_value = data.get("qrcode", "")
    qrcode_url   = data.get("qrcode_img_content", "")
    return qrcode_value, qrcode_url

def poll(qrcode_value, timeout=480):
    deadline = time.time() + timeout
    while time.time() < deadline:
        url = f"{BASE}/ilink/bot/get_qrcode_status?qrcode={qrcode_value}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except Exception as e:
            time.sleep(1); continue

        status = data.get("status", "wait")
        print(f"[{time.strftime('%H:%M:%S')}] Status: {status}", file=sys.stderr)

        if status == "wait":
            print(".", end="", flush=True)
            time.sleep(2)
        elif status == "scaned":
            print("\n已扫码，请在微信里确认...", file=sys.stderr)
            time.sleep(2)
        elif status == "expired":
            print("\n二维码过期，重新运行脚本获取新码", file=sys.stderr)
            return None
        elif status == "confirmed":
            print("\n登录成功!", file=sys.stderr)
            return data
    print("\n超时", file=sys.stderr)
    return None

if __name__ == "__main__":
    qr_val, qr_url = fetch_qr()
    print(f"二维码链接: {qr_url}", file=sys.stderr)
    print(qr_url)  # stdout: capture this
    result = poll(qr_val)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
```

Run:
```bash
python3 ~/.hermes/weixin_qr_fetch.py 2>&1
```

The script prints the QR URL to stdout — give it to the user. Then poll for confirmation.

## After Successful Login

Extract `account_id` and `token` from the confirmed response and write to `~/.hermes/profiles/<name>/.env`:

```bash
WEIXIN_ACCOUNT_ID=<account_id>
WEIXIN_TOKEN=<token>
```

Then restart the gateway.

## Kill Before Restart

`launchctl stop ai.hermes.gateway-<name>` often does NOT actually kill the Python process — it returns success but the process remains alive. Always verify:

```bash
ps aux | grep "hermes.*gateway.*<name>" | grep -v grep
# If still running:
kill -9 <PID>
```

Then start fresh:

```bash
launchctl start ai.hermes.gateway-<name>
```

## Key iLink API Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /ilink/bot/get_bot_qrcode?bot_type=3` | Fetch QR code token + liteapp URL |
| `GET /ilink/bot/get_qrcode_status?qrcode=<token>` | Poll scan/confirm status |

Status values: `wait` → `scaned` → `confirmed` (success) or `expired`.

## Why Not `hermes gateway setup`?

The interactive TUI menu intercepts keyboard input differently than shell pipes. `printf "14\ny\n" | hermes gateway setup` fails with `✗ Please enter a number` because prompt_toolkit consumes the TTY differently. Direct API script is the reliable alternative.
