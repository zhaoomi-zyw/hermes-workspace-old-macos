# Pet-Competitor Profile Debugging — MiniMax Auth Failure (May 2026)

## Symptoms
- Gateway starts OK, qqbot connects
- Messages trigger: `RuntimeError: Provider 'minimax-cn' is set in config.yaml but no API key was found`
- The `.env` has `MINIMAX_CN_API_KEY=***` (appears set)
- `hermes config check` shows `✓ MINIMAX_CN_API_KEY`

## Root Cause
The error message is **misleading**. The real problem was HIDDEN earlier in the same log:

```
⚠️  API call failed (attempt 1/3): AuthenticationError [HTTP 401]
📝 Error: HTTP 401: login fail: Please carry the API secret key in the 'Authorization' field...
```

The API key exists but is **invalid/expired**. The "no API key found" error is a SECONDARY symptom — when the API returns 401, something in the resolution chain fails and produces this error.

## Fix
1. Obtain a fresh MiniMax API key
2. Update `~/.hermes/.env` and/or `~/.hermes/profiles/pet-competitor/.env`
3. Clear session resume queue to stop repeated errors:
   ```bash
   rm -rf ~/.hermes/profiles/pet-competitor/sessions/*.jsonl
   ```
4. Restart gateway with env loaded

## Key Insight
Always search gateway logs for `HTTP 401` before concluding "API key is missing". The "no API key found" error is a downstream fallback message that fires when the actual API call fails.

## Config That Was Correct (once key is valid)
```yaml
model:
  default: MiniMax-M2.7
  provider: minimax-cn
  base_url: https://api.minimaxi.com/v1
custom_providers:
  - name: minimax-cn
    provider: minimax-cn
    api_key: env:MINIMAX_CN_API_KEY
    base_url: https://api.minimaxi.com/v1
```

Base URL must be `/v1` not `/anthropic`.