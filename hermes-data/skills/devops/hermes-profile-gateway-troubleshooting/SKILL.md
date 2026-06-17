---
name: hermes-profile-gateway-troubleshooting
description: Hermes profile architecture, gateway startup failures, and qqbot credential issues
---
# Hermes Profile & Gateway Troubleshooting

## Profiles Architecture

- `~/.hermes/` = default profile (not a subfolder)
- Additional profiles live in `~/.hermes/profiles/<name>/`
- Each profile can have its own `.env`, `config.yaml`, `gateway_state.json`
- `hermes profile list` shows all profiles with their gateway status

## Default Profile Gateway Won't Start

**Symptom**: `hermes chat` (default profile) hangs with no response. `hermes gateway status` shows stopped.

**Diagnosis**:
1. Check what platform is failing: `tail ~/.hermes/logs/gateway.error.log`
2. If qqbot fails with "QQ_APP_ID and QQ_CLIENT_SECRET are required" → credentials are missing
3. If all platforms fail → gateway exits immediately

**Key insight**: qqbot credentials come from `~/.hermes/.env` environment variables (`QQ_APP_ID`, `QQ_CLIENT_SECRET`), NOT from `config.yaml`.

**Two fixes**:
- **Fix A (recommended)**: Use main profile instead: `hermes chat --profile main` or `hermes profile use main`
- **Fix B**: Provide qqbot credentials in `~/.hermes/.env`, OR disable qqbot in config.yaml

## Launchd Gateway Service

- Service plist: `~/Library/LaunchAgents/ai.hermes.gateway.plist`
- Launchd does NOT use `--profile` flag — it uses `HERMES_HOME` env var
- `hermes gateway start` regenerates the plist from current profile
- `hermes --profile <name> gateway start` → plist starts that profile's gateway

## Multiple Profiles Can Run Simultaneously

- main gateway: `hermes gateway start` (uses HERMES_HOME, likely main profile)
- default gateway: `hermes --profile default gateway start`
- Each runs its own process with its own `.env` / config
- Check processes: `ps aux | grep 'hermes.*gateway' | grep -v grep`

### Stopping a Specific Profile's Gateway

```bash
hermes --profile <name> gateway stop
```

**Pitfall — `HERMES_PROFILE` env var does NOT work for gateway stop**: Using `HERMES_PROFILE=sakura hermes gateway stop` stops the **main** profile's gateway (`hermes-gateway-main`), not the target profile's. Always use the `--profile` CLI flag, not the env var, for `gateway stop` and `gateway start`.

**Pitfall — Don't `kill` the process directly**: Launchd-managed gateways (labels like `ai.hermes.gateway-<profile>`) auto-restart after a SIGTERM. Use `hermes --profile <name> gateway stop` to properly unload the launchd job.

**Verification that it's fully stopped**:
```bash
# Should return empty (no process)
ps aux | grep "hermes.*--profile <name>" | grep -v grep
# Should return empty (no launchd entry)
launchctl list 2>/dev/null | grep gateway-<name>
```

## Clearing Stale gateway_state.json

If a profile shows "token already in use" but the process is dead:
```bash
rm ~/.hermes/gateway_state.json  # or profile's gateway_state.json
```

## Disabling Platforms (qqbot / weixin)

**qqbot**: The `qqbot` platform is loaded at runtime based on the **presence** of `QQ_APP_ID` and `QQ_CLIENT_SECRET` environment variables in the profile's `.env` file, NOT from `config.yaml`. This means setting `qqbot: []` in `platform_toolsets` does NOT disable it — it still loads if env vars exist. To truly disable qqbot, remove `QQ_APP_ID` and `QQ_CLIENT_SECRET` from the profile's `.env`.

**weixin**: Same behavior — setting `weixin: []` in `platform_toolsets` does NOT disable weixin. It still initializes and connects if account/token files exist in `weixin/accounts/`. To disable weixin, remove the weixin account files or use a profile with no weixin configuration.

