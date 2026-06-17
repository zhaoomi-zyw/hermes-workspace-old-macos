---
name: macos-optimization
description: >
  Diagnose and fix macOS performance issues — high CPU/Windowerver, memory pressure,
  thermal throttling, unnecessary background services, visual effects tuning,
  keyboard shortcut customization, and general system optimization.
version: 1.0.0
platforms: [macos]
metadata:
  hermes:
    tags: [macos, performance, optimization, system-settings]
    category: apple
---

# macOS Performance Optimization

Use when the user reports system slowness, asks for a performance audit, or
wants to optimize their Mac. Covers diagnostics, visual-effects tuning, service
management (launchd, Hermes gateways), and keyboard-shortcut customization.

## 1. Performance audit — diagnostic commands

Run these in parallel for a first-pass overview:

```bash
# Hardware + storage
system_profiler SPHardwareDataType SPSoftwareDataType SPStorageDataType

# Top CPU consumers
top -l 1 -n 20 -o cpu -stats pid,command,cpu,mem,power

# Memory consumers (BSD-style: -r = sort by mem; use ps aux -r, NOT --sort)
ps aux -r | head -20

# Memory pressure
memory_pressure

# Battery + thermal (note: pmset -g thermlog on newer macOS, not -g therm)
pmset -g batt; pmset -g thermlog

# GPU and display info
system_profiler SPDisplaysDataType

# Launchd non-Apple services
launchctl list 2>/dev/null | awk '$1 !~ /^PID$|^-/ && $3 !~ /com\.apple\./ {print}'

# ColorSync display profiles
ls /Library/ColorSync/Profiles/Displays/
```

## 2. Key areas to inspect

### 2.1 Launchd services (background daemons)
```bash
launchctl list 2>/dev/null | awk '$1 !~ /^PID$|^-/ && $3 !~ /com\.apple\./ {print}'
ls -la ~/Library/LaunchAgents/
```

### 2.2 Hermes gateways (common CPU hogs)

Look for `hermes_cli.main --profile * gateway run` in `ps aux`. Stop unused profiles:
```bash
hermes --profile <name> gateway stop
```

**⚠️ Do NOT use `HERMES_PROFILE=<name>` env var** — it will stop the WRONG gateway.
Always pass `--profile` as a CLI flag. Verify with:
```bash
launchctl list | grep hermes.gateway
ps aux | grep "hermes_cli.main.*gateway" | grep -v grep
```

Never use `kill` directly — launchd auto-restarts. Use `hermes gateway stop`.
The launchd label format is `ai.hermes.gateway-<profile>`.

### 2.3 WindowServer / visual effects
WindowServer above 15% CPU usually means transparency effects are active on a
high-resolution display. Check current settings:
```bash
defaults read com.apple.universalaccess reduceMotion
defaults read com.apple.universalaccess reduceTransparency
```

### 2.4 Virtual machines (Docker/Colima/UTM)
```bash
ps aux | grep -iE "docker|colima|lima|utm|qemu"
colima status
docker ps
```

**Full Colima/Docker cleanup** (when deleting a project that uses Docker):
```bash
# 1. Stop containers
docker stop <container1> <container2>

# 2. Remove containers
docker rm <container1> <container2>

# 3. Remove volumes (or use docker volume prune)
docker volume rm <volume1> <volume2>

# 4. Stop Colima VM
colima stop

# 5. Delete project directory
rm -rf <project-path>
```

### 2.5 External displays / GPU
```bash
system_profiler SPDisplaysDataType
```
Discrete GPU (AMD Radeon) on Intel Macs triggers thermal throttling when engaged.
Check which GPU is active and what's triggering the dGPU.

