# DeepSeek 503 Service Busy (Omi-specific pattern)

## Symptom

At the start of a new conversation session, before any response is returned:

```
⚠️  API call failed (attempt 1/3): InternalServerError [HTTP 503]
   🔌 Provider: deepseek  Model: deepseek-chat
   🌐 Endpoint: https://api.deepseek.com/v1
   📝 Error: HTTP 503: Service is too busy. We advise users to temporarily switch to alternative LLM API service providers.
   ⏱️  Elapsed: 0.21s  Context: 4 msgs, ~5,180 tokens
⏳ Retrying in 2.7s (attempt 1/3)...
```

Hermes automatically retries 3 times. The 2nd or 3rd attempt usually succeeds, so the user experiences no actual interruption — just visual noise at the top of the terminal.

## Root Cause

DeepSeek V4 Pro (deepseek-chat) has high popularity after recent price drops and model releases. The API server frequently hits capacity limits, returning HTTP 503 "Service Busy" on the first connection attempt of a new session.

This is a **server-side capacity issue**, not a client-side misconfiguration:
- Fast failure (0.21s elapsed) confirms it's an immediate server-side rejection, not a timeout
- The retry succeeds because DeepSeek's load balancer routes the retry to a different backend node
- Each new Hermes session establishes a fresh connection, hitting the overloaded entry point

## Impact

- **Cosmetic only** — the error appears as banner text but the conversation proceeds normally after retry
- DeepSeek will likely scale capacity over time, reducing 503 frequency
- No data loss, no session corruption, no API key invalidation

## Mitigations

1. **Accept the retry** — Hermes handles it transparently. The user sees the red text but never loses service.

2. **Switch to MiniMax** for sessions where the visual noise is bothersome:
   - Use `/model` in-session to pick MiniMax-M2.7, or
   - Change config: `hermes config set model.provider minimax-cn`

3. **Long-term** — wait for DeepSeek to scale infrastructure.

## What NOT to do

- Do NOT rotate API keys — the key is valid, the server is just busy
- Do NOT change the endpoint URL — `https://api.deepseek.com/v1` is correct
- Do NOT reduce context token count — the 503 fires before the request is even processed (0.21s elapsed)