**Workaround**: For a qqbot-only profile, use a separate profile directory with only qqbot credentials in `.env` and no `weixin/` subdirectory.

## WeChat "Unauthorized User" Even When Connected

**Symptom**: WeChat gateway shows `weixin: connected` in `gateway_state.json`, but messages fail with `Unauthorized user: <weixin_id>` in error log.

**Root cause**: `WEIXIN_ALLOW_ALL_USERS=false` and `WEIXIN_ALLOWED_USERS=` is empty — all users are denied by default.

**Fix**: Add the denied WeChat user ID to `WEIXIN_ALLOWED_USERS` in the profile's `.env`:
```bash
# Find the denied user ID from error log:
grep "Unauthorized user" ~/.hermes/profiles/<name>/logs/gateway.error.log

# Set it in the profile's .env (use sed since .env is protected):
sed -i '' 's/^WEIXIN_ALLOWED_USERS=$/WEIXIN_ALLOWED_USERS=<user_id>/' ~/.hermes/profiles/<name>/.env
```

**Key insight**: The user's own WeChat ID (`WEIXIN_HOME_CHANNEL`) must also be in `WEIXIN_ALLOWED_USERS` — setting `WEIXIN_HOME_CHANNEL` alone does NOT grant permission.

## QQBot "No messaging platforms enabled" — Missing Credentials

**Symptom**: Gateway starts but logs say:
```
WARNING gateway.run: No messaging platforms enabled.
Gateway will continue running for cron job execution.
```

Both weixin and qqbot show disconnected. The gateway runs but no messaging platform connects.

**Root Cause**: Each profile has its own `.env` file (`~/.hermes/profiles/<name>/.env`). Credentials for messaging platforms (WeChat, QQ) live in the `.env` file, NOT in `config.yaml`. If the profile's `.env` is missing the required variables, that platform simply doesn't initialize.

**Fix — Add QQ credentials to the profile's `.env`**:
```bash
# Append to the profile's .env file
cat >> ~/.hermes/profiles/<name>/.env << 'EOF'

QQ_APP_ID=1903908826
QQ_CLIENT_SECRET=your_secret_here
QQ_ALLOW_ALL_USERS=true
QQ_ALLOWED_USERS=
QQBOT_HOME_CHANNEL=your_home_channel_id
EOF
```

For WeChat, the required variables typically include:
```
WEIXIN_ACCOUNT_ID=945ab2f3cee1@im.bot
WEIXIN_TOKEN=...
WEIXIN_BASE_URL=https://ilinkai.weixin.qq.com
WEIXIN_ALLOWED_USERS=o9cq80_QqkAnltK8A4P60TrUwZGk@im.wechat
WEIXIN_HOME_CHANNEL=o9cq80_QqkAnltK8A4P60TrUwZGk@im.wechat
```

**After adding credentials, restart the gateway**:
```bash
ps aux | grep 'hermes.*gateway' | grep <profile> | grep -v grep | awk '{print $2}' | xargs kill
hermes --profile <name> gateway run --replace &
```

**Verification**:
```bash
sleep 6 && tail -10 ~/.hermes/profiles/<name>/logs/gateway.log
# Look for: ✓ qqbot connected / ✓ weixin connected
```

---

## Auxiliary LLM Provider Warning on Messaging Platforms

**Symptom**: QQ/WeChat bot is connected but shows:
```
⚠️ No auxiliary LLM provider configured — context compression will drop middle turns without a summary.
Auxiliary title generation failed: No LLM provider configured for task=title_generation provider=auto.
Run: hermes setup or set OPENROUTER_API_KEY.
```

The bot is online and connected, but fails to generate responses because auxiliary tasks (title generation, compression, etc.) are set to `provider: auto` which has no backend.

