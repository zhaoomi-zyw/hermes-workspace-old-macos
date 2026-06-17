# macOS launchd + git post-merge auto-restart pattern

Pattern for deploying long-running services on macOS that need to auto-start on boot, auto-restart on crash, and auto-restart after `git pull` updates.

Applied here to `nesquena/hermes-webui` (installed at `/Users/omi/hermes-webui/`, port 8787, LAN-accessible at `0.0.0.0`).

## 1. Launchd plist

File: `~/Library/LaunchAgents/com.parantoux.hermes-webui.plist`

Key settings:
- `RunAtLoad: true` — start on boot
- `KeepAlive: true` — restart if it crashes
- `WorkingDirectory` — set to repo root so relative paths resolve
- `EnvironmentVariables` — all env vars in the plist (survives across git pulls, unlike repo `.env`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.parantoux.hermes-webui</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>/Users/omi/hermes-webui/bootstrap.py</string>
    <string>--no-browser</string>
    <string>--foreground</string>
    <string>--host</string>
    <string>0.0.0.0</string>
    <string>8787</string>
  </array>
  <key>WorkingDirectory</key>
  <string>/Users/omi/hermes-webui</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>HERMES_WEBUI_HOST</key>
    <string>0.0.0.0</string>
    <key>HERMES_WEBUI_PORT</key>
    <string>8787</string>
    <key>HERMES_WEBUI_CSP_CONNECT_EXTRA</key>
    <string>http://192.168.1.113:* ws://192.168.1.113:*</string>
    <key>HOME</key>
    <string>/Users/omi</string>
  </dict>
  <key>RunAtLoad</key>
  <true/>
  <key>KeepAlive</key>
  <true/>
  <key>StandardOutPath</key>
  <string>/Users/omi/.hermes/profiles/main/webui.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/omi/.hermes/profiles/main/webui.error.log</string>
</dict>
</plist>
```

Load with:
```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.parantoux.hermes-webui.plist
```

Manage:
```bash
launchctl kickstart -k gui/$(id -u)/com.parantoux.hermes-webui  # restart
launchctl print gui/$(id -u)/com.parantoux.hermes-webui          # status
launchctl bootout gui/$(id -u)/com.parantoux.hermes-webui        # stop & unload
```

Pitfall: `launchctl kickstart` alone may not restart if the process crashed — always use `-k` (kill first).

## 2. Git post-merge hook for auto-restart

File: `.git/hooks/post-merge`

Runs after `git pull` (which is `git fetch` + `git merge`). Only restarts when files actually changed (skips no-op merges).

```bash
#!/usr/bin/env bash
LABEL="com.parantoux.hermes-webui"
SERVICE="gui/$(id -u)/${LABEL}"

if git diff-tree --name-only -r ORIG_HEAD HEAD 2>/dev/null | grep -q .; then
    echo "[hermes-webui] Files changed, restarting..."
    launchctl kickstart -k "${SERVICE}" 2>/dev/null && \
        echo "[hermes-webui] Restarted successfully" || \
        echo "[hermes-webui] Restart failed"
else
    echo "[hermes-webui] No file changes, skip restart"
fi
```

Make executable: `chmod +x .git/hooks/post-merge`

Pitfall: git hooks live in `.git/hooks/` which is NOT tracked by git — they persist across pulls but NOT across fresh clones. After a fresh clone, the hook must be re-created.

## 3. Hermes web interface distinction

Three different things, easy to confuse:

| Service | Port | Command | Purpose |
|---------|------|---------|---------|
| API Server | 8642 | `hermes gateway` platform | OpenAI-compatible API (no UI) |
| Built-in Dashboard | 9119 | `hermes dashboard` | Hermes management dashboard |
| hermes-webui (third-party) | 8787 | `bootstrap.py` via launchd | Full-featured chat web UI |

The API Server and hermes-webui both run under `hermes gateway`, but the Dashboard is a separate process. Port conflicts: the built-in Dashboard can't share 8787 with hermes-webui; stop it first with `hermes dashboard --stop`.
