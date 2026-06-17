# Multi-Profile WeChat (Weixin/iLink) Setup

## How WeChat accounts are stored

Each WeChat bot account connected via iLink is stored under:
```
<profile>/weixin/accounts/<account_id>@im.bot.sync.json
```

The `.sync.json` file contains `get_updates_buf` (the session token/state blob).
The account ID and token also live in `<profile>/.env` as `WEIXIN_ACCOUNT_ID` and `WEIXIN_TOKEN`.

## Key fact: profiles are isolated

Each profile has its own isolated `.env`. WeChat credentials are **not** shared between profiles. If a profile's gateway logs show:
```
WARNING gateway.run: No messaging platforms enabled.
```
...the profile's `.env` is missing the WeChat credentials, even if other profiles have them.

## Adding WeChat to a new profile

### Prerequisites

You need from an existing connected profile (or a fresh iLink bot):
- `WEIXIN_ACCOUNT_ID` — e.g. `1d3a994e2ef3@im.bot`
- `WEIXIN_TOKEN` — e.g. `1d3a994e2ef3@im.bot:060000aa33208110dc5200a6be8ac2cff7a5e8`
- `WEIXIN_BASE_URL=https://ilinkai.weixin.qq.com`
- `WEIXIN_CDN_BASE_URL=https://novac2c.cdn.weixin.qq.com/c2c`
- `WEIXIN_DM_POLICY=pairing`
- `WEIXIN_ALLOW_ALL_USERS=false`
- `WEIXIN_ALLOWED_USERS=<ilink_user_id>@im.wechat`
- `WEIXIN_HOME_CHANNEL=<ilink_user_id>@im.wechat`

### Steps

**1. Copy credentials to target profile `.env`:**
```bash
grep -E "^WEIXIN_" ~/.hermes/profiles/<source>/.env
# Append all WEIXIN_* vars to target profile's .env
```

**2. Enable WeChat in config.yaml** — add under `platform_toolsets`:
```yaml
platform_toolsets:
  weixin: []
```

**3. Stop existing gateway using that iLink bot** (if any):
The same iLink bot cannot be connected in two profiles simultaneously.
```bash
ps aux | grep "hermes.*<source_profile>" | grep -v grep
kill -9 <pid>
```

**4. Restart the target gateway:**
```bash
launchctl start ai.hermes.gateway-<target>
tail -20 ~/.hermes/profiles/<target>/logs/gateway.log | grep "Connected account="
```

## If the iLink token is expired (errcode=-14)

See `references/wechat-qr-reconnect.md` — full QR re-authentication workflow.

## Checking account status

```bash
# List accounts
ls ~/.hermes/profiles/<profile>/weixin/accounts/

# Check connection state
python3 -c "
import json, os
d = '/Users/omi/.hermes/profiles/<profile>/weixin/accounts/'
for f in sorted(os.listdir(d)):
    if 'sync' in f:
        with open(os.path.join(d, f)) as fh:
            data = json.load(fh)
        print(f'{f}: connected={bool(data.get(\"get_updates_buf\"))}')
"
```