# Provider Balance & Account Checking

How to query remaining balance/tokens for various AI providers via their public APIs.

**General pattern:** source the profile's `.env`, then curl the provider's balance endpoint.

```bash
cd ~/.hermes/profiles/<profile> && set -a && source .env && set +a
```

---

## DeepSeek

**Balance endpoint:** `GET https://api.deepseek.com/user/balance`

```bash
curl -s https://api.deepseek.com/user/balance \
  -H "Authorization: Bearer ${DEEPSEEK_API_KEY}"
```

Response:
```json
{
  "is_available": true,
  "balance_infos": [
    {"currency": "USD", "total_balance": "0.00", "granted_balance": "0.00", "topped_up_balance": "0.00"},
    {"currency": "CNY", "total_balance": "40.42", "granted_balance": "0.00", "topped_up_balance": "40.42"}
  ]
}
```

Fields: `total_balance` = sum of `granted_balance` + `topped_up_balance`. CNY is the primary billing currency for Chinese accounts.

**Account identity:** DeepSeek does NOT expose account identity (email, phone, username) via any public API endpoint. The following endpoints all return 404:
- `/user/info`
- `/account/profile`
- `/billing/usage`
- `/dashboard/billing/subscription`

To identify which account a key belongs to, log in to [platform.deepseek.com](https://platform.deepseek.com) → API Keys and match the balance amount.

**Models endpoint** (for verifying the key works): `GET https://api.deepseek.com/v1/models`

---

## OpenAI

**Billing/usage:** OpenAI exposes usage via `https://api.openai.com/v1/usage` (requires billing scope) and dashboard at [platform.openai.com/usage](https://platform.openai.com/usage).

```bash
curl -s https://api.openai.com/v1/usage?date=2026-05-30 \
  -H "Authorization: Bearer ${OPENAI_API_KEY}"
```

---

## Anthropic

Anthropic does not expose a public balance/usage API. Check at [console.anthropic.com](https://console.anthropic.com).

---

## MiniMax

Check at [platform.minimaxi.com](https://platform.minimaxi.com) → 费用中心.
