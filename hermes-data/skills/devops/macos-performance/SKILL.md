---
name: macos-performance
description: Diagnose and optimize macOS performance — CPU/memory/thermal audit, WindowServer tuning, identify resource hogs, reduce visual effects overhead, Colima/Docker cleanup.
---

# macOS Performance Diagnostics & Tuning

## When to Use

- User reports macOS feeling sluggish, laggy, or choppy
- Fan noise, heat, or thermal throttling concerns
- Want to identify and eliminate unnecessary resource consumption
- Pre-upgrade baseline check or post-installation health verification

## Performance Audit Workflow

Run these in order. Each section builds on the last.

### Phase 1: Hardware Baseline

```bash
system_profiler SPHardwareDataType SPSoftwareDataType SPStorageDataType 2>/dev/null
```

Capture: Model, CPU, RAM, macOS version, SSD free space, uptime.

Key red flags:
- **Uptime > 30 days** → kernel memory creep, suggest reboot
- **SSD < 20% free** → APFS performance degradation
- **Intel i9 in thin chassis (MacBookPro16,x)** → thermal throttling prone

### Phase 2: Process Resource Audit

```bash
# CPU hogs (macOS top, BSD syntax — no -c flag)
top -l 1 -n 20 -o cpu -stats pid,command,cpu,mem,power | head -25

# Memory hogs (BSD ps — use -r for RSS sort, not --sort)
ps aux -r | head -20

# Memory pressure (single definitive check)
memory_pressure
```

Red flags:
- Any single process > 50% CPU sustained
- WindowServer > 15% CPU (see Phase 4)
- Swapins/swapouts > 0 in second+ lines of memory_pressure
- System-wide memory free percentage < 30%

### Phase 3: Thermal & Throttling Check

```bash
pmset -g thermlog 2>/dev/null   # CPU thermal state
pmset -g therm 2>/dev/null       # Speed limit / available CPUs
```

Red flags:
- `CPU_Speed_Limit` < 100 → active throttling
- Thermal warning level recorded → check for dust, fan blockage
- `kernel_task` consuming > 50% CPU in `ps aux -r` → thermal throttling in effect (kernel_task runs dummy cycles to reduce heat)

### Phase 4: WindowServer Diagnosis

WindowServer is the macOS compositor (display server). High CPU here = the GPU/compositor is overloaded.

```bash
ps aux | grep WindowServer | grep -v grep
```

**Causes of high WindowServer CPU** (check in order):

| Cause | Check | Fix |
|-------|-------|-----|
| Transparency effects | `defaults read com.apple.universalaccess reduceTransparency` → 0 | Enable Reduce Transparency (see below) |
| Dynamic wallpaper | `ps aux \| grep -i wallpaper` shows active extension | Switch to static wallpaper |
| HiDPI resolution | `system_profiler SPDisplaysDataType \| grep Resolution` → ≥ 4K | Reduce scaled resolution |
| 30-bit color | `Framebuffer Depth: 30-Bit` | Not user-adjustable; offset with other fixes |
| Many windows | Lots of open apps | Close unnecessary windows |
| External display mirror/extend | Additional display in SPDisplaysDataType | Disconnect or reduce resolution |

### Phase 5: Launchd Services

```bash
# List user-level non-Apple services
launchctl list 2>/dev/null | awk '$1 !~ /^PID$|^-/ && $3 !~ /com\.apple\./ {print}'

# List LaunchAgents (user auto-start)
ls -la ~/Library/LaunchAgents/
```

### Phase 6: Docker / Colima Check

```bash
colima status 2>&1 | head -1
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}"
```

Colima runs a full Linux VM via macOS Virtualization.framework. Typical footprint: 5–8 GB RAM + 10–20% CPU. Stop when not actively using Docker:

```bash
colima stop
```

### Phase 7: Visual Effects Tuning

```bash
# Check all animation/transparency settings
defaults read com.apple.universalaccess reduceMotion
defaults read com.apple.universalaccess reduceTransparency
```

**Reduce Transparency** — biggest single win for WindowServer CPU. On macOS Sequoia (26+), `defaults write com.apple.universalaccess reduceTransparency` is **blocked by TCC**. Use AppleScript GUI automation instead:

```applescript
-- See references/macos-accessibility-gui-automation.md for patterns
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

To toggle, first open the correct Settings pane:
```bash
open "x-apple.systempreferences:com.apple.preference.universalaccess?Seeing_Display"
```

## Hermes Gateway Resource Management

Hermes gateways can consume significant CPU when idle. Check:

```bash
ps aux | grep 'hermes.*gateway' | grep -v grep
```

**To stop a profile's gateway properly** (launchd-managed, auto-restarts if killed):

```bash
hermes --profile <name> gateway stop
```

**Pitfall**: `HERMES_PROFILE=<name> hermes gateway stop` stops the MAIN profile, not the target. Always use `--profile` flag, not the env var.

**Pitfall**: `kill <PID>` doesn't work — launchd auto-restarts the process. Use `hermes gateway stop`.

**Verification** it's fully stopped:
```bash
ps aux | grep "hermes.*--profile <name>" | grep -v grep  # should be empty
launchctl list 2>/dev/null | grep "gateway-<name>"        # should be empty
```

## Display Color Troubleshooting

When external display colors feel uncomfortable, check in order:

1. **HDR mode** (System Settings → Displays → select external display → toggle "High Dynamic Range" OFF). HDR on for SDR content is the #1 cause of washed-out / harsh colors.

2. **Color Profile** (popup in Displays settings) — ensure it matches the display model, not "Color LCD" which is for the built-in display.

3. **True Tone** — disable for external displays; it only calibrates for the built-in panel.

4. **Night Shift** — check if scheduled and affecting daytime white point.

## System Cleanup: Project Removal

When removing a project that uses Docker:

```bash
# 1. Stop containers
docker stop <container1> <container2>

# 2. Remove containers
docker rm <container1> <container2>

# 3. Remove volumes (data)
docker volume rm <volume1> <volume2>

# 4. Stop Colima
colima stop

# 5. Delete project directory
rm -rf /path/to/project
```

## Key Tools Reference

| Tool | macOS-specific note |
|------|---------------------|
| `top -l 1 -n 20 -o cpu` | BSD top, no interactive mode with -l |
| `ps aux -r` | Sort by RSS (not `--sort`); use `-r` |
| `memory_pressure` | More reliable than `vm_stat` for pressure |
| `pmset -g thermlog` | Thermal state / throttling |
| `defaults read com.apple.universalaccess` | Reading works; writing blocked on Sequoia+ |
| `launchctl list` / `launchctl bootout` | Manage user services |
| `osascript` + System Events | GUI automation for TCC-protected settings |
| `open "x-apple.systempreferences:..."` | Direct pane navigation |

## Pitfalls

- **`ps aux --sort=-%mem`** does NOT work on macOS BSD `ps`. Use `ps aux -r`.
- **`defaults write com.apple.universalaccess`** fails on macOS 26+ with TCC error "Could not write domain". Use AppleScript GUI automation instead.
- **`HERMES_PROFILE` env var vs `--profile` flag**: The env var does NOT work for `gateway stop/start` — always use the CLI flag.
- **Colima stays running** after stopping containers. `colima stop` is a separate step.
