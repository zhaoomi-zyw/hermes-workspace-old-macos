# Hermes WebUI (nesquena/hermes-webui) Server Troubleshooting

## Server unreachable from LAN — binding to localhost only

**Symptom**: WebUI works on `http://127.0.0.1:8787` but `http://192.168.1.113:8787` from another device returns connection refused or times out.

**Diagnosis**:

```bash
lsof -i :8787 -P
```

If output shows `TCP localhost:msgsrvr (LISTEN)` instead of `TCP *:8787 (LISTEN)`, the server is bound to localhost only.

**Fix — Option A (direct, stable)**: Start `server.py` directly with host binding:

```bash
kill $(lsof -ti :8787) 2>/dev/null
cd /Users/omi/hermes-webui
HERMES_WEBUI_HOST=0.0.0.0 /Users/omi/.hermes/hermes-agent/venv/bin/python server.py &
```

**Fix — Option B (ctl.sh, may be unstable)**: Restart with `--host 0.0.0.0` via ctl.sh:

```bash
cd /Users/omi/hermes-webui
./ctl.sh restart --host 0.0.0.0 8787
```

⚠️ **Warning**: Option B (ctl.sh → bootstrap.py --foreground → os.execv → server.py) may cause the server to silently exit within 1-2 minutes. See "Process dies silently — bootstrap.py --foreground crash" below. Option A (direct `python server.py`) has been stable for 20+ hours.

**Why**: The server was started without `--host 0.0.0.0` (or with no `--host` flag, which defaults to `127.0.0.1`). The `--host 0.0.0.0` flag tells the HTTP server to bind to all network interfaces.

## Process dies silently — bootstrap.py --foreground crash

**Symptom**: WebUI starts via ctl.sh, serves requests for ~30-90 seconds, then silently exits with no error in logs. The process disappears and port 8787 goes dead.

**Root cause**: `ctl.sh` runs `bootstrap.py --foreground`, which does `os.execv()` to replace itself with `server.py`. This execv path causes `server.py` to silently exit within 1-2 minutes — no crash, no error log, no OOM kill.

**Evidence**: Multiple restarts via `ctl.sh start --host 0.0.0.0 8787` consistently died within 38s and 86s. The previously stable process (PID 84335, running since Thu 9PM ~20 hours) was started directly as `python server.py` — NOT through ctl.sh or bootstrap.py.

**Fix**: Run `server.py` directly with the host env var set. This is the path that stays stable for days:

```bash
# Kill any existing process on port 8787
kill $(lsof -ti :8787) 2>/dev/null

# Start directly — stable long-term
cd /Users/omi/hermes-webui
HERMES_WEBUI_HOST=0.0.0.0 /Users/omi/.hermes/hermes-agent/venv/bin/python server.py &
```

For Hermes agent background management, use:
```bash
terminal(background=True, command="HERMES_WEBUI_HOST=0.0.0.0 /Users/omi/.hermes/hermes-agent/venv/bin/python server.py", workdir="/Users/omi/hermes-webui")
```

**Verification**: Server should stay up >5 minutes (vs bootstrap.py dying in <2 min).
Check with: `lsof -i :8787 -P | grep LISTEN` should show `TCP *:8787 (LISTEN)`.

**Pitfall — `export` in background terminal doesn't propagate**: When using `terminal(background=true)`, shell `export VAR=val` does NOT carry to the child process. Set the env var inline before the command (as shown above) or use the workdir variant.

**ctl.sh status shows "stopped" when running directly**: ctl.sh tracks processes via PID file. Direct-launched `server.py` won't have a ctl.sh PID file, so `./ctl.sh status` reports "stopped" even though the server is running. Use `lsof -i :8787` for ground truth.

## Quick health check

```bash
# Check process and binding
lsof -i :8787 -P | grep LISTEN
# Should show: TCP *:8787 (LISTEN)

# API health endpoint
curl -s http://127.0.0.1:8787/health
# Should return {"status": "ok", ...}

# ctl.sh status
cd /Users/omi/hermes-webui && ./ctl.sh status
```

## Key files

| Path | Purpose |
|------|---------|
| `/Users/omi/hermes-webui/ctl.sh` | Lifecycle manager (start/stop/restart/status/logs) — ⚠️ unstable: see bootstrap.py execv issue |
| `/Users/omi/hermes-webui/bootstrap.py` | Launcher with venv + env setup — ⚠️ `--foreground` mode (used by ctl.sh) causes silent exit via os.execv |
| `/Users/omi/hermes-webui/server.py` | Server entry point — direct launch (`python server.py`) is the stable path for LAN deployments |
| `/Users/omi/.hermes/profiles/main/webui.log` | Runtime log |
| `/Users/omi/.hermes/profiles/main/webui.pid` | PID file |
| `/Users/omi/.hermes/profiles/main/webui.ctl.env` | Launch state (host, port, python path) |
