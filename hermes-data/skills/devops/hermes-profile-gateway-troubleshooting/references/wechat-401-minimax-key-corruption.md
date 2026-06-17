# glp1-research WeChat 401 — Corrupted MINIMAX_CN_API_KEY

**Date**: 2026-05-25  
**Profile**: glp1-research  
**Symptom**: WeChat gateway shows `connected` in `gateway_state.json` but all messages fail with:
```
Non-retryable error (HTTP 401)
Error code: 401 - {'type': 'error', 'error': {'type': 'authorized_error',
'message': "login fail: Please carry the API secret key in the 'Authorization' field (1004)"}
```

## Root Cause

The `MINIMAX_CN_API_KEY` value in `~/.hermes/profiles/glp1-research/.env` was corrupted — a long repeating string instead of the actual key. This was NOT a key sync issue between global .env and profile .env. The profile's own .env key was independently corrupted during a prior write operation.

## Fix Applied

1. Used `read_file` to inspect the actual value in `.env`
2. Used `patch` tool (NOT sed/terminal echo) to replace the corrupted key
3. Killed old gateway process (PID 11306)
4. Restarted gateway with env sourcing:
   ```bash
   cd ~/.hermes/profiles/glp1-research && set -a && source .env && set +a && hermes --profile glp1-research gateway run --replace &
   ```
5. Verified: `gateway_state.json` showed `weixin: {state: "connected"}` with updated timestamp

## Key Insight

- `gateway_state.json` shows WebSocket handshake success only — it does NOT validate that the LLM provider credentials work
- 401 from WeChat adapter means MiniMax API key is invalid at the provider call level, not that WeChat auth failed
- Root cause was a corrupted .env value, NOT environment variable loading or key synchronization

## Prevention

When editing .env files with long API key values:
- Always use `patch` tool (not sed/terminal echo/cat)
- Use `read_file` to verify the written value matches the intended key
- Avoid clipboard paste of keys when terminal write tools are involved