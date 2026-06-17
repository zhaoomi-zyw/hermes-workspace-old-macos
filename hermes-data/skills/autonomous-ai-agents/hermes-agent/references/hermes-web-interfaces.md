# Hermes Web Interfaces

Hermes has three different web-accessible interfaces. They are NOT the same and restarting one does not restart the others.

## Comparison

| Service | Default Port | Launched by | Purpose | Has UI? |
|---------|-------------|-------------|---------|---------|
| API Server | 8642 | `hermes gateway` (platform) | OpenAI-compatible REST API | No |
| Built-in Dashboard | 9119 | `hermes dashboard` | Config/sessions management | Yes |
| hermes-webui (third-party) | 8787 | `bootstrap.py` (separate) | Full chat web UI | Yes |

## API Server (gateway platform)

- Runs as a platform adapter inside `hermes gateway`
- Default: `127.0.0.1:8642` (configurable via `API_SERVER_HOST/PORT` env vars)
- Endpoints: `/v1/chat/completions`, `/v1/models`, `/health`, `/api/sessions`
- No built-in HTML UI — returns `404: Not Found` at `/`
- Requires `API_SERVER_KEY` when binding to non-loopback (`0.0.0.0`)
- Restarted via: `hermes gateway restart`

## Built-in Dashboard

- Separate process, NOT part of gateway
- Default: `127.0.0.1:9119`
- Launched via: `hermes dashboard --host 0.0.0.0 --port <port> --insecure --no-open`
- Requires `--insecure` flag for non-localhost binds
- Stop with: `hermes dashboard --stop`
- Status: `hermes dashboard --status`
- Pitfall: if running on port 8787, conflicts with third-party hermes-webui

## Third-party hermes-webui (nesquena/hermes-webui)

- Installed at: `/Users/omi/hermes-webui/`
- Managed via launchd: `com.parantoux.hermes-webui`
- Default port: 8787 (configurable via `HERMES_WEBUI_PORT`)
- LAN access requires: `HERMES_WEBUI_HOST=0.0.0.0` + CSP headers for the LAN IP
- Restart: `launchctl kickstart -k gui/$(id -u)/com.parantoux.hermes-webui`
- Git pull auto-restarts via post-merge hook

## Common confusion

When the user says "hermes web is down" or "can't access hermes from LAN", first determine WHICH service they mean:

1. Ask or check which port they're trying (8787 → webui, 9119 → dashboard, 8642 → API server)
2. Check if the right process is running: `lsof -i :<port>`
3. `hermes gateway restart` only affects the gateway + API server, NOT the built-in dashboard or third-party webui
