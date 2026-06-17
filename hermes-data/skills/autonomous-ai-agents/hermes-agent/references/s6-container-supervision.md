# Hermes s6-overlay Container Supervision

> Originally the standalone `hermes-s6-container-supervision` skill, consolidated into `hermes-agent`.

## Architecture

```
/init                                  ← PID 1 (s6-overlay v3.2.3.0)
├── cont-init.d                        ← oneshot setup, runs as root
│   ├── 01-hermes-setup                ← UID/GID remap, chown, seed, skills sync
│   └── 02-reconcile-profiles          ← restore profile gateway slots from persistent volume
├── s6-rc.d (static services)
│   ├── main-hermes/run                ← exec sleep infinity (no-op slot)
│   └── dashboard/run                  ← if HERMES_DASHBOARD=1
├── /run/service (s6-svscan watches; tmpfs)
│   └── gateway-<name>/                ← runtime-registered per-profile gateways
└── CMD ("main program")               ← /opt/hermes/docker/main-wrapper.sh
```

## Key files

| Path | Role |
|---|---|
| `Dockerfile` | s6-overlay install + cont-init.d wiring |
| `docker/stage2-hook.sh` | UID remap, chown, seed, skills sync |
| `docker/cont-init.d/02-reconcile-profiles` | Calls `hermes_cli.container_boot` on every boot |
| `docker/main-wrapper.sh` | Routes user args, drops to hermes via `s6-setuidgid` |
| `hermes_cli/service_manager.py` | `S6ServiceManager`: register/unregister/start/stop gateways |
| `hermes_cli/container_boot.py` | `reconcile_profile_gateways()` — walks persistent profiles |

## Why Architecture B (CMD as main program)

Two s6-overlay v3 mechanics blocked supervised main hermes:
1. cont-init.d scripts receive no CMD args — can't parse `docker run <image> chat -q "hi"`
2. `/run/s6/basedir/bin/halt` does NOT propagate exit codes (always 143/SIGTERM)

Solution: `ENTRYPOINT ["/init", "/opt/hermes/docker/main-wrapper.sh"]`. The CMD exits normally with the real exit code.

## Quick recipes

```sh
# Verify s6 is PID 1
docker exec <c> sh -c 'cat /proc/1/comm'

# Inspect a profile gateway
docker exec <c> /command/s6-svstat /run/service/gateway-<name>

# Bring service up/down
docker exec <c> /command/s6-svc -u /run/service/gateway-<name>   # up
docker exec <c> /command/s6-svc -d /run/service/gateway-<name>   # down

# Watch reconciler log
docker exec <c> tail -n 50 /opt/data/logs/container-boot.log
```

## Common pitfalls

- **"command not found" via docker exec:** `/command/` is only on PATH for supervised processes. Use absolute path `/command/s6-svstat`.
- **Profile directory ownership:** Stage2 chowns `$HERMES_HOME/profiles` to hermes on every boot. Don't remove that block.
- **Files written by `docker exec` are root-owned:** Pass `--user hermes` or rely on stage2 chown sweep next reboot.
- **Service slot exists but "s6-supervise not running":** The tmpfs was wiped on restart. Wait for cont-init reconciler.
- **Gateway starts then immediately exits:** Profile has no model/auth configured. Run `hermes -p <profile> setup` first.
- **Reconciler skipped a profile:** It keys on `SOUL.md` presence. Add a SOUL.md to opt back in.
- **Container exits 143:** Something invoked `s6-svscanctl -t`. Let CMD exit normally instead.