**Root Cause**: In `config.yaml`, auxiliary tasks like `compression`, `title_generation`, `vision`, etc. default to `provider: auto`. When no API key is configured for the `auto` fallback, these tasks fail silently or with the above warning.

**Fix — Set all auxiliary providers to the profile's main LLM**:
```bash
hermes config set auxiliary.vision.provider minimax-cn --profile <name>
hermes config set auxiliary.web_extract.provider minimax-cn --profile <name>
hermes config set auxiliary.compression.provider minimax-cn --profile <name>
hermes config set auxiliary.session_search.provider minimax-cn --profile <name>
hermes config set auxiliary.skills_hub.provider minimax-cn --profile <name>
hermes config set auxiliary.approval.provider minimax-cn --profile <name>
hermes config set auxiliary.mcp.provider minimax-cn --profile <name>
hermes config set auxiliary.title_generation.provider minimax-cn --profile <name>
hermes config set auxiliary.triage_specifier.provider minimax-cn --profile <name>
hermes config set auxiliary.curator.provider minimax-cn --profile <name>
```

Or edit `~/.hermes/profiles/<name>/config.yaml` directly — find the `auxiliary:` section and set `provider: minimax-cn` under each sub-task.

**Then restart the gateway**.

**Key Insight**: `auxiliary.*.provider` is independent from `model.provider`. The profile can use MiniMax for chat while auxiliary tasks use the same MiniMax credentials — just set `auxiliary.*.provider` to the same provider name (`minimax-cn`).

---

## WeChat Gateway Stuck in Rate-Limit Loop

**Symptom**: Gateway process is running (`ps aux` shows PID alive), `gateway_state.json` shows weixin connected, but messages fail repeatedly:
```
WARNING gateway.platforms.weixin: [Weixin] rate limited for o9cq80_Q; backing off 3.0s before retry
ERROR gateway.platforms.weixin: [Weixin] send failed to=o9cq80_Q: iLink sendmessage rate limited: ret=-2
```

**Root cause**: The weixin gateway connection is alive but stuck in a rate-limiting loop — the gateway can't send but keeps trying. Causes include prolonged idle, too many rapid messages, or a server-side session age-out.

**Fix**: Restart the gateway — clears the stuck poll loop and restores fresh context tokens:
```bash
hermes --profile main gateway restart
```

**Key insight**: A running gateway process does NOT mean the messaging platform is healthy. Rate-limiting on weixin causes send failures while the connection appears alive in `gateway_state.json`. Restart clears stuck state and restores fresh connection. Always use profile-specific log: `~/.hermes/profiles/main/logs/gateway.log`, NOT the root-level `~/.hermes/logs/gateway.log`.

**Verification**:
```bash
sleep 8 && tail -20 ~/.hermes/profiles/main/logs/gateway.log
# Look for: ✓ weixin connected
```

## WeChat 401 authorized_error — Platform Shows Connected But Bot Fails

**Symptom**: `gateway_state.json` shows `weixin: {state: "connected"}` but the bot fails to respond with:
```
Non-retryable error (HTTP 401)
Error code: 401 - {'type': 'error', 'error': {'type': 'authorized_error',
'message': "login fail: Please carry the API secret key in the
'Authorization' field of the request header (1004)", 'http_code': '401'}
```

The WeChat WebSocket handshake succeeded (hence `connected`), but when the adapter tries to call the LLM provider (MiniMax) for response generation, it gets a 401 because the API key is invalid.

**Root Causes to Check (in order)**:

1. **Corrupted / duplicated API key value** — Most common on macOS. The `MINIMAX_CN_API_KEY` in `~/.hermes/profiles/<profile>/.env` contains a malformed repeated string like `sk-cp-...OOmw...` instead of the actual key. Caused by certain text editors/tools corrupting long base64 key values during write.

   **Diagnosis**: `grep MINIMAX_CN_API_KEY ~/.hermes/profiles/<profile>/.env` — if the value looks like a repeating pattern or displays as `***` (masked), it's corrupted. Use `read_file` on the `.env` to see the actual value.

   **Fix**: Replace with the actual key from MiniMax dashboard. Use `patch` (not sed/terminal) to write the .env — sed can also corrupt long keys.

