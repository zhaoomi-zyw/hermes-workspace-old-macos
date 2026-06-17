---
name: openwrt-service-deployment
description: Deploy and troubleshoot third-party services on OpenWrt/iStoreOS routers, including binary services, procd init scripts, data directories, LAN verification, and web-app storage integrations.
tags:
  - openwrt
  - istoreos
  - procd
  - router
  - alist
---

# OpenWrt / iStoreOS Service Deployment

Use this skill when the user asks to install, configure, or troubleshoot a service on an OpenWrt/iStoreOS router, NAS-like home gateway, or LuCI-managed device (for example: Alist, OpenClash add-ons, file services, reverse proxies, or LAN-only daemons).

## Workflow

1. **Discover the target before installing**
   - SSH to the router and collect: `uname -a`, `/etc/os-release` or `/etc/openwrt_release`, `df -h`, `opkg print-architecture`, and current process/port state.
   - Check whether the service is already installed before downloading anything: `command -v <binary>`, `/etc/init.d/<service>`, and `netstat -tlnp`.
   - On iStoreOS, persistent writable space is usually `/overlay`; confirm available space before placing binaries or databases.

2. **Prefer native binaries or existing packages over Docker on routers**
   - Many OpenWrt/iStoreOS devices have limited storage and may not have Docker available or running.
   - Match binary architecture to `opkg print-architecture` / `uname -m` (for example `aarch64_generic` / `linux arm64`).

3. **Normalize the service data directory**
   - Do not assume the configured data directory is actually used. Verify the running process with:
     - `pidof <service>`
     - `readlink /proc/$PID/cwd`
     - `tr '\0' ' ' < /proc/$PID/cmdline`
   - If the service supports a `--data` or equivalent flag, put it in the init script so restarts and boot use the same database/config every time.
   - If multiple data directories already exist, identify the active one before resetting passwords or editing databases.

4. **Use procd-style init scripts for long-running services**
   - Prefer `USE_PROCD=1`, `start_service()`, `procd_set_param command ...`, and `procd_set_param respawn` over shell-backgrounding with `&`.
   - Enable autostart only after the command and data directory are verified: `/etc/init.d/<service> enable`.
   - Restart and verify the port is listening after edits.

5. **Configure via local API when available**
   - For web apps such as Alist, reset or set admin credentials using the service CLI against the correct data directory, then call the local API from the operator machine.
   - Verify authentication, list current storage/plugins/settings, apply the requested config, then verify user-visible behavior (for example list mounted files).

6. **Handle browser cookies safely**
   - If a cloud-drive driver needs a cookie/token, first try to obtain it from the user’s active browser session or browser DevTools.
   - Do not print full cookies in final responses. Treat them as login credentials and only use them for the target local service.
   - For Quark/Alist specifically, `copy(document.cookie)` may be incomplete because HttpOnly login cookies are omitted; if Alist initializes as `require login [guest]`, guide the user to Chrome DevTools → Network → refresh page → click a `pan.quark.cn` request → Headers/标头 → Request Headers/请求标头 → copy the full `Cookie:` header.
   - On macOS, AppleScript can locate a logged-in Chrome tab and read non-HttpOnly cookies, but it is not sufficient when the driver needs the full request Cookie header.

## Alist on iStoreOS / OpenWrt

See `references/alist-quark-on-istoreos.md` for the concrete Alist + Quark workflow discovered on iStoreOS.

Key reminders:
- Alist’s CLI default data folder is relative (`data`), so `alist admin set ... --data /etc/alist` only affects the running service if the service also starts with `alist server --data /etc/alist`.
- Validate the actual process command line before concluding a password reset failed.
- Quark driver fields in Alist v3 include `cookie` and `root_folder_id` (usually `0` for root). Mount path must be unique, e.g. `/quark`.
- Alist WebDAV is exposed under `/dav`; if a client such as VidHub reports an added source as unavailable, test `PROPFIND http://host:5244/dav` and `PROPFIND http://host:5244/dav/<mount>` with Basic auth. A 403 can mean the Alist user has `permission=0`; update the user permission via `/api/admin/user/update` before blaming the client path.

## Pitfalls

- `expect` treats square brackets and `$()` as Tcl syntax. When driving SSH with `expect`, avoid shell constructs that Tcl will pre-expand, or wrap the remote command carefully with braces/single quotes.
- BusyBox/OpenWrt commands may differ from macOS/Linux desktop behavior; keep commands simple and verify each operation.
- Do not persist a session-specific cookie/password in skill text or final summaries. Store only the procedure.

## Verification checklist

- Service binary exists and version is known.
- `/etc/init.d/<service> enabled` succeeds or service is otherwise documented as intentionally manual.
- Running process command line contains the intended config/data flags.
- Port is listening on the intended interface.
- Admin/API login succeeds.
- Requested integration is visible and works from the user-facing UI/API.
