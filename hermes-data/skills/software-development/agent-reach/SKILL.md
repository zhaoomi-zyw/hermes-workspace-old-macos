---
name: agent-reach
description: "Give Hermes eyes to see the entire internet — read & search Twitter, Reddit, YouTube, GitHub, Bilibili, 小红书, LinkedIn, V2EX via one CLI, zero API fees."
platforms: [linux, macos, windows]
---

# Agent Reach

Give your AI agent eyes to see the entire internet. Read & search Twitter, Reddit, YouTube, GitHub, Bilibili, 小红书 — one CLI, zero API fees.

**GitHub**: https://github.com/Panniantong/Agent-Reach (⭐29.5k, MIT)

## What it is

Agent Reach is a **capability layer** — not just another tool. It installs, configures, and health-checks the best available open-source backends for each platform, so the agent can read any internet content without manual tool research.

Each platform = preferred + fallback backends in an ordered list. When one backend breaks (e.g. yt-dlp blocked by Bilibili → switched to bili-cli), the user doesn't need to know.

## Supported Platforms

| Platform | Out-of-box | Auth Needed | Auth Method |
|----------|-----------|-------------|-------------|
| 🌐 Web pages | ✅ Read any URL | — | — |
| 📺 YouTube | ✅ Subtitles + search | — | — |
| 📡 RSS | ✅ Read any RSS/Atom | — | — |
| 🔍 Web Search | ✅ Semantic search (Exa via MCP) | — | Auto-configured, free |
| 📦 GitHub | ✅ Public repos + search | Private repos/Issues | `gh auth login` |
| 🐦 Twitter/X | ✅ Read single tweet | Search, timeline | Cookie (tell agent "帮我配 Twitter") |
| 📺 Bilibili | ✅ Search + video details | Subtitles | OpenCLI / Cookie |
| 📖 Reddit | — | Search + read posts | OpenCLI / rdt-cli + Cookie |
| 📕 小红书 | — | Search, read, comment | OpenCLI / xiaohongshu-mcp |
| 💼 LinkedIn | ✅ Public pages | Profile/Company detail | Cookie / linkedin-mcp |
| 💻 V2EX | ✅ Hot posts, nodes, user info | — | — |
| 📈 雪球 | ✅ Stock quotes, search, hot posts | — | Cookie optional |

## Installation

One command to the agent:

```
帮我安装 Agent Reach：https://raw.githubusercontent.com/Panniantong/agent-reach/main/docs/install.md
```

Or manual:

```bash
pip install agent-reach
agent-reach install --env=auto
agent-reach doctor   # check what works
```

### What install does:
1. **Installs CLI** — `pip install agent-reach` (bundles yt-dlp, feedparser)
2. **System dependencies** — auto-detect & install Node.js, gh CLI, mcporter
3. **Search engine** — Exa via mcporter MCP (free, no API key)
4. **Environment detection** — local desktop vs server, gives corresponding advice
5. **Registers SKILL.md** — agent auto-knows which upstream tool to call per platform
6. **Interactive auth** — asks which auth-requiring platforms to configure

### Safety:

```bash
# Preview only, no changes
agent-reach install --env=auto --dry-run

# Safe mode — don't auto-install system packages
agent-reach install --env=auto --safe
```

## Key auth notes

- **Cookie-based platforms** (Twitter, 小红书, Reddit): use a **dedicated burner account** (risk of ban via script access)
- Cookie Editor Chrome extension recommended for export: https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm
- **Cookies stay local** at `~/.agent-reach/config.yaml` (chmod 600)
- **Reddit** requires a proxy from mainland China networks

## How to use in Hermes

After installation, use natural language:

- "帮我看看这个网页" → `curl https://r.jina.ai/URL`
- "这个 GitHub 仓库是做什么的" → `gh repo view owner/repo`
- "这个 YouTube 视频讲了什么" → `yt-dlp` extracts subtitles
- "B站搜一下 AI 教程" → `bili search` (no login needed)
- "全网搜一下 LLM 框架对比" → Exa semantic search
- "订阅这个 RSS" → `feedparser` parse

## Diagnosis

```bash
# Check every platform's status
agent-reach doctor

# Update backends
agent-reach update

# Uninstall
agent-reach uninstall
```

## Uninstall

```bash
agent-reach uninstall
# Clears ~/.agent-reach/ (cookies/tokens), skill files, MCP config

# Keep cookies/tokens for reinstall
agent-reach uninstall --keep-config
pip uninstall agent-reach
```
