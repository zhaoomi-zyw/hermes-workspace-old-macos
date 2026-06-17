---
name: macos-system-administration
description: macOS system administration — performance diagnostics, system settings
  modification, symbolic hotkey management, display configuration, user account
  management. Load when the user asks about Mac performance, system settings tweaks,
  keyboard shortcuts, display color profiles, or user accounts.
platforms: [macos]
version: 1.0.0
metadata:
  hermes:
    tags: [macos, system-administration, performance, hotkeys, display]
    category: apple
---

# macOS System Administration

System-level macOS operations — diagnostics, settings, hotkeys, displays, users.

## 1. Performance Diagnostics

Run these commands to audit Mac performance:

```bash
# Hardware + OS info
system_profiler SPHardwareDataType SPSoftwareDataType SPStorageDataType

# CPU top consumers (top 20)
top -l 1 -n 20 -o cpu -stats pid,command,cpu,mem

# Memory pressure and stats
memory_pressure && vm_stat

# Battery / thermal
pmset -g batt && pmset -g therm

# Process list sorted by memory
ps aux -r | head -20

# LaunchAgents/Daemons
ls -la ~/Library/LaunchAgents/ /Library/LaunchAgents/ /Library/LaunchDaemons/

# Visual effects settings
defaults read com.apple.universalaccess reduceMotion
defaults read com.apple.universalaccess reduceTransparency
```

**Key red flags:**
- WindowServer > 20% CPU → likely transparency/animation effects
- kernel_task high CPU → thermal throttling (check i9 chassis)
- Colima/VM processes > 4GB RAM → stop when not needed
- Any process running > 24h at high CPU → investigate gateway loops
- Uptime > 30 days → suggest reboot for kernel memory reclamation

## 2. Hermes Gateway Management

Hermes gateways are managed by launchd. Killing with `kill` won't work — launchd restarts them.

```bash
# List all gateways
launchctl list 2>/dev/null | grep hermes

# Stop a profile's gateway
hermes --profile <name> gateway stop

# Uninstall (prevents auto-start on reboot)
hermes --profile <name> gateway uninstall
```

## 3. System Settings Modification on macOS 26+

### The Problem
`defaults write` and `plutil` fail on accessibility/system domains in macOS Sequoia (26.x) due to TCC (Transparency, Consent, and Control) protections. Writing to `com.apple.universalaccess`, `com.apple.Accessibility`, and similar protected domains returns:
```
Could not write domain com.apple.universalaccess; exiting
```
or
```
You don't have permission to save the file
```

### The Solution: AppleScript UI Automation
Use `osascript` + System Events to interact with System Settings via accessibility APIs:

```bash
# 1. Open the correct settings pane
open "x-apple.systempreferences:com.apple.preference.universalaccess?Seeing_Display"

# 2. Wait for UI to load, then find and click the checkbox
osascript -e '
tell application "System Events"
    tell process "System Settings"
        tell window 1
            set allElem to entire contents
            repeat with e in allElem
                try
                    if class of e is checkbox and (name of e) contains "降低透明度" then
                        click e
                    end if
                end try
            end repeat
        end tell
    end tell
end tell'
```

**Key patterns:**
- `entire contents` traverses the full UI hierarchy — avoids nesting guesswork
- Search by Chinese element name (e.g., "降低透明度", "辅助功能", "显示器")
- Always verify with `value of e` before/after click
- `SystemUIServer` restart: `killall SystemUIServer` after plist changes

### Important: AppleScript variable name `result` is reserved
If you use `result` as a variable name in AppleScript, you get `execution error: 变量"result"没有定义。 (-2753)`. Use `outputStr` or any other name.

## 4. Symbolic Hotkey Management

Screenshot shortcuts live in `~/Library/Preferences/com.apple.symbolichotkeys.plist` under `AppleSymbolicHotKeys`.

### Key IDs for Screenshots
| Key | Function |
|-----|----------|
| 28 | Copy picture of selected area to clipboard |
| 29 | Copy picture of screen to clipboard |
| 30 | Save picture of selected area as a file |
| 31 | Save picture of screen as a file |

