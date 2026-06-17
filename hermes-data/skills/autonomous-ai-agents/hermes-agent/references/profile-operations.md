# Hermes Profile Operations Reference

> Originally the standalone `hermes-profile-operations` skill, consolidated into `hermes-agent`.

## Profile Inspection Workflow

### 1. List all profiles + gateway status
```bash
hermes profile list
```
Shows each profile's model, gateway status, alias. `◆` marks the current active profile.

### 2. Full status including messaging platforms
```bash
hermes status
```
Most informative single command — shows API key config, messaging platform connections, gateway PID, active cron/sessions.

### 3. Per-profile detailed info
```bash
hermes profile show <name>
```
Shows path, model, gateway status, skill count, .env/SOUL.md presence.

### 4. Gateway-specific PID and service info
```bash
hermes gateway status
```
Shows launchd plist details, PID, LastExitStatus. For other profiles, shows compact status.

## Profile Paths
- Profile directory: `~/.hermes/profiles/<name>/`
- Per-profile `.env`: `~/.hermes/profiles/<name>/.env`
- Gateway state: `~/.hermes/profiles/<name>/gateway_state.json`
- Gateway PID lock: `~/.hermes/profiles/<name>/gateway.pid`

## Restarting a Profile's Gateway

**`hermes profile restart <name>` does NOT exist.** There is no `restart` subcommand under `hermes profile`.

Correct method for non-main profiles:
```bash
# Find PID
ps aux | grep "hermes.*<profile_name>" | grep -v grep
# Kill
kill <gateway_pid>
# Start replacement
/Users/omi/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main --profile <profile_name> gateway run --replace &
```

For main profile only — use launchd:
```bash
launchctl kickload -w ~/Library/LaunchAgents/ai.hermes.gateway-main.plist
launchctl start ai.hermes.gateway-main
```

## Platform Management

### Disabling a Messaging Platform
Use `unauthorized_dm_behavior: ignore` inside the `approvals` section of config.yaml:
```yaml
approvals:
  mode: auto
  unauthorized_dm_behavior: ignore
```
This silently drops unauthorized DMs instead of responding with pairing codes. Restart required.

### WeChat Allowlist Issues
When WeChat appears connected but all messages are rejected with "Unauthorized user":
- Symptom: `WEIXIN_ALLOW_ALL_USERS=false` but `WEIXIN_ALLOWED_USERS` is empty
- Fix: Add user ID to allowlist in `.env`: `WEIXIN_ALLOWED_USERS=o9cq80_QqkAnltK8A4P60TrUwZGk@im.wechat`
- Note: `WEIXIN_HOME_CHANNEL` is the bot's own channel ID, NOT the allowlist

### Multi-Profile QQ Bot Setup
QQ credentials go in `.env` files, not config.yaml:
```
QQ_APP_ID=<AppID>
QQ_CLIENT_SECRET=<Token>
QQ_ALLOW_ALL_USERS=true
```
Each profile runs its own gateway process with isolated workspace, identity, and memory.

## Common Pitfalls

1. **`hermes profile config <name>` returns nothing.** Use `hermes profile show <name>` instead.
2. **Profile list shows `stopped` but a PID exists.** Gateway crashed or was SIGTERM'd. Check logs.
3. **QQBot disconnects every ~1 minute.** Known QQ platform WebSocket behavior. Hermes qqbot adapter has reconnect logic but can get stuck. Watchdog cron monitors and restarts.
4. **QQBot shows repeated "Still not connected after 15s" in logs.** Adapter stuck in reconnect loop. Full gateway restart needed, not adapter restart.

## Web Interfaces

For distinguishing between Hermes's three web interfaces (API Server, built-in Dashboard, third-party webui), see `references/hermes-web-interfaces.md`.

## Provider API Checks

For curl commands to check token balance and account status for configured providers (DeepSeek, MiniMax, OpenAI, etc.), see `references/provider-api-checks.md`.