2. **Key is valid but revoked/expired** — Get a fresh key from the MiniMax dashboard.

3. **Gateway started without profile env** — If the gateway was started via `openclaw-gateway` directly rather than `hermes --profile <name> gateway run`, it may not have loaded the profile's `.env`. Always start with:
   ```bash
   cd ~/.hermes/profiles/<profile> && set -a && source .env && set +a && hermes --profile <profile> gateway run --replace &
   ```

**Key insight**: `connected` in `gateway_state.json` only means the WeChat WebSocket is alive. It says nothing about whether the platform adapter can successfully call the LLM provider at message-handling time. The 401 is a downstream provider auth failure, not a WeChat auth failure.

**Verification**:
```bash
# Confirm key is valid (should return JSON with id, not 404)
KEY=$(grep MINIMAX_CN_API_KEY ~/.hermes/profiles/<profile>/.env | cut -d= -f2)
curl -s -X POST "https://api.minimaxi.com/v1/messages" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -H "anthropic-version: 2023-06-01" \
  -d '{"model":"MiniMax-M2.7","max_tokens":10,"messages":[{"role":"user","content":"hi"}]}'
```

**Restart after fix**:
```bash
cd ~/.hermes/profiles/<profile> && set -a && source .env && set +a && hermes --profile <profile> gateway run --replace &
sleep 10 && grep weixin ~/.hermes/profiles/<profile>/gateway_state.json
```

---

## Gateway Stale Bytecode — ImportError After Code Update

**Symptom**: WeChat (or another platform) shows "connected" in `gateway_state.json`, but inbound messages fail silently or produce error responses. Gateway logs show:

```
ImportError: cannot import name '<function_name>' from 'tools.<module>' (/Users/omi/.hermes/hermes-agent/tools/<module>.py)
```

The function being imported **does exist** in the source file — confirmed by `read_file` or `git show`.

**Root cause**: The gateway process loaded an older version of the Python module into memory at startup. After a `git pull` or code change, the `.py` file was updated but the running process still holds stale bytecode. The function may have been added after gateway startup, or the module's import chain changed.

**Diagnosis workflow**:
```bash
# 1. Check gateway logs for ImportError
grep -i "importError\|cannot import" ~/.hermes/profiles/<name>/logs/gateway.log

# 2. Verify the function IS present in the source
grep "def <function_name>" /Users/omi/.hermes/hermes-agent/tools/<module>.py

# 3. Verify import works from the venv
/Users/omi/.hermes/hermes-agent/venv/bin/python -c "from tools.<module> import <function_name>; print('OK:', <function_name>)"

# 4. Compare .py vs .pyc modification times
ls -la /Users/omi/.hermes/hermes-agent/tools/__pycache__/<module>*.pyc
stat -f "%Sm" /Users/omi/.hermes/hermes-agent/tools/<module>.py
```

If step 3 succeeds but the gateway still fails → stale in-memory module. **Fix**:

```bash
# Kill the gateway — launchd will auto-restart with fresh code
kill $(ps aux | grep "hermes.*--profile main" | grep -v grep | awk '{print $2}')
sleep 5
# Verify new gateway started and WeChat reconnected
tail -20 ~/.hermes/profiles/main/logs/gateway.log | grep -iE "weixin.*connected|started"
```

**After restart**, verify the error no longer appears and messages process correctly.

**Key insight**: `gateway_state.json` can show `weixin: connected` even when the agent is broken on every inbound message. The WebSocket (platform connectivity) and the agent runtime (LLM / tool execution) are independent layers. A connected bot that fails on every message is usually a code-level issue in the agent runtime, not a platform auth issue.