## 3. Common fixes

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| WindowServer high CPU | Transparency effects on HiDPI | Enable "Reduce Transparency" |
| Intermittent stutter | dGPU → thermal throttle | Force integrated GPU, stop GPU-triggering apps |
| High idle CPU | Unused Hermes gateways | `hermes --profile X gateway stop` |
| Memory pressure | Colima/Docker VM | `colima stop` when not using Docker |
| Sluggish after weeks | Kernel/page cache bloat | Reboot (62-day uptime isn't unusual) |

## 4. Modifying protected settings (macOS 26+ TCC)

`defaults write com.apple.universalaccess` and `com.apple.Accessibility` are
blocked by TCC in macOS Sequoia. You CANNOT write to them from the terminal.

**Workaround: use AppleScript to click the UI in System Settings.**

Step-by-step pattern:
```applescript
# 1. Open the settings pane
open "x-apple.systempreferences:com.apple.preference.universalaccess?Seeing_Display"

# 2. Find the checkbox by searching entire contents
tell application "System Events"
  tell process "System Settings"
    tell window 1
      set allElem to entire contents
      repeat with e in allElem
        if class of e is checkbox and (name of e) contains "降低透明度" then
          click e
        end if
      end repeat
    end tell
  end tell
end tell
```

Key AppleScript patterns:
- `entire contents` traverses the full UI hierarchy — use this, not `every checkbox of window 1` (which only checks direct children)
- Variable name `result` is reserved in AppleScript — never use it. Use `outputStr`, `res`, etc.
- Always wrap `name of e` and `value of e` in `try` blocks (many elements don't have names)
- After clicking, verify: `value of e` returns 0 or 1 for checkboxes
- Check page title with `name of static text 1 of window 1`
- Open the correct sub-pane first before searching: `open "x-apple.systempreferences:com.apple.preference.universalaccess?Seeing_Display"`

See `references/applescript-checkbox-discovery.md` for ready-to-run discovery scripts.

### Key settings and their checkbox names (Chinese locale)

| Setting | Checkbox name | Pane URL |
|---------|--------------|----------|
| Reduce Transparency | 降低透明度 | `?Seeing_Display` |
| Reduce Motion | 减弱动态效果 | `?Seeing_Display` |
| Increase Contrast | 增强对比度 | `?Seeing_Display` |
| Auto Brightness | 自动调节亮度 | Displays pane |
| True Tone | 原彩显示 | Displays pane |

## 5. Keyboard shortcut customization

Custom shortcuts are stored in `~/Library/Preferences/com.apple.symbolichotkeys.plist`
under the `AppleSymbolicHotKeys` dictionary.

Screenshot keys:
| Key | Action |
|-----|--------|
| 28 | Copy picture of selected area to clipboard |
| 29 | Copy picture of screen to clipboard |
| 30 | Save picture of selected area as a file |
| 31 | Save picture of screen as a file |

Modifier values:
| Modifier | Value |
|----------|-------|
| Command  | 1048576 (2^20) |
| Shift    | 131072 (2^17) |
| Option   | 524288 (2^19) |
| Control  | 262144 (2^18) |

Add them together. Example — Cmd+Shift+Q (keycode 12) for screenshot to clipboard:
```python
hotkeys['28'] = {
    'enabled': True,
    'value': {
        'parameters': [12, 1048576 + 131072, 0],
        'type': 'standard'
    }
}
```

After modifying the plist, restart SystemUIServer:
```bash
killall SystemUIServer
```

**NEVER override Cmd+A** — it's the universal "Select All" shortcut used by
virtually every macOS app. ⚠️ Cmd+Shift+Q is normally "Log Out"; overriding it
is acceptable but warn the user.

See `references/keyboard-keycodes.md` for a keycode reference table.
See `references/applescript-checkbox-discovery.md` for ready-to-run checkbox discovery scripts.

## Pitfalls

- **`defaults write com.apple.universalaccess` fails silently** in macOS 26+.
  TCC blocks writes to accessibility domains. Use AppleScript GUI scripting instead.
- **Never `kill` a launchd-managed process** — it auto-restarts. Use `launchctl bootout`
  or the app's own stop command (e.g. `hermes gateway stop`).
- **`ps` flags differ on macOS vs Linux** — use BSD-style: `ps aux -r` for memory sort.
- **`sudo` requires a TTY** in most Hermes terminal backends. Use `-S` with a password,
  or avoid sudo altogether when possible.
- **Hermes resolves `~` to its profile home**, not `/Users/omi`. Use absolute paths
  (`/Users/omi/Library/...`) for system files.
- **AppleScript `result` is a reserved keyword** — use a different variable name.
- **Dynamic wallpapers (WallpaperAerialsExtension)** consume 5-10% CPU continuously.
  Switch to a static image if idle CPU matters.
- **Screenshot shortcut conflicts**: NEVER override:
  - `Cmd+A` (universal Select All)
  - `Ctrl+A` (jump to line start in all text editors)
  - `Cmd+Shift+W` (close window in many apps)
  - `Cmd+Shift+Q` (system Log Out — acceptable to override but warn user)
  - `Option+<letter>` may conflict with character input (e.g. Option+A → å on US layout)
  Safe alternatives: `Cmd+Shift+A`, `Cmd+Option+A`, `Cmd+Shift+1`

## Verification

After applying fixes, run:
```bash
top -l 1 -n 10 -o cpu -stats pid,command,cpu | head -15
```
Compare CPU idle % and load average before/after. Target: idle > 85%.
