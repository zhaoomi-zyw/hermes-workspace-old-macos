# Multi-Profile Messaging Credential Reference

## The Problem

Each Hermes profile at `~/.hermes/profiles/<name>/` has its own isolated `.env` file.
Messaging platform credentials (WeChat, QQ, Telegram, etc.) are NOT shared between profiles.
If a profile's gateway logs show:

```
WARNING gateway.run: No messaging platforms enabled.
```

...the profile's `.env` is missing the required credentials — even if the main profile has them.

**Also: WeChat iLink session tokens are NOT MiniMax API keys.** A common misconfiguration
is copying the `WEIXIN_TOKEN` value (a 201-char JWT like `7f4fa490915c@im.bot:06000001c3ea...`)
into the `MINIMAX_CN_API_KEY` field. This causes `HTTP 401: login fail: Please carry the API
secret key` on every LLM call. Use the diagnostic script to confirm before restarting:

```bash
python3 ~/.hermes/profiles/main/skills/autonomous-ai-agents/hermes-agent/scripts/minimax_key_diagnostic.py <profile>
```

## Credential Checklist Per Profile

For a WeChat-enabled profile, the `.env` must contain:

```bash
WEIXIN_ACCOUNT_ID=945ab2f3cee1@im.bot
WEIXIN_TOKEN=<token>           # WeChat iLink session token (from QR scan)
WEIXIN_BASE_URL=https://ilinkai.weixin.qq.com
WEIXIN_CDN_BASE_URL=https://novac2c.cdn.weixin.qq.com/c2c
WEIXIN_DM_POLICY=pairing
WEIXIN_ALLOW_ALL_USERS=false
WEIXIN_ALLOWED_USERS=<user_id>@im.wechat
WEIXIN_HOME_CHANNEL=<user_id>@im.wechat

MINIMAX_CN_API_KEY=sk-cp-2y...  # ← separate from WEIXIN_TOKEN, must be actual API key
```

For QQ-enabled profile:

```bash
QQ_APP_ID=<app_id>
QQ_CLIENT_SECRET=<secret>
QQ_ALLOW_ALL_USERS=true
QQBOT_HOME_CHANNEL=<channel_id>
```

## Quick Diagnostic

```bash
# Check if profile's .env has messaging credentials
grep -E "WEIXIN_|QQ_" ~/.hermes/profiles/<name>/.env

# Check gateway logs for the actual error
grep -i "no messaging\|platforms enabled\|weixin\|qq" \
  ~/.hermes/profiles/<name>/logs/gateway.log

# Diagnose MiniMax API key (see if it's a WeChat token instead)
python3 ~/.hermes/profiles/main/skills/autonomous-ai-agents/hermes-agent/scripts/minimax_key_diagnostic.py <profile>
```

## Fix

Copy missing credentials from main profile's `.env` into the target profile's `.env`, then restart:

```bash
# Kill and restart the gateway
kill $(pgrep -f "hermes.*--profile <name>")
hermes gateway run --profile <name> --replace &
```