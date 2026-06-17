---
name: macos-system-admin
description: >
  macOS system administration — performance audits, keyboard shortcut
  management, System Settings automation, process/launchd control,
  and general Mac tuning. Load when asked to check performance,
  modify shortcuts, toggle system preferences, or manage launchd
  services.
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [macos, system, performance, shortcuts, launchd]
    category: apple
    related_skills: [macos-computer-use]
---

# macOS System Administration

General Mac system tasks: performance audits, hotkey management,
System Settings tweaks, launchd service control.

## Performance Audit

When the user asks to check performance, run this sequence in parallel
batches where possible:

### Batch 1: Hardware + System Overview
```bash
system_profiler SPHardwareDataType SPSoftwareDataType SPStorageDataType
```
Key data: Model, CPU, RAM, SSD free/health, macOS version, uptime.

### Batch 2: Resource Usage
```bash
top -l 1 -n 20 -o cpu -stats pid,command,cpu,mem,power
ps aux -r | head -20          # macOS uses `-r` not `--sort`
memory_pressure
vm_stat
pmset -g therm 2>/dev/null    # thermal throttle state
```

### Batch 3: Startup + Services
```bash
ls -la ~/Library/LaunchAgents/
osascript -e 'tell application "System Events" to get name of every login item'
launchctl list | grep -v com.apple. | head -30
```

### Batch 4: Visual Effects + Displays
```bash
defaults read com.apple.universalaccess reduceMotion
defaults read com.apple.universalaccess reduceTransparency
system_profiler SPDisplaysDataType
```

### Batch 5: Docker/VM
```bash
ps aux | grep -iE "docker|colima|utm|parallels|virtualbox|lima" | grep -v grep
```

### Common Issues + Fixes

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| Sluggish UI, WindowServer high | Transparency ON | Enable Reduce Transparency |
| Sluggish UI, WindowServer high | Dynamic wallpaper | Switch to static image |
| Intermittent stutter | AMD discrete GPU active | Stop GPU-triggering apps (Chrome GPU, VMs) |
| Hot + slow (Intel i9) | Thermal throttling | Check `pmset -g therm`, reduce load |
| High idle CPU | Hermes gateways idle-spinning | `hermes --profile X gateway stop` |
| Memory pressure with swap | Colima/Docker VM running | `colima stop` when unused |

## Keyboard Shortcut Management

macOS symbolic hotkeys live in:
`/Users/<user>/Library/Preferences/com.apple.symbolichotkeys.plist`

Key numbering for screenshots:
- **28**: Copy picture of selected area to clipboard
- **29**: Copy picture of screen to clipboard
- **30**: Save picture of selected area as file
- **31**: Save picture of screen as file

Modifier values:
- Cmd = 1048576 (2^20)
- Shift = 131072 (2^17)
- Option = 524288 (2^19)
- Control = 262144 (2^18)

See `references/symbolic-hotkeys.md` for the plistlib manipulation pattern.

### Pitfalls
- Single-modifier + letter key combos (e.g. Option+A) are captured by
  text input and will NOT trigger hotkeys. Must include Cmd.
- `defaults write` is blocked by TCC on macOS 26 Sequoia for protected
  domains. Use `plutil` or Python `plistlib` on the file directly.
- Changes need `killall SystemUIServer` to take effect.
- Always use absolute path `/Users/<user>/Library/Preferences/...`
  not `~/Library/...` — Hermes sandboxes the home directory.

## Network Configuration: Static IP + Router Reservation

When asked to fix this Mac's LAN IP address, treat it as a two-sided task:

1. macOS-side static/manual IP on the active service, usually Wi-Fi:
   ```bash
   networksetup -listallhardwareports
   route -n get default
   networksetup -getinfo Wi-Fi
   networksetup -setmanual Wi-Fi <ip> <subnet-mask> <router>
   networksetup -setdnsservers Wi-Fi <dns1> <dns2>
   ```
2. Router-side reservation/binding so DHCP does not allocate that IP elsewhere.
   For TP-Link TL-XDR3050, this may live under 应用管理 → 已安装应用 → IP与MAC绑定, not under DHCP Server.
   See `references/tplink-dhcp-reservation.md` for the verified TL-XDR3050 workflow and pitfalls.
3. Verify both sides before reporting success:
   ```bash
   networksetup -getinfo Wi-Fi
   route -n get default
   curl -I --connect-timeout 5 --max-time 10 https://www.apple.com 2>/dev/null | head -n 1
   ```

Pitfalls:
- Convert MAC address format as needed: macOS shows `3c:22:...`; TP-Link UI commonly displays/accepts `3C-22-...`.
- If direct DOM assignment in the router UI does not persist, use normal `browser_type` on each textbox and then click 保存.
- A short-lived `ping` failure after network changes is not conclusive; verify route, DNS, router HTTP, and external HTTPS.

## Process & launchd Control

### Hermes Gateways
```bash
# Stop a profile's gateway (persistent, won't auto-restart)
hermes --profile <name> gateway stop

# Check status
hermes --profile <name> gateway status
```

Gateway processes idle-spin at ~69% CPU each. Stop any profile's
gateway that isn't actively needed. It won't restart until manually
started or profile is re-initialized.

### Colima / Docker
```bash
colima status          # check
colima stop            # stop VM, frees ~5GB RAM + CPU
docker ps              # what's running inside
```

## Control Center / Menu Bar Customization

Unlike Accessibility settings, **Control Center preferences are NOT TCC-protected**.
`defaults write com.apple.controlcenter` works directly on macOS 26+ —
no AppleScript workaround needed. Restart ControlCenter after writing.

### Available NSStatusItem keys

| Key | Effect |
|-----|--------|
| `"NSStatusItem Visible FastUserSwitching"` | Show username/avatar in menu bar |
| `"NSStatusItem Visible Battery"` | Battery percentage / icon |
| `"NSStatusItem Visible WiFi"` | Wi-Fi icon |
| `"NSStatusItem Visible Bluetooth"` | Bluetooth icon |
| `"NSStatusItem Visible Sound"` | Volume icon |
| `"NSStatusItem Visible Clock"` | Clock display |

### Enable Fast User Switching (show username in top-right)

```bash
defaults write com.apple.controlcenter "NSStatusItem Visible FastUserSwitching" -bool true
killall ControlCenter
```

Verify:
```bash
defaults read com.apple.controlcenter "NSStatusItem Visible FastUserSwitching"
# Returns: 1
```

### Pitfalls

- ControlCenter restarts automatically after `killall` — the menu bar item appears instantly.
- The popup button in System Settings → Control Center is named "快速用户切换" (Chinese locale) and has name `"快速用户切换"` in AppleScript — clicking it opens a submenu rather than directly revealing menu items, making AppleScript automation unreliable for this specific toggle. Prefer `defaults write`.
- Other `com.apple.*` domains like `com.apple.universalaccess` ARE TCC-protected — `defaults write` fails silently there. This section only applies to `com.apple.controlcenter`.

## System Settings Automation (AppleScript Fallback)

When `defaults write` is blocked by TCC (macOS 26+), use AppleScript
UI automation. See `references/applescript-system-settings.md` for
the full pattern.

Quick reference:
```bash
# Open a specific pane
open "x-apple.systempreferences:com.apple.preference.universalaccess?Seeing_Display"

# Find and click a checkbox
osascript -e '
tell application "System Events"
  tell process "System Settings"
    tell window 1
      repeat with e in (entire contents)
        if class of e is checkbox and name of e contains "目标文字" then
          click e
        end if
      end repeat
    end tell
  end tell
end tell'
```
