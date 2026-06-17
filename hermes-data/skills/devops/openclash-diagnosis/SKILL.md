---
name: openclash-diagnosis
description: Diagnose OpenClash node failures by analyzing runtime logs and LuCI web interface — identify TLS cert errors, connection issues, subscription problems, and service-not-running conditions.
---

# OpenClash Diagnosis Skill

## Trigger
OpenClash is running but all/some proxy nodes fail — connection errors, TLS certificate errors, nodes appear dead.

## Diagnostic Steps

### 1. Check OpenClash Log via SSH
```bash
ssh root@<router_ip> "cat /tmp/openclash.log | tail -100"
```

Or via the LuCI web interface:
- Services → OpenClash → 运行日志 → 插件日志

### 2. Common Error Patterns

**TLS Certificate Errors** (most common with subscription nodes):
```
tls: failed to verify certificate: x509: certificate is not valid for any names
```
→ Nodes' certificates have expired/changed. Solution: refresh subscription.

**MMDB Database Invalid** (causes core to crash/never fully start):
```
level=warning msg="MMDB invalid, remove and download"
```
→ The Country.mmdb file is corrupted (file size too small, e.g. 53/104 bytes instead of ~200KB). Core starts but doesn't listen on any ports. Fix: run `/usr/share/openclash/openclash_ipdb.sh` to redownload the correct MMDB.

**Core Starts But No Ports Listening**:
```
ps aux | grep clash  # shows process running but ss -lnp | grep 7890 shows nothing
```
→ Usually caused by corrupted MMDB or config syntax error. Check `/tmp/openclash.log` for the MMDB error above.

**Connection Refused / Timeout**:
```
error: connection refused
```
→ Node server is down or network blocked. Try updating subscription.

**DNS Resolution Failures**:
```
dial tcp: lookup xxx: no such host
```
→ DNS issues, check router DNS settings.

### 3. Verify Core is Actually Running

After starting OpenClash, verify ports are actually listening (not just process existing):
```bash
ssh root@<router_ip> "ss -lnp | grep -E '7890|7891|9090'"
```

Expected: `:::7890`, `:::7891`, `:::9090` all show LISTEN. If process exists but no ports, core crashed — check MMDB error above.

### 4. Solution: Refresh Subscription
In LuCI:
1. Go to Services → OpenClash → 配置订阅
2. Find the failing config (e.g., SSRDOG.yaml)
3. Click 刷新 (refresh) button
4. If "订阅信息获取失败" persists, check:
   - Is the subscription URL accessible from the router's network? (see Section 7 for CDN issue)
   - Is the conversion service responding? (try Section 6 alternatives)

### 10. Version Check
GeoSite.dat can also become corrupted (much larger than normal, e.g. 38MB instead of ~10MB, or cause rule matching failures). Use OpenClash's built-in script or download manually:

```bash
# Option 1: OpenClash built-in script (preferred)
ssh root@<router_ip> "/usr/share/openclash/openclash_geosite.sh"

# Option 2: Manual download via ghproxy.net (if GitHub is blocked)
ssh root@<router_ip> "curl -L 'https://ghproxy.net/https://github.com/Loyalsoldier/v2ray-rules-dat/releases/download/YYYYMMDDHHMM/geosite.dat' -o /etc/openclash/GeoSite.dat"
```

Verify: `ls -la /etc/openclash/GeoSite.dat` should show ~10-11MB.

### 6. Subscription Conversion Service Failures

If subscription refresh returns HTTP 400 error, the conversion service URL is dead. Common services:
- `https://api.wcc.best` — often returns 400, deprecated
- `https://api.asailor.org` — working alternative
- `https://sub.id` — also works

To update the conversion service in your config:
```bash
ssh root@<router_ip> "sed -i 's/api\.wcc\.best/api.asailor.org/g' /etc/openclash/config/YOUR_CONFIG.yaml"
```

### Git Push Hangs/Times Out Due to Fake-IP

**Symptom:** `git push` to GitHub hangs indefinitely or times out, but `curl https://github.com` returns 200 instantly.

