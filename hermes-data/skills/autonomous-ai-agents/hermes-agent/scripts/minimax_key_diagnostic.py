#!/usr/bin/env python3
"""
Diagnose MiniMax API key auth failures in Hermes profiles.
Run from any machine with access to ~/.hermes/profiles/<name>/.env

Usage: python3 minimax_key_diagnostic.py [profile_name]
"""
import sys, json, urllib.request, urllib.error

PROFILE = sys.argv[1] if len(sys.argv) > 1 else "glp1-research"
ENV_PATH = f"/Users/omi/.hermes/profiles/{PROFILE}/.env"

print(f"=== MiniMax Auth Diagnostic: {PROFILE} ===\n")

# Step 1: read the .env
key = None
with open(ENV_PATH) as f:
    for line in f:
        if line.startswith('MINIMAX_CN_API_KEY'):
            key = line.strip().split('=', 1)[1]
            break

if not key:
    print("ERROR: MINIMAX_CN_API_KEY not found in .env"); sys.exit(1)

print(f"Key length: {len(key)}")
print(f"Key prefix: {key[:20]}")

# Step 2: classify the key type
if len(key) > 180 and '@im.bot:' in key:
    print("⚠️  This looks like a WeChat iLink SESSION TOKEN (not a MiniMax API key)")
    print("    WeChat tokens start with <account_id>@im.bot:<session>")
    print("    This cannot be used for MiniMax API calls.")
    print("    FIX: replace MINIMAX_CN_API_KEY with the actual MiniMax API key from main profile")
    sys.exit(1)
elif key.startswith('sk-cp-') or len(key) < 150:
    print("✓  This looks like a valid MiniMax API key")
else:
    print(f"?  Unrecognized key format (len={len(key)})")

# Step 3: test the API
data = json.dumps({
    "model": "MiniMax-M2.7",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 5
}).encode()

req = urllib.request.Request(
    "https://api.minimaxi.com/v1/chat/completions",
    data=data,
    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read())
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"\n✓  API call OK: {content[:60]}")
except urllib.error.HTTPError as e:
    body = json.loads(e.read().decode())
    err = body.get('error', {})
    print(f"\n✗  HTTP {e.code}: {err.get('message', str(body)[:100])}")
    sys.exit(1)
except Exception as e:
    print(f"\n✗  Error: {e}")
    sys.exit(1)