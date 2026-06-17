# Provider API Balance & Account Checks

Quick API calls to check token balance and account status for configured providers.

---

## DeepSeek

### Check Balance

```bash
cd /Users/omi/.hermes/profiles/main && \
set -a && source .env && set +a && \
curl -s https://api.deepseek.com/user/balance \
  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}"
```

Returns:
```json
{
  "is_available": true,
  "balance_infos": [
    {"currency": "USD", "total_balance": "0.00", "granted_balance": "0.00", "topped_up_balance": "0.00"},
    {"currency": "CNY", "total_balance": "40.42", "granted_balance": "0.00", "topped_up_balance": "40.42"}
  ]
}
```

### Account Identity

No public API endpoint exposes account email/phone. Must log into https://platform.deepseek.com to view account details.

### Notes

- API key file: `~/.hermes/profiles/main/.env` → `DEEPSEEK_API_KEY=...`
- Hermes `.env` credential masking (shows `***` in read_file) — must use `source .env` + `curl` via terminal
- The `${DEEPSEEK_API_KEY}` env var may cause bash substitution issues in loops; use Python for complex multi-endpoint checks
- Account: zhaoomi@gmail.com (in memory)

---

## MiniMax (minimax-cn)

### Check Balance / Token Plan Status

TBD — MiniMax Token Plan API endpoint to be added when verified.

---

## OpenAI

### Check Usage / Billing

TBD — add `https://api.openai.com/v1/usage` or `https://api.openai.com/dashboard/billing/usage` endpoint when verified.