**Diagnostic:** Check the DNS resolution:
```bash
nslookup github.com
# Returns 198.18.x.x → Fake-IP active
```

Or check git trace:
```bash
GIT_TRACE=1 git push origin main 2>&1 | grep "Trying"
# Shows "Trying 198.18.0.14:443"
```

**Root cause:** The same Fake-IP mechanism that blocks CDN subscriptions also blocks git's HTTPS transport. The git protocol establishes a persistent connection that routes through the Fake-IP, while ephemeral curl requests may route correctly through proxy rules.

**Workaround:** Use GitHub's Contents API via curl to push files directly (bypasses git protocol entirely). See the `github-repo-management` skill's Known Pitfalls section for the exact API call.

### 7. CDN Subscription URLs — China-Only Access Problem

**Critical**: Many Chinese VPN providers use CDN URLs like `*.aliyuncs-file.com` or `*.com.cn` domains that are **only accessible from within China**. When managing OpenClash from overseas:
- DNS resolves to 198.18.x.x (Clash Fake-IP) but the CDN is unreachable from abroad
- This causes subscription download to hang/fail
- The core runs but all nodes fail with timeout

**Symptoms**:
```
error: connection timeout
dial tcp: i/o timeout
```

**Solution**: You need a globally accessible subscription URL. Options:
1. Get a direct node configuration (not through CDN) from your VPN provider
2. Access the router from within China and refresh the subscription there
3. Ask your VPN provider for a non-CDN subscription URL

There is no workaround from overseas — the CDN must be reachable.

### 8. Provider File Format

When downloading a subscription directly as a provider file, ensure it contains only `proxies:` and `proxy-providers:` sections — NOT a full Clash config. A full config has sections like `port:`, `socks-port:`, `allow-lan:`, `mode:`, etc. A provider file should only have the proxy definitions.

### 6. Fix MMDB Corruption

If `Country.mmdb` is corrupted, the core will crash on startup. DO NOT manually curl from random GitHub URLs — use OpenClash's own script:

```bash
ssh root@<router_ip> "/usr/share/openclash/openclash_ipdb.sh"
```

Then verify the file size is ~200KB:
```bash
ssh root@<router_ip> "ls -la /etc/openclash/Country.mmdb"
```

Expected output: `-rw-r--r-- 1 root root 203xxx Apr 30 ... /etc/openclash/Country.mmdb`

### 9. If opkg Update Fails (Empty Reply)
```
curl: (52) Empty reply from server
```
→ The iStoreOS package repo is unreachable. Try:
```bash
ssh root@<router_ip> "opkg update --force_checksum"
```
Or use a different iStoreOS repo source.

### 5. Diagnose via LuCI Web Interface (when SSH is unavailable)

