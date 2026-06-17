# Hermes Web Access on LAN — Full Setup Recipe

Session date: 2026-06-06

## Problem

User on 192.168.1.106 cannot access http://192.168.1.113:8787/ (Hermes web interface on LAN).

## Diagnosis Steps

1. **ping** — confirmed network reachable, 0% packet loss
2. **curl to port 8787** — `000` response, port closed
3. **lsof -i :8787** — no process listening
4. **ifconfig** — confirmed this machine IS 192.168.1.113 (user was on a different LAN client)
5. **grep .env** — no API_SERVER or Dashboard vars configured

## Critical Discovery — API Server ≠ Dashboard

The session revealed a common confusion: the user wanted the **Dashboard** (HTML web UI with config, sessions, chat), but we first mistakenly set up the **API Server** (OpenAI-compatible REST API, no HTML at root).

| | API Server | Dashboard |
|---|---|---|
| What | REST API endpoints | Full HTML web UI |
| Root path | 404: Not Found | 200: `<!doctype html>` |
| Start mechanism | Gateway platform adapter (env vars) | `hermes dashboard` (separate process) |
| Default port | 8642 | 9119 |
| LAN binding | `API_SERVER_HOST=0.0.0.0` | `--host 0.0.0.0 --insecure` |
| Auth required | `API_SERVER_KEY` (on 0.0.0.0) | `--insecure` flag |

## Fix — Dashboard on port 8787

The user previously had the Dashboard on port 8787, so we needed to move the API Server off that port and start the Dashboard there:

**Step 1**: Move API Server to its default port (8642) to free up 8787:
```bash
sed -i '' 's/API_SERVER_PORT=8787/API_SERVER_PORT=8642/' ~/.hermes/profiles/main/.env
hermes gateway restart
```

**Step 2**: Start Dashboard on 8787 with LAN access:
```bash
hermes dashboard --stop                # kill stale instances
hermes dashboard --host 0.0.0.0 --port 8787 --insecure --no-open &
```

## API Server Setup (for reference)

If you actually want the API Server on LAN (for Open WebUI, LobeChat, etc.):

Add to `~/.hermes/profiles/main/.env`:
```
API_SERVER_ENABLED=true
API_SERVER_HOST=0.0.0.0
API_SERVER_PORT=8642
API_SERVER_KEY=<random 32-byte urlsafe token>
```

Generate key: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

Restart gateway: `hermes gateway restart`

Verify: `curl http://192.168.1.113:8642/health` → 200

**API_SERVER_KEY is mandatory** when binding to `0.0.0.0`. Without it:
```
ERROR gateway.platforms.api_server: [Api_Server] Refusing to start: API_SERVER_KEY
is required for the API server, including loopback-only binds on 0.0.0.0.
```

## Key Takeaways

- **Dashboard and API Server are completely different things** — Dashboard = HTML UI, API Server = REST API
- **Dashboard is a separate process from the gateway** — `hermes gateway restart` does NOT restart the dashboard
- **Both need explicit LAN configuration** — Dashboard needs `--host 0.0.0.0 --insecure`, API Server needs env vars with key
- **Port conflicts** — if both try to use the same port, one will fail silently
- Verify with: `lsof -i :<port>` and `curl http://<ip>:<port>/`
