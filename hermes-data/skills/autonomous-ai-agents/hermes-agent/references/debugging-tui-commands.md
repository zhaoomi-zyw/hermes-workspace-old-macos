# Debugging Hermes TUI Slash Commands

> Originally the standalone `debugging-hermes-tui-commands` skill, consolidated into `hermes-agent`.

## Architecture Overview

Hermes slash commands span three layers:
```
Python backend (hermes_cli/commands.py)     <- canonical COMMAND_REGISTRY
       │
       ▼
TUI gateway (tui_gateway/server.py)         <- slash.exec / command.dispatch
       │
       ▼
TUI frontend (ui-tui/src/app/slash/)        <- local handlers + fallthrough
```

The Python `COMMAND_REGISTRY` is the source of truth for: CLI dispatch, gateway help, Telegram BotCommand menu, Slack subcommand map, and autocomplete data shipped to Ink.

## When a command misbehaves

Common issues and their causes:

1. **Command shows in TUI but not in autocomplete.** The command is in the TUI codebase but missing from `COMMAND_REGISTRY` in `hermes_cli/commands.py`. Autocomplete data ships from Python.

2. **Command shows in autocomplete but doesn't work.** Check the handler in `tui_gateway/server.py` and the frontend handler in `ui-tui/src/app/createSlashHandler.ts`. Local TUI handlers take precedence over gateway dispatch.

3. **Command behavior differs between CLI and TUI.** The command might have different implementations. Check both `cli.py::process_command` and the TUI's local handler.

4. **Command persists config but doesn't apply live.** For TUI-local commands, updating `config.set` is not enough. Also patch the relevant nanostore state immediately (`patchUiState(...)`) and pass new state through rendering components.

5. **Gateway dispatch silently ignores the command.** Check `GATEWAY_KNOWN_COMMANDS` includes the canonical name. If `cli_only` with `gateway_config_gate`, verify the gated config is truthy.

## Fixing missing autocomplete

Add a `CommandDef` entry to `COMMAND_REGISTRY` in `hermes_cli/commands.py`:
```python
CommandDef("commandname", "Description of the command", "Session",
           cli_only=True, aliases=("alias",),
           args_hint="[arg1|arg2|arg3]",
           subcommands=("arg1", "arg2", "arg3")),
```

- `cli_only=True` — only in the interactive CLI/TUI
- `gateway_only=True` — only in messaging platforms
- neither — available everywhere

Then add handler in `HermesCLI.process_command()` in `cli.py`, and for gateway-available commands, add handler in `gateway/run.py`.

## Debugging Tactics

- **Python side hangs:** use `python-debugpy` skill to break inside `_SlashWorker.exec`
- **Ink side not reacting:** use `node-inspect-debugger` skill to break in `app.tsx`'s slash dispatch
- **Registry mismatch:** compare `COMMAND_REGISTRY` entry against TUI's local command list side-by-side

## Pitfalls

- After adding live UI state, search every consumer and thread new state through ALL render paths
- Rebuild TUI (`npm --prefix ui-tui run build`) before testing
- `cli_only=True` commands won't work in gateway/messaging platforms