### Modifier Values
| Modifier | Value |
|----------|-------|
| Cmd | 1048576 |
| Shift | 131072 |
| Option | 524288 |
| Ctrl | 262144 |

Add modifiers together (e.g., Cmd+Shift = 1179648).

### Keycodes for Common Keys
| Key | Keycode |
|-----|---------|
| A | 0 |
| Q | 12 |
| 1 | 18 |

### Read/Write Hotkeys
```python
import plistlib, os

plist_path = f'{os.environ["HOME"]}/Library/Preferences/com.apple.symbolichotkeys.plist'

# Read
with open(plist_path, 'rb') as f:
    data = plistlib.load(f)
hotkeys = data['AppleSymbolicHotKeys']

# Set (e.g., Cmd+Option+1 → screenshot region to clipboard)
hotkeys['28'] = {
    'enabled': True,
    'value': {
        'parameters': [18, 1572864, 0],  # keycode, modifiers, reserved
        'type': 'standard'
    }
}

# Delete (restore default)
del hotkeys['28']

# Write
with open(plist_path, 'wb') as f:
    plistlib.dump(data, f)

os.system('killall SystemUIServer')
```

### Pitfall: Modifier-only shortcuts don't fire
Single modifier + letter (e.g., Option+A, Ctrl+A) is consumed by the text input system for character composition. The hotkey never fires. **Always include Cmd in the modifier stack** (e.g., Cmd+Option+1 works, Option+A doesn't).

### Pitfall: Conflicting default shortcuts
Always check for conflicts before binding:
- `Cmd+A` → Select All (used everywhere)
- `Cmd+Shift+Q` → Log Out (system-level)
- `Cmd+Shift+W` → Close Window (used everywhere)
- `Ctrl+A` → Move to beginning of line (all text editors)

## 5. Display Color Adjustment

External displays with uncomfortable colors are usually:
1. **HDR enabled** — SDR content looks washed out/bright/off-color. Disable HDR in Display Settings for that monitor.
2. **Wrong color profile** — System Settings → Displays → select the external monitor → Color Profile → pick the display-specific one (e.g., "LG HDR 4K") or sRGB.
3. **True Tone** — Turn off for external displays; it's calibrated for the built-in screen.

Find connected displays:
```bash
system_profiler SPDisplaysDataType 2>/dev/null
```

## 6. Docker/Colima Cleanup

```bash
# Stop containers
docker stop <container1> <container2>

# Remove containers
docker rm <container1> <container2>

# Remove volumes
docker volume ls | grep <project>
docker volume rm <volume1> <volume2>

# Stop the VM
colima stop

# Delete project
rm -rf <project_path>
```

## 7. User Account Management

Creating new users: System Settings → Users & Groups → unlock → Add User.
Switching users: menu bar top-right user name → select other user, or lock screen (Ctrl+Cmd+Q) and pick user at bottom.

## Pitfalls

1. **`sudo` in automation**: Commands requiring sudo will fail in the terminal tool unless the user has configured passwordless sudo or an askpass helper. Installers like Logi Options+ that call `sudo` inside their script need the user to run them manually in their own Terminal.

2. **Path resolution in Hermes**: `~` resolves to `~/.hermes/profiles/main/home/` in the sandbox. Use absolute paths like `/Users/<username>/Library/...` for system files.

3. **`ps` flag differences on macOS**: macOS `ps` uses BSD flags. `ps aux -r` works; `ps aux --sort=-%mem` (GNU-style) does not.

4. **SystemUIServer restart**: After modifying plists that affect keyboard shortcuts or system settings, run `killall SystemUIServer` to apply changes without logout.

5. **Exhaust automation before asking user to do something manually**: The user prefers you to try alternative approaches (AppleScript GUI automation, plist editing, URL schemes) rather than giving up after a single failure and telling them to do it by hand. When `defaults write` fails on macOS 26+, try `plutil`, then `open "x-apple.systempreferences:..."`, then AppleScript UI scripting — only tell the user to do it manually if all three approaches fail.
