---
name: cua-computer-use
description: "Background computer-use agent — drive native macOS/Windows/Linux desktop apps without stealing focus. MCP integration for Claude Code, Cursor, Codex, and Hermes."
platforms: [linux, macos, windows]
---

# Cua — Computer Use Agent Infrastructure

Build, benchmark, and deploy agents that use computers. Open-source infrastructure for computer-use agents: sandboxes, SDKs, benchmarks, and drivers.

**GitHub**: https://github.com/trycua/cua (⭐18k, MIT)
**Docs**: https://cua.ai/docs
**Discord**: https://discord.gg/mVnXXpdE85

## Three main components

This skill focuses on **Cua Driver** (background desktop automation) and **Cua Sandbox** (agent-ready VM/container environments).

### 1. Cua Driver — Background Computer Use

Drives native desktop apps **in the background** — agents click, type, verify without stealing cursor or focus.

**Install (macOS / Linux):**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/cua-driver/scripts/install.sh)"
```

**Install (Windows PowerShell):**
```powershell
irm https://raw.githubusercontent.com/trycua/cua/main/libs/cua-driver/scripts/install.ps1 | iex
```

**Wire into MCP-compatible agents:**
```bash
# Standard MCP
claude mcp add --transport stdio cua-driver -- cua-driver mcp

# Claude Code computer-use compatibility mode (screenshot grounding)
claude mcp add --transport stdio cua-computer-use -- cua-driver mcp --claude-code-computer-use-compat
```

**What Cua Driver provides:**
- Background screenshot capture (no focus steal)
- Mouse click, drag, scroll
- Keyboard typing, hotkeys
- Window listing and focus
- Works on macOS, Windows, Linux (pre-release)

**Compatible with:** Claude Code, Cursor, Codex, OpenClaw, and custom MCP clients.

### 2. Cua Sandbox — Agent-Ready Environments

One API for any VM or container image — cloud or local.

```bash
pip install cua
```

```python
# Requires Python 3.11+
from cua import Sandbox, Image

# Same API regardless of OS/runtime
async with Sandbox.ephemeral(Image.linux()) as sb:
    result = await sb.shell.run("echo hello")
    screenshot = await sb.screenshot()
    await sb.mouse.click(100, 200)
    await sb.keyboard.type("Hello from Cua!")
```

| | Linux container | Linux VM | macOS | Windows | Android | BYOI |
|---|---|---|---|---|---|---|
| **Cloud (cua.ai)** | ✅ | ✅ | ✅ | ✅ | ✅ | 🔜 |
| **Local (QEMU)** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 3. Lume — macOS Virtualization (Apple Silicon)

Create and manage macOS/Linux VMs with near-native performance using Apple's Virtualization.Framework.

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/trycua/cua/main/libs/lume/scripts/install.sh)"
lume run macos-sequoia-vanilla:latest
```

## API Keys

**No API keys needed for local use** (cua-driver, lume, cua sandbox with local QEMU).

Cua.ai cloud sandboxes require a cua.ai account (paid). Local use is free and open-source.

## Use cases for Hermes workshops

- **Background desktop automation demo**: Cua Driver can be shown as the backend that enables "Computer Use Agent" without stealing mouse focus — perfect for live workshop demos where the presenter keeps control.
- **Sandboxed environment**: Run code in isolated VMs/containers for safe agent testing.
- **Cross-platform**: Same API for macOS, Windows, Linux environments.

## Architecture notes

- Cua Driver communicates over MCP stdio transport
- Screenshots with `pid` and `window_id` capture only that window
- `cua-computer-use` MCP compatibility mode renames the `screenshot` tool to match what Claude Code expects for vision grounding
- CLI screenshots work as direct CuaDriver calls