**Prevention**: After `git pull` on the Hermes repo, always restart the gateway:
```bash
kill $(ps aux | grep "hermes.*gateway" | grep -v grep | awk '{print $2}')
# launchd auto-restarts
```

## QQBot Credential Failure — "invalid appid or secret"

**Symptom**: QQBot was previously failing with "QQ_APP_ID and QQ_CLIENT_SECRET are required" but now fails with:
```
RuntimeError: QQ Bot token response missing access_token: {'code': 100016, 'message': 'invalid appid or secret'}
```

**Root cause**: Credentials are present in `.env` (`QQ_APP_ID=1903908826`) but are no longer valid — the QQ Bot application has been deleted, reset, or the secret rotated on the QQ Open Platform. The gateway runs fine with weixin only.

**Diagnosis**:
```bash
grep QQ_ ~/.hermes/profiles/main/.env
```

**Fix**: Refresh credentials on the [QQ Open Platform](https://open.qq.com/). No manual disabling needed — gateway continues running with weixin.

---

## Hermes API Server (OpenAI-Compatible HTTP API)

The API Server is a gateway platform adapter that exposes an OpenAI-compatible HTTP API. Unlike the Dashboard (HTML UI), the API Server provides `/v1/chat/completions`, `/v1/models`, `/health`, etc. — any OpenAI-compatible frontend (Open WebUI, LobeChat, etc.) can connect to it.

Default bind: `127.0.0.1:8642` (loopback only, no auth required).

### Enabling for LAN Access

To make the API Server accessible from other machines on the LAN (e.g. `http://192.168.1.113:8787/v1`), set these env vars in the profile's `.env`:

```bash
API_SERVER_ENABLED=true
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8787
API_SERVER_KEY=<a strong random key>
```

### Critical Pitfall — API_SERVER_KEY is mandatory on 0.0.0.0

Binding to `0.0.0.0` (or any non-loopback address) **requires** `API_SERVER_KEY`. Without it, the gateway refuses to start the API server:

```
ERROR gateway.platforms.api_server: [Api_Server] Refusing to start: API_SERVER_KEY
is required for the API server, including loopback-only binds on 0.0.0.0.
```

Generate a random key: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

Binding to `127.0.0.1` (default) does NOT require a key.

### Verification

```bash
# Check port is listening
lsof -i :8787 -P -n

# Health check
curl -s -o /dev/null -w "%{http_code}" http://192.168.1.113:8787/health
# Expected: 200
```

### After Changing .env

Restart the gateway for the API Server env vars to take effect:
```bash
hermes gateway restart
```

> **See also**: `references/api-server-lan-setup.md` — full session recipe with diagnostics.

## Prevention

When editing .env files with long API key values, always use `patch` tool (not sed/terminal echo/cat). Use `read_file` to verify the written value matches the intended key. Avoid clipboard paste of keys when terminal write tools are involved.

> **See also**: `references/wechat-401-minimax-key-corruption.md` — full case study with timeline and commands used.

## API Server vs Dashboard — Critical Distinction

These are **two different things** and the confusion is common:

| | API Server | Dashboard |
|---|---|---|
| What | OpenAI-compatible REST API | HTML web UI |
| Start | Via gateway (env vars in .env) | `hermes dashboard` (separate process) |
| Default port | 8642 | 9119 |
| Root path | 404 (no UI) | 200 (HTML page) |
| Uses | Open WebUI, LobeChat, programmatic | Browser-based config, sessions, chat |
| Gateway restart | Picks up .env vars automatically | Does NOT auto-start — must run separately |

**Pitfall — "I restarted the gateway but the web UI is gone"**: The Dashboard is a completely separate process from the gateway. `hermes gateway restart` does NOT restart the dashboard. You must run `hermes dashboard` separately. If both need to be on the same port (e.g. 8787), stop the API Server first by changing `API_SERVER_PORT` in `.env` away from that port.

**Quick fix for missing Dashboard after gateway restart**:
```bash
hermes dashboard --stop          # kill any stale instances
hermes dashboard --host 0.0.0.0 --port 8787 --insecure --no-open &
```

## Hermes Web Dashboard Setup

**Symptom**: User wants a browser-based UI for Hermes (config, sessions, chat, cron, usage stats).

### Installation

The Dashboard needs `[web,pty]` extras. Hermes' venv may lack pip — fix first:

```bash
# Fix missing pip in venv
/Users/omi/.hermes/hermes-agent/venv/bin/python3 -m ensurepip

# Install extras
/Users/omi/.hermes/hermes-agent/venv/bin/python3 -m pip install 'hermes-agent[web,pty]'
```

### Basic Usage

```bash
# Start Dashboard (local only — http://127.0.0.1:9119)
hermes dashboard

# With in-browser Chat tab (needs --tui)
hermes dashboard --tui
```

### LAN Access (Windows/other devices on same network)

```bash
# Stop any existing instances first
hermes dashboard --stop

# Start with LAN binding (⚠️ requires --insecure)
hermes dashboard --host 0.0.0.0 --port 9119 --insecure

# With Chat tab:
hermes dashboard --host 0.0.0.0 --port 9119 --tui --insecure
```

**Pitfall — `--insecure` is required for `--host 0.0.0.0`**: Running `hermes dashboard --host 0.0.0.0` without `--insecure` is refused with:
```
Refusing to bind to 0.0.0.0 — the dashboard exposes API keys and config
without robust authentication.
Use --insecure to override (NOT recommended on untrusted networks).
```

### Lifecycle Management

```bash
hermes dashboard --status   # List running dashboard processes
hermes dashboard --stop     # Kill all dashboard processes
```

**Pitfall — Dashboard does NOT auto-start with gateway**: `hermes gateway restart` only restarts the messaging/API gateway. The Dashboard is a completely independent process. After a machine reboot or gateway restart, you must manually start the dashboard again:
```bash
hermes dashboard --host 0.0.0.0 --port 8787 --insecure --no-open &
```

**Pitfall — Port conflict with API Server**: If the API Server is configured on the same port (e.g. both on 8787), the Dashboard will fail to bind. Either change `API_SERVER_PORT` in `.env` or use a different port for the Dashboard. The Dashboard default is 9119.

**`--no-open` flag**: In headless/background/SSH contexts, always use `--no-open` to prevent the dashboard from trying to launch a browser.

### Prerequisite — tmux (macOS)

The tmux workaround (Option B below) requires `tmux`. It's not pre-installed on macOS:

```bash
brew install tmux
```

### Pitfall — `--tui` Chat tab shows "events feed disconnected"

The `--tui` (Chat panel) spawns a PTY-based embedded Hermes TUI. The Chat tab can show "events feed disconnected — tool calls may not appear" for **two distinct reasons**:

#### Cause 1: No controlling PTY (background start)

When started via `terminal(background=true)` (no controlling terminal), the PTY bridge can't get a real terminal.

**Root cause**: Background processes in Hermes agent run without a controlling PTY. The `--tui` mode depends on `ptyprocess` which needs a real terminal.

**Solutions**:
- **Option A (recommended)**: Skip `--tui` on the Dashboard, use CLI `hermes` for actual conversations. Dashboard for config/sessions/cron/usage; terminal for chat.
- **Option B (tmux wrapper)**: Start the dashboard inside a tmux session to provide a real PTY:
  ```bash
  tmux kill-session -t hermes-dash 2>/dev/null
  tmux new-session -d -s hermes-dash 'hermes dashboard --host 0.0.0.0 --port 9119 --tui --insecure'
  ```

#### Cause 2: LAN client IP rejected by WebSocket guard (even with `--insecure`)

When accessing from another machine on the LAN (e.g. `192.168.1.113:9119/chat`), the events feed shows disconnected even though the dashboard was started with `--host 0.0.0.0 --insecure`.

**Root cause**: `_ws_client_is_allowed()` in `hermes_cli/web_server.py` hardcodes loopback-only (`127.0.0.1`, `::1`, `localhost`). The `--insecure` flag relaxes HTTP Host-header checks but does NOT flow through to WebSocket client-IP checks. Non-loopback clients are rejected with close code 4403 BEFORE the WebSocket handshake completes. Because the close is pre-accept, the browser sees abnormal closure (code 1006) and shows the generic "events feed disconnected" rather than the specific "events feed rejected (4403)".

**Diagnosis**: From the browser machine, open DevTools → Network → WS tab. If the `/api/events` WebSocket shows status "(failed)" or closes immediately with code 1006, and the page was loaded from a LAN IP, this is the cause. Quick test: access `http://127.0.0.1:9119/chat` from the same machine running the dashboard — if events feed works there, the LAN IP guard is blocking.

**Fix**: Patch `_ws_client_is_allowed()` to honour `--insecure` mode. Details in `references/dashboard-ws-lan-client-fix.md`.

After patching, restart the dashboard (kill tmux session + recreate).

### Community Web UIs (Alternatives)

The built-in dashboard has limitations: the Chat tab requires PTY (`--tui` + tmux),
no native file attachment support, and LAN access needs source patches. Two community
alternatives offer richer web experiences:

| | hermes-webui | AionUi |
|---|---|---|
| Stars | ★9,039 | ★26,984 |
| Focus | Hermes-only, full CLI parity | Multi-agent Cowork platform |
| Attachments | ✅ Native file upload per-session | ⚠️ Agent-to-agent file sharing |
| Profiles | ✅ Full profile switching | ✅ Multi-agent profiles |
| Setup | Python + vanilla JS, no build | Desktop app + WebUI, zero config |
| Repo | `nesquena/hermes-webui` | `iOfficeAI/AionUi` |

**hermes-webui** (`nesquena/hermes-webui`) — recommended for Hermes-only use.
Full install guide: `references/hermes-webui-install.md`.
Troubleshooting guide: `references/hermes-webui-server-troubleshooting.md`.

- Three-panel layout (sessions | chat | workspace file browser)
- File attachments stored at `~/.hermes/webui/attachments/<session_id>/`
- Attachments persist across page reloads
- SSH tunnel friendly, SSE auto-reconnect
- Optional password protection, light/dark themes

**AionUi** (`iOfficeAI/AionUi`) — multi-agent Cowork platform:
- Supports Hermes + Claude Code + Codex + 20+ other CLI agents
- Built-in PPT/Word/Excel generation via OfficeCLI
- 21 pre-built professional assistants
- Telegram / Feishu / DingTalk / WeChat access
- Desktop app (macOS/Windows/Linux) + mobile WebUI

### Verification

```bash
# Check if dashboard is running and responding
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119/
# Should return 200
```

## WeChat Bot Unresponsive — Codex / Provider Hang Pattern

**Symptom**: WeChat bot appears disconnected — no response for 10+ minutes, the WeChat app shows no typing indicator, user may get a "send chunk failed" in logs. But `gateway_state.json` shows `weixin: connected` and the gateway process is running.

**Root cause**: The WeChat platform adapter (iLink long-poll) is fine. The **agent runtime / LLM provider** is hung. Most commonly: Codex CLI (`openai-codex` / `gpt-5.5`) stream produces no SSE events for 30+ minutes, causing the entire agent session to block.

**Diagnostic steps**:

```bash
# 1. Check if weixin is actually connected (platform level)
grep weixin ~/.hermes/profiles/main/gateway_state.json
# Expected: "state": "connected"

# 2. Check for provider-hang patterns in errors.log
grep "Codex stream produced no SSE events\|Agent idle for" ~/.hermes/profiles/main/logs/errors.log | tail -10

# 3. Check gateway.log for the complete timeline
grep "send chunk failed\|response ready.*weixin" ~/.hermes/profiles/main/logs/gateway.log

# 4. Check if the LLM provider API call itself was stuck
grep "Non-streaming API call stale\|Codex stream killed\|waiting for non-streaming" ~/.hermes/profiles/main/logs/errors.log
```

**Key error signatures**:

| Error | Meaning |
|-------|---------|
| `Codex stream produced no SSE events for Ns after first byte` | Codex backend connected but never produced data. N ≥ 1800 = 30 min timeout |
| `Agent idle for Ns (timeout 1800s)` | Agent session timed out because no API response arrived |
| `send chunk failed to=o9cq80_Q attempt=1/5` | Agent tried to push a partial response but the hung provider blocked it |
| `Connection reset by peer` (weixin poll) | iLink server closed the long-poll connection — normal, auto-reconnects |
| `Can't assign requested address` (errno 49) (weixin poll) | macOS ephemeral port exhaustion — local port pool depleted by too many concurrent outbound connections. Auto-resolves after existing connections close and ports are released. |
| `send chunk failed to=o9cq80_Q attempt=N/5` (empty errmsg) | Agent tried to push a partial response chunk but the hung provider blocked the send queue. No specific iLink error — the failure is downstream of WeChat. The empty `errmsg=` (no text) means the TCP connection to iLink was still alive but the send timed out waiting for the stuck provider to yield. |

**Fix options**:

1. **Try a new message** — Sending another message ("在？") triggers a new session that may work around the hung one (as happened in this session — 20:47 message responded in 14s).

2. **Restart the gateway** — Clears all in-flight agent sessions and provider connections:
   ```bash
   hermes --profile main gateway restart
   ```

3. **Switch away from Codex provider** — If Codex/`openai-codex` is frequently hanging, change the model provider to a more reliable one (DeepSeek, MiniMax, etc.). **Crucially, also clear the old `base_url`** — the old Codex URL (`https://chatgpt.com/backend-api/codex`) will break the new provider if left set:
   ```bash
   hermes config set model.provider deepseek
   hermes config set model.default deepseek-v4-flash
   hermes config set model.base_url ""         # ← MUST clear old Codex URL
   ```
   After changing, **restart the gateway** for the new provider to take effect:
   ```bash
   hermes gateway restart
   ```
   **Verify** the weixin adapter reconnects with the new provider:
   ```bash
   sleep 3 && grep weixin ~/.hermes/profiles/main/logs/gateway.log | tail -5
   # Look for: ✓ weixin connected
   ```

   **Pitfall — `hermes config set model.model` vs `model.default`**: The correct key is `model.default`, not `model.model`. `model.default` sets the default model name used by the provider.

**Key insight**: A connected WeChat bot that fails to respond is almost always an **agent runtime / LLM provider** issue, not a WeChat platform issue. Platform-level diagnostics (connection state, auth, rate limits) will all show healthy. Always check `errors.log` for provider timeout patterns first.

**Prevention**: After a `git pull` or provider config change, send a quick test message through WeChat to verify the agent runtime chain (inbound poll → LLM call → tool execution → outbound send) completes within seconds.

> **See also**: `references/weixin-codex-hang-timeline.md` — detailed timeline of a 30-minute Codex hang episode, with complete error transcript and recovery.

## Verification Commands

```bash
# Check running gateways
ps aux | grep 'hermes.*gateway' | grep -v grep

# Check gateway status for a profile
hermes --profile <name> gateway status

# View error logs — use PROFILE-SPECIFIC log, not root-level
tail ~/.hermes/profiles/<name>/logs/gateway.log

# Restart gateway
hermes --profile <name> gateway restart

# Stop gateway (properly unloads launchd job)
hermes --profile <name> gateway stop
```
