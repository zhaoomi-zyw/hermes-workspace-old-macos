# WeChat Bot Unresponsive — Codex 30-Min Hang Episode

**Date**: 2026-06-17
**Provider**: openai-codex (gpt-5.5) via Codex CLI
**Platform**: Weixin (iLink bot API)
**Recovery**: Gateway recovered automatically when the Codex timeout killed the connection, then new messages worked fine.

## Timeline

| Time | Event |
|------|-------|
| **10:35** | User sent "516700怎么样" via WeChat DM |
| **10:35~11:04** | Agent session started, used Codex CLI (gpt-5.5) |
| **11:04:04** | Session 1: API call failed with APIConnectionError → retried |
| **11:04:06** | Session 2: Codex stream produced 0 SSE events for 1685s → retried |
| **11:04:15** | execute_code tool blocked (cron safety guard) on Session 1 |
| **11:04:19** | `send chunk failed to=o9cq80_Q attempt=1/5` — agent tried to push a partial response |
| **11:04~11:34** | Both agent sessions hung — Codex producing no data |
| **11:34:54** | Session 1 killed: "Non-streaming API call stale for 1831s" |
| **11:34:55.297** | First response ready (360 chars) → delivered to WeChat |
| **11:34:55.538** | Session 2 killed: "Codex stream killed after 1802s with no SSE events" |
| **11:34:55.540** | Second response ready (369 chars) → delivered to WeChat |
| **13:12** | Agent cache evicted session (idle 5836s / 97min) |
| **20:14** | `poll error: Connection reset by peer` — iLink server closed connection |
| **20:45** | `poll error: Can't assign requested address` — ephemeral port exhaustion |
| **20:47** | User sent "在？" → responded in 14s ✅ **Recovered** |

## Error Transcript (from errors.log)

```
2026-06-17 11:04:04,479 WARNING agent.conversation_loop: API call failed (attempt 1/3)
  error_type=APIConnectionError provider=openai-codex
  base_url=https://chatgpt.com/backend-api/codex model=gpt-5.5
  summary=Connection error.

2026-06-17 11:04:06,661 WARNING agent.conversation_loop: API call failed (attempt 1/3)
  error_type=TimeoutError provider=openai-codex
  base_url=https://chatgpt.com/backend-api/codex model=gpt-5.5
  summary=Codex stream produced no SSE events for 1685s after first byte

2026-06-17 11:04:19,469 WARNING gateway.platforms.weixin: [Weixin] send chunk failed
  attempt=1/5, retrying in 1.00s

2026-06-17 11:34:54,941 WARNING agent.chat_completion_helpers: Non-streaming API call
  stale for 1831s (threshold 600s). model=gpt-5.5 context=~36,727 tokens.
  Killing connection.

2026-06-17 11:34:54,942 ERROR gateway.run: Agent idle for 1831s (timeout 1800s)
  session agent:main:weixin:dm:o9cq80_QqkAnltK8A4P60TrUwZGk@im.wechat
  last_activity=waiting for non-streaming API response | iteration=4/90

2026-06-17 11:34:55,538 ERROR gateway.run: Agent idle for 0s (timeout 1800s)
  session agent:main:weixin:dm:o9cq80_QqkAnltK8A4P60TrUwZGk@im.wechat
  last_activity=codex stream killed after 1802s with no SSE events
```

## Key Takeaways

1. **Platform vs Runtime**: WeChat was connected the entire time (`gateway_state.json` showed `weixin: connected`). The failure was purely in the agent runtime layer (Codex provider).

2. **"Connected" ≠ "Working"**: The WeChat platform adapter (iLink long-poll) and the agent runtime (LLM provider → tool execution) are independent layers. One can be perfectly healthy while the other is broken.

3. **Provider Hang Recovery**: The agent has a 1800s (30 min) session idle timeout. When the provider eventually times out, the responses DO get delivered — but after a huge delay.

4. **Ephemeral Port Exhaustion**: After the hang, multiple reconnection attempts can exhaust macOS ephemeral ports (`Can't assign requested address`). Auto-resolves as ports are released by TIME_WAIT expiry.

5. **Self-Healing**: The bot recovered without intervention — new messages after the hang resolved triggered fresh sessions that completed quickly.
