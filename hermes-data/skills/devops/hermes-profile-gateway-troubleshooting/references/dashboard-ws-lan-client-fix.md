# Dashboard WebSocket LAN Client Fix

## Symptom

Dashboard started with `--host 0.0.0.0 --tui --insecure`, HTTP pages load fine from LAN
machines, but the Chat tab shows "events feed disconnected — tool calls may not appear".

## Root Cause

`_ws_client_is_allowed()` in `hermes_cli/web_server.py` hardcodes loopback-only:

```python
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})

def _ws_client_is_allowed(ws: "WebSocket") -> bool:
    client_host = ws.client.host if ws.client else ""
    if not client_host:
        return True
    return client_host in _LOOPBACK_HOSTS
```

The `--insecure` flag relaxes HTTP Host-header checks but does NOT flow through to
WebSocket client-IP checks. All four WebSocket endpoints are affected:

- `/api/ws` — JSON-RPC for Chat tab
- `/api/events` — events feed sidebar
- `/api/pub` — PTY→dashboard event publishing
- `/api/pty` — xterm.js terminal bridge

When a non-loopback client connects, the server calls `ws.close(code=4403)` **before**
`ws.accept()`. Because the WebSocket handshake never completes, the browser sees abnormal
closure (code 1006), not the intended 4403. The frontend JS only distinguishes 1000, 4401,
and 4403 — everything else shows the generic "events feed disconnected" message.

## Fix

Two-line patch in `hermes_cli/web_server.py`:

**1. Store `allow_public` flag in app.state** (in `start_server()`, near `app.state.bound_port`):

```python
app.state.bound_host = host
app.state.bound_port = port
app.state.allow_public = allow_public   # ← add this line
```

**2. Honour it in `_ws_client_is_allowed()`**:

```python
def _ws_client_is_allowed(ws: "WebSocket") -> bool:
    """Check if the WebSocket client IP is acceptable.

    Allows loopback clients unconditionally.  Non-loopback clients are
    accepted when the dashboard was started with ``--insecure`` (i.e.
    ``allow_public`` is True on app.state).
    """
    client_host = ws.client.host if ws.client else ""
    if not client_host:
        return True
    if client_host in _LOOPBACK_HOSTS:
        return True
    return getattr(app.state, "allow_public", False)
```

## Revert

If the dashboard is removed, revert both patches to restore original loopback-only
behaviour.

## Verification

After patching and restarting the dashboard, access `/chat` from a LAN machine.
The events feed sidebar should show live gateway status instead of the disconnected
banner. Quick test from the server itself:

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:9119/chat
# 200

# In browser on LAN machine → http://192.168.x.x:9119/chat
# Sidebar should show live model/tools info, not "events feed disconnected"
```
