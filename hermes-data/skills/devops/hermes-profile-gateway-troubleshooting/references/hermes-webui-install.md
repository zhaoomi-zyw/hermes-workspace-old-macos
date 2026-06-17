# Hermes WebUI Installation (nesquena/hermes-webui)

Third-party community web UI for Hermes Agent with native file attachment support.

Repo: https://github.com/nesquena/hermes-webui

## Why Use This Over Built-in Dashboard

| Feature | Built-in Dashboard | hermes-webui |
|---------|-------------------|--------------|
| Chat | Requires `--tui` + PTY (tmux workaround) | Native SSE streaming |
| File attachments | None | ✅ Per-session, persist across reloads |
| LAN access | Needs source patch for WS guard | `HERMES_WEBUI_HOST=0.0.0.0` |
| Profiles | Yes | ✅ Full profile switching |
| Session browser | Yes | ✅ Three-panel layout |
| Workspace file browser | No | ✅ Right panel with inline preview |

## Installation

```bash
git clone https://github.com/nesquena/hermes-webui.git ~/hermes-webui
cd ~/hermes-webui
python3 bootstrap.py --no-browser
```

The bootstrap auto-detects the Hermes agent venv and installs minimal deps (pyyaml, cryptography).

Default bind: `127.0.0.1:8787`.

## LAN Access

Stop the default local-only instance and restart bound to all interfaces:

```bash
cd ~/hermes-webui
./ctl.sh stop
HERMES_WEBUI_HOST=0.0.0.0 ./ctl.sh start
```

Access from LAN: `http://<lan-ip>:8787`

## Lifecycle Management

```bash
cd ~/hermes-webui
./ctl.sh status              # PID, uptime, bound host/port, health
./ctl.sh stop                # Stop
./ctl.sh start               # Start (foreground)
./ctl.sh restart             # Restart
./ctl.sh logs --lines 100    # Tail logs
```

Log file: `~/.hermes/profiles/main/webui.log` (when running under main profile).

## File Attachments

Attachments are stored per-session:
- `~/.hermes/webui/attachments/<session_id>/`
- Persist across page reloads
- Configurable via `HERMES_WEBUI_ATTACHMENT_DIR`

## Health Check

```bash
curl -s http://127.0.0.1:8787/health
# → {"status":"ok","sessions":0,"active_streams":0}
```
