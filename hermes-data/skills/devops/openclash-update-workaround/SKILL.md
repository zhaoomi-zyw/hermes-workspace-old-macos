---
name: openclash-update-workaround
description: Update luci-app-openclash on iStoreOS when GitHub is blocked and opkg feed is corrupted
---

# OpenClash Update Workaround for iStoreOS

## Context
When updating luci-app-openclash on iStoreOS/OpenWRT, standard `opkg update && opkg install` may fail due to:
1. Corrupted opkg feed URLs
2. GitHub.com being inaccessible from the router

## Symptoms
- `opkg list-upgradable | grep openclash` returns nothing even though a newer version exists
- `curl -L https://github.com/...` times out on the router
- After upgrade, OpenClash core fails to start with "[Warning] OpenClash Now Disabled, Need Start From Luci Page, Exit..."

## Root Causes
1. **Feed URL corrupted**: `/etc/opkg/compatfeeds.conf` has truncated URL (e.g. `https://istore.istoreos.com/repo/all/compatroot@iStoreOS` instead of `https://istore.istoreos.com/repo/all/compat`)
2. **GitHub blocked**: `github.com` direct downloads timeout, but `api.github.com` may work (proxied)
3. **Dual enable flags**: OpenClash uses BOTH `config.enabled='1'` AND `config.enable='1'` — the second one controls whether the core starts

## Fix Procedure

### Step 1: Fix corrupted opkg feed
```bash
echo "src/gz istore_compat https://istore.istoreos.com/repo/all/compat" > /etc/opkg/compatfeeds.conf
opkg update
```

### Step 2: Download ipk via proxy
Direct GitHub download from router fails. Use `ghfast.top` proxy:
```bash
curl -L --max-time 120 -o /tmp/openclash.ipk "https://ghfast.top/https://github.com/vernesong/OpenClash/releases/download/v0.47.088/luci-app-openclash_0.47.088_all.ipk"
```
Note: `ghproxy.com` returns HTML instead of the file. `mirror.ghproxy.com` also times out.

### Step 3: Get latest version URL
```bash
# On any machine with api.github.com access:
curl -sL "https://api.github.com/repos/vernesong/OpenClash/releases/latest" | grep browser_download_url | grep ipk
```

### Step 4: Install with force-overwrite
```bash
/etc/init.d/openclash stop
opkg install --force-overwrite /tmp/openclash.ipk
```

### Step 5: Fix BOTH enable flags
```bash
# These are DIFFERENT settings — both must be 1
uci set openclash.config.enabled=1   # 插件启用状态
uci set openclash.config.enable=1    # 核心启动开关
uci commit
/etc/init.d/openclash start
```

## Verification
```bash
ps | grep clash | grep -v grep        # core process running
netstat -tlnp | grep -E "7890|7891|9090"  # ports listening
curl -s http://127.0.0.1:9090/proxies -H "Authorization: Bearer <dashboard_password>" | head -c 200
```

## Key Lessons
- Always check BOTH `enabled` AND `enable` UCI flags — they control different things
- `ghfast.top` is the reliable GitHub proxy in China; others (`ghproxy.com`, `mirror.ghproxy.com`) are unreliable or broken
- `objects.githubusercontent.com` is reachable but returns 404 for direct asset URLs without valid signed cookies
