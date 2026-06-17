# WeChat Bot Setup for a New Hermes Profile

## Scenario

A Hermes profile exists but has no messaging platform configured. You want to give it an independent WeChat bot (方案B — new dedicated bot, not shared with another profile).

**Unlike reconnect** (where an existing profile's token expired), a new profile requires:
1. Fetching and scanning the QR code
2. Writing credentials to the profile's `.env`
3. **Adding `platforms: {weixin: {}}` to `config.yaml`** ← this step is only needed for NEW setup, not reconnect
4. Starting the gateway for the first time

## Step-by-Step

### 1. Fetch QR code (background process)

```python
#!/usr/bin/env python3
"""Fetch WeChat QR from iLink API, poll until scan confirmed."""
import json, sys, urllib.request, urllib.error, time

ILINK_BASE_URL = "https://ilinkai.weixin.qq.com"

def fetch_qr():
    url = f"{ILINK_BASE_URL}/ilink/bot/get_bot_qrcode?bot_type=3"
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0")
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    return data.get("qrcode", ""), data.get("qrcode_img_content", "")

def poll(qrcode_value, timeout=480):
    deadline = time.time() + timeout
    while time.time() < deadline:
        url = f"{ILINK_BASE_URL}/ilink/bot/get_qrcode_status?qrcode={qrcode_value}"
        req = urllib.request.Request(url)
        req.add_header("User-Agent", "Mozilla/5.0")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
        except:
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
    print(f"OPEN_THIS_URL_TO_SCAN:{qrcode_url}", file=sys.stdout)
    result = poll(qrcode_value)
    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("QR expired or timeout", file=sys.stderr)
        sys.exit(1)
```

Run as background process:
```bash
python3 /tmp/weixin_qr_fetch.py > /tmp/weixin_qr_result.json 2>&1 &
```
Check output after ~10s: `cat /tmp/weixin_qr_result.json`

### 2. Write credentials to profile `.env`

After scan confirmed, extract from result:
```json
{
  "ilink_bot_id": "7f4fa490915c@im.bot",
  "bot_token": "7f4fa490915c@im.bot:06000001c3ea2071c6933195caa55c2fc78b65",
  "ilink_user_id": "o9cq80zxX7BjhQCClz9VxzJnrUUI@im.wechat"
}
```

Append to `~/.hermes/profiles/<name>/.env`:
```bash
WEIXIN_ACCOUNT_ID=7f4fa490915c@im.bot
WEIXIN_TOKEN=7f4fa490915c@im.bot:06000001c3ea2071c6933195caa55c2fc78b65
WEIXIN_BASE_URL=https://ilinkai.weixin.qq.com
WEIXIN_CDN_BASE_URL=https://novac2c.cdn.weixin.qq.com/c2c
WEIXIN_DM_POLICY=pairing
WEIXIN_ALLOW_ALL_USERS=false
WEIXIN_ALLOWED_USERS=o9cq80zxX7BjhQCClz9VxzJnrUUI@im.wechat
WEIXIN_HOME_CHANNEL=o9cq80zxX7BjhQCClz9VxzJnrUUI@im.wechat
```

### 3. Enable WeChat platform in `config.yaml`

This step is **only needed for new profile setup**, not for reconnection.

```yaml
# In the display: section of config.yaml
platforms: {weixin: {}}
```

Or via CLI:
```bash
hermes config set platforms.weixin.enabled true  # if this syntax works
```

Or edit directly — find `platforms: {}` and change to `platforms: {weixin: {}}`.

### 4. Start the gateway

```bash
cd ~/.hermes/hermes-agent && \
  set -a && source ~/.hermes/profiles/<name>/.env && set +a && \
  ./venv/bin/python -m hermes_cli.main --profile <name> gateway run --replace &
```

Or via launchctl (if previously installed as a service):
```bash
launchctl start ai.hermes.gateway-<name>
```

### 5. Verify

```bash
tail -20 ~/.hermes/profiles/<name>/logs/gateway.log | grep -i "Connected account\|weixin\|error"
```

Expected output:
```
[Weixin] Connected account=7f4fa490 base=https://ilinkai.weixin.qq.com
✓ weixin connected
```

## Key Differences: New Setup vs Reconnect

| Step | New Profile Setup | Reconnect (Expired Token) |
|------|------------------|--------------------------|
| QR script | Same | Same |
| Write `.env` | Append all 8 vars | Update WEIXIN_ACCOUNT_ID + WEIXIN_TOKEN only |
| Edit `config.yaml` | **Required** — add `platforms: {weixin: {}}` | Not needed (already configured) |
| Gateway action | Start fresh | Kill old PID + restart |
| launchctl | `start` (never ran before) | `start` (after kill) |

## Finding Existing Bot Accounts (for reference)

If you need to find previously-connected bot account IDs:

```python
import os, json
acc_dir = '/Users/omi/.hermes/profiles/<profile>/weixin/accounts/'
for f in sorted(os.listdir(acc_dir)):
    if 'sync' in f:
        with open(os.path.join(acc_dir, f)) as fh:
            d = json.load(fh)
        print(f"{f}: account_id={d.get('account_id','?')}")
```

## Troubleshooting: "No messaging platforms enabled"

If gateway logs show:
```
WARNING gateway.run: No messaging platforms enabled.
```

This means either:
1. `.env` is missing the WEIXIN_* credentials → add them
2. `config.yaml` still has `platforms: {}` → change to `platforms: {weixin: {}}`
3. Gateway was not restarted after adding credentials → restart it
