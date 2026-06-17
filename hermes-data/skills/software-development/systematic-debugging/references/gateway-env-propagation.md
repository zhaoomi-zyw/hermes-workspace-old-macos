# Gateway .env Propagation — Debugging 401 authorized_error

## Symptom

WeChat (or any platform adapter) fails with:
```
Error code: 401 - {'type': 'error', 'error': {'type': 'authorized_error',
'message': "login fail: Please carry the API secret key in the
'Authorization' field of the request header (1004)", 'http_code': '401'}
```

Yet `gateway_state.json` shows the platform as `connected`.

## Root Cause

The gateway process does NOT automatically inherit `.env` from the active profile directory.
It reads from `~/.hermes/.env` (global) only, via `load_env()` in `hermes_cli/config.py`.

If the gateway was started via `openclaw-gateway` directly (not `hermes gateway run` through the profile),
it inherits the system shell environment — not the profile `.env`.

## Diagnostic Checklist

1. Check which `.env` the gateway sees:
   - `grep MINIMAX ~/.hermes/.env` (global)
   - `grep MINIMAX ~/.hermes/profiles/<profile>/.env` (profile-specific)

2. Check which profile is active:
   - `hermes profile active`

3. Check gateway process environment:
   - `ps aux | grep openclaw-gateway` → find PID
   - `grep -E 'MINIMAX|OPENAI' /proc/<PID>/environ | tr '\0' '\n'` (Linux)
   - On macOS: `ls -l /proc/<PID>/` not available — use `hermes gateway status`

4. Check `gateway_state.json`:
   ```json
   "platforms": {"weixin": {"state": "connected", ...}}
   ```
   Note: `connected` means the WeChat WebSocket handshake succeeded, NOT that the
   platform adapter can reach the AI provider at runtime.

## Key Files

- `hermes_cli/config.py:4609` — `load_env()` reads `~/.hermes/.env`
- `agent/credential_pool.py:1768` — `_get_env_prefer_dotenv()` uses `load_env()`
- `gateway/platforms/weixin.py` — WeChat adapter, expects `MINIMAX_CN_API_KEY` in env

## Fix Options

**Option A (preferred):** Restart gateway through hermes so it loads profile `.env`:
```bash
hermes profile switch <profile>
hermes gateway restart
```

**Option B:** Verify global `~/.hermes/.env` has the correct key:
```bash
grep MINIMAX_CN_API_KEY ~/.hermes/.env
```

**Option C:** If the key itself may be expired — get a fresh key from MiniMax dashboard and update `~/.hermes/.env`.