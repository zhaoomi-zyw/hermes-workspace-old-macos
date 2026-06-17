---
name: network-diagnostics
description: Diagnose upload/download traffic on macOS and home routers — per-process monitoring, interface stats, router investigation, and ISP data reconciliation.
---

# Network Diagnostics

Use this skill when the user asks to:
- Investigate upload/download traffic on their Mac
- Find which apps are consuming bandwidth
- Reconcile local traffic stats with ISP data
- Investigate home router traffic/device statistics

## Trigger conditions
- "check upload traffic", "what's using bandwidth", "network usage", "data cap exceeded"
- ISP warning about traffic limits
- Router device/traffic investigation

## Step 1: macOS per-process network monitoring

```bash
# TCP traffic (cumulative since process start)
nettop -x -P -m tcp -J bytes_out,bytes_in -n -l 1

# UDP traffic
nettop -x -P -m udp -J bytes_out,bytes_in -n -l 1

# Interface-level cumulative stats (since boot)
netstat -ib
```

**Key pitfalls:**
- `nettop` only shows CURRENTLY RUNNING processes. Processes that exited (or restarted) are missed.
- Process cumulative bytes reset on restart. A process running since Apr includes pre-June traffic.
- Always cross-check interface stats against process stats — if the gap is huge, something exited or restarted.
- To identify what a process is: `ps -p <PID> -o lstart,pid,args`

## Step 2: Interface-level reconciliation

Parse `netstat -ib` to get total upload since boot:
- Active interfaces are marked `status: active` in `ifconfig`
- Obytes = total outbound bytes since boot
- On M-series Macs: `en0` is WiFi, `en5` may be virtual/Thunderbolt bridge

Compare interface totals vs ISP reported usage. If ISP reports 10x+ what interfaces show, the traffic is from **other devices on the same network**, not this Mac.

## Step 3: Router investigation

See `references/tplink-router-api.md` for TP-Link router API details: authentication flow, stok extraction via `$.session`, Canvas UI limitation, common endpoints from `menu.js`, API call format, and error codes (-40401, -40101, -40210).

General router approaches:
- Try browser to `http://192.168.1.1`
- Many consumer routers (including TP-Link TL-XDR3050) do NOT track per-device historical traffic — they only show real-time
- Fallback: use ARP table (`arp -a`) for connected device list
- ISP apps (中国移动APP, etc.) often have per-device breakdowns that routers lack

## Step 4: Check for VPN/tunnel software

Common bandwidth-intensive services:
- Tailscale (exit node, DERP relay) — `tailscale status`
- Cloud backup/sync (iCloud `bird`, Dropbox, 百度网盘, etc.)
- P2P (aria2, qBittorrent, Transmission, 迅雷)
- Docker VM networking (Lima/Colima `limactl`)

```bash
# Check for Tailscale
ps aux | grep -i tailscale
systemextensionsctl list | grep -i tailscale

# Check for backup/sync
ps aux | grep -iE "bird|backupd|dropbox|onedrive|baidu|syncthing"
```

## Step 5: Present findings

Always include:
1. Per-app ranking with human-readable sizes
2. Process start times (to show coverage of the target period)
3. Interface totals for cross-reference
4. If ISP vs local mismatch > 10x: state clearly that traffic is from other devices
5. Router device list (ARP or router UI)
6. Practical next steps (检查其他设备, 中国移动APP, Tailscale排查)
