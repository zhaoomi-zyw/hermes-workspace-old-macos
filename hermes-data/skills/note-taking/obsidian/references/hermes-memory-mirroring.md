# Hermes memory mirroring to Obsidian

Session-derived workflow for Omi's `macos hermes` Obsidian vault.

## Purpose

Omi wants Hermes durable memories to be split across three knowledge layers:

- **Hermes memory** — short, critical, behavior-affecting long-term preferences only.
- **Obsidian `macos hermes`** — complete background, long history, project knowledge, and a readable mirror of Hermes memory.
- **Skills** — reusable procedures/workflows such as WebUI deployment, NAC analysis, and fund-report workflows.

## Target vault

Use the real user vault path:

`/Users/omi/Documents/macos hermes`

Do not blindly trust `OBSIDIAN_VAULT_PATH` when running from launchd/WebUI/profile-sandbox contexts: it may point under `/Users/omi/.hermes/profiles/main/home/...` and not exist. If the target is specifically the Hermes memory mirror, use the concrete path above unless the user gives a different path.

## Mirroring procedure

When a future session saves or updates Hermes durable memory for Omi:

1. Save/update the Hermes memory with the `memory` tool first.
2. Mirror the same durable fact into the Obsidian vault:
   - User preferences/profile facts → `01-Hermes-Memory/Omi User Profile.md`
   - Environment/project/tool/process facts → `01-Hermes-Memory/Hermes Persistent Memory.md`
   - Policy/process notes for mirroring → `01-Hermes-Memory/Memory Sync Policy.md`
3. Redact secrets before writing Obsidian notes:
   - API keys, GitHub PATs, bearer tokens, passwords, router/admin credentials.
   - Keep useful non-secret context such as paths, IP ranges, filenames, tool names, and high-level account/provider names.
4. Update the MOC if a new note is created:
   - `00-MOC/macos hermes.md`
5. If the vault is a git repo, commit the note changes locally with a concise message.

## Memory limit note

Hermes built-in memory character limits are configurable in the active profile config:

```yaml
memory:
  memory_char_limit: 10000
  user_char_limit: 6000
```

Use `hermes config set memory.user_char_limit 6000` and `hermes config set memory.memory_char_limit 10000` to adjust. New limits apply to new sessions because the memory snapshot is frozen at session start.