When SSH is blocked but LuCI is accessible (http://router_ip/cgi-bin/luci):

**OpenClash service status page** — Services → OpenClash → 运行状态 (or direct URL):
- Shows all nodes: TCP/UDP/DNS status at top ("未运行" = not running, "运行中" = running)
- Shows subscription traffic used/total GB and expiration date
- "正在收集数据中..." = service not running

**Basic settings page** — Services → OpenClash → 基本设置:
- Top status cards show TCP/UDP/DNS — all "未运行" means service is down
- Main switch checkbox (主开关) — must be checked
- TCP node / UDP node dropdowns — if both show "关闭" (closed), no proxy is assigned
- DNS forwarding in Dnsmasq: `127.0.0.1#7874` means Dnsmasq forwards to OpenClash

**Restart from LuCI**: Click "重启" button on the OpenClash status page.

**Key diagnostic paths in LuCI**:
- Services → OpenClash → 运行状态 — overall status, node list, traffic stats
- Services → OpenClash → 基本设置 — main switch, node assignment, DNS settings
- Network → DHCP/DNS → 转发 — shows upstream DNS forwarding (e.g., 127.0.0.1#7874)

**Common symptom**: Main switch is ON but all services show "未运行" — the core isn't actually running. This happens when:
- No TCP/UDP node is assigned (both set to "关闭")
- Subscription exhausted (traffic at 89-100%)
- Config file outdated or invalid

### 6. When OpenClash Won't Start Despite Enabled Switch

Even with the main switch ON, OpenClash may not run if:
1. **No proxy node assigned** — TCP and UDP nodes both show "关闭"
2. **Subscription exhausted** — traffic quota used up (check status page)
3. **Config file corrupted or missing** — core crashes silently

Solution: Assign a node manually via 基本设置 → TCP 节点 dropdown, then restart.

## Key Files
- `/tmp/openclash.log` — main OpenClash runtime log
- `/etc/config/openclash` — LuCI config
- `/etc/openclash/` — config directory

## Version Check
```bash
ssh root@<router_ip> "opkg list-installed | grep openclash"
```

---

## Traffic Control: Rate-Limiting OpenClash Upload via tc

When OpenClash is consuming too much upload bandwidth and hitting ISP caps, use Linux `tc` (traffic control) to hard-cap the WAN interface's outbound rate.

### Install tc (one-time, survives reboots)

Most OpenWRT/iStoreOS builds ship `kmod-sched-core` (the kernel module) but NOT the `tc` userspace tool. Install it:

```bash
ssh root@<router_ip> "opkg update && opkg install tc"
```

Verify: `which tc` should print `/sbin/tc`.

### Choose a Rate Limit

Calculate based on remaining ISP quota and days left in the billing cycle:

```
Remaining GB / days / 86400 * 8 * 1024^2 = Mbps limit
```

Example: 524 GB remaining, 17 days → `524/17/86400*8*1024^2 ≈ 2.8 Mbps` (theoretical minimum to stay under cap). In practice, use 3-5× this because actual usage is well below the cap. Typical recommendation: **15 Mbps** — allows 4K streaming through the proxy while keeping daily upload ≤ ~80 GB under real-world usage patterns.

### Apply the Limit

```bash
# Create HTB qdisc on the WAN interface (eth0)
tc qdisc add dev eth0 root handle 1: htb default 30

# Parent class with the rate cap
tc class add dev eth0 parent 1: classid 1:1 htb rate 15mbit ceil 15mbit

# Leaf class that all traffic goes through
tc class add dev eth0 parent 1:1 classid 1:10 htb rate 15mbit ceil 15mbit

# Filter: match ALL outbound IP traffic
tc filter add dev eth0 protocol ip parent 1:0 prio 1 u32 match ip src 0.0.0.0/0 flowid 1:10
```

### Verify It's Working

```bash
tc -s qdisc show dev eth0
```

Look for `overlimits > 0` — that means packets are being rate-limited. Also verify on the LuCI dashboard (首页) — the real-time upload rate should cap at the configured limit.

### Remove / Adjust the Limit

```bash
# Remove entirely
tc qdisc del dev eth0 root

# Adjust rate (change, don't re-add)
tc class change dev eth0 parent 1:1 classid 1:1 htb rate 20mbit ceil 20mbit
tc class change dev eth0 parent 1:1 classid 1:10 htb rate 20mbit ceil 20mbit
```

### Persist Across Reboots

tc rules are lost on reboot. Options:

**Option A — Manual (easiest):** In LuCI → 系统 → 启动项 → 本地启动脚本, add the four `tc` commands from above before `exit 0`.

**Option B — Init script:** Create `/etc/init.d/qos-upload` with START=99, then `enable` it. (May be blocked by SSH security policies in automated environments — use Option A via WebUI instead.)

**Option C — @reboot cron:** In LuCI → 系统 → 计划任务, add:
```
@reboot sleep 30 && tc qdisc add dev eth0 root handle 1: htb default 30 && tc class add dev eth0 parent 1: classid 1:1 htb rate 15mbit ceil 15mbit && tc class add dev eth0 parent 1:1 classid 1:10 htb rate 15mbit ceil 15mbit && tc filter add dev eth0 protocol ip parent 1:0 prio 1 u32 match ip src 0.0.0.0/0 flowid 1:10
```

### Pitfalls

- **`tc: not found`**: Install it with `opkg install tc`. The kernel module (`kmod-sched-core`) is usually pre-installed.
- **`RTNETLINK answers: File exists`**: A qdisc already exists. Use `tc qdisc change` instead of `add`, or delete first with `tc qdisc del dev eth0 root`.
- **Limit applies to ALL eth0 outbound traffic**, including non-Clash services (Samba, alist, etc.). If you need per-service shaping, use more complex tc filters (match by destination port, mark via iptables, etc.).
- **WebUI "本地启动脚本" tab may not respond to automated clicks**: This is a known issue with the Argon theme's JavaScript. Use browser console or SSH instead.

---

## Diagnosing Excessive Bandwidth Consumption (ISP Upload Limit Alerts)

When the ISP reports hundreds of GB of upload traffic but no single device seems responsible, OpenClash transparent proxy is the prime suspect — it aggregates ALL household overseas traffic and funnels it through the router's WAN interface.

### Diagnostic Flow: Mac → Router → Soft Router

**Step 1: Rule out the local Mac first.**
```bash
# Per-process cumulative upload (only currently-running processes)
nettop -x -P -m tcp -J bytes_out -n -l 1 2>/dev/null | tail -n +2
# Interface-level cumulative since boot
netstat -ib | grep -E "^en[0-9]"
# LAN device list
arp -a
```
A Mac showing ~20 GB over 60 days while ISP reports 500 GB in 13 days → culprit is elsewhere.

**Step 2: Check the iStoreOS/OpenWRT soft router's WAN interface.**
SSH in and check `/proc/net/dev` for eth0 (WAN) TX bytes:
```bash
ssh root@<router_ip> "cat /proc/net/dev | grep eth0"
```
Compare TX bytes against the router's uptime to estimate daily upload rate.

**Step 3: Verify OpenClash is the bandwidth driver.**
```bash
# Count active Clash proxy connections
ssh root@<router_ip> "netstat -tunp 2>/dev/null | grep clash | wc -l"
# Check which LAN devices are using the proxy
ssh root@<router_ip> "netstat -tunp 2>/dev/null | grep clash | awk '{print \$5}' | cut -d: -f1 | sort | uniq -c | sort -rn"
```
100+ active connections, all from devices on the LAN → OpenClash is proxying all overseas traffic.

**Step 4: Check real-time rates via LuCI web UI.**
Navigate to 状态 → 实时信息 → 流量 tab. Each network interface (br-lan, eth0, eth1, docker0) shows 3-minute average inbound/outbound rates with peaks. Look for interfaces with sustained MiB/s-level outbound averages.

### Interpretation

If eth0 (WAN) shows cumulative TX in the hundreds of GB range and real-time averages are 1+ MiB/s upload, OpenClash is the root cause. The upload traffic is NOT from a single app or device — it's the household's aggregated overseas traffic (streaming, social media, downloads) encrypted and forwarded through proxy nodes.

### Solutions

- **Stop the proxy**: `/etc/init.d/openclash stop` and disable in LuCI
- **Limit proxy scope**: Change Clash from transparent proxy (redir-port 7892/tproxy 7895) to explicit proxy on specific devices only
- **Rate-limit on upstream router**: If OpenClash must stay on, QoS-throttle the iStoreOS's WAN IP on the main router
- **Monitor with cron**: Set up a cron job that checks `/proc/net/dev` eth0 TX delta daily and alerts on threshold

### SSH on macOS without sshpass

macOS doesn't ship `sshpass`. Use `expect` for automated password entry:
```bash
expect << 'EOF'
spawn ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 root@<router_ip> "<command>"
expect "password:" { send "<password>\r" }
expect eof
EOF
```
Note: Use `<< 'EOF'` (quoted) to prevent shell variable expansion inside the expect script. For `awk` commands containing `$`, escape them with backslashes inside the expect block.
