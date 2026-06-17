# Hermes memory export to Obsidian

Use this when a user asks to move/export Hermes memory into an Obsidian vault.

## Source files

For the active `main` profile, durable Hermes memory normally lives in:

- `/Users/omi/.hermes/profiles/main/memories/MEMORY.md`
- `/Users/omi/.hermes/profiles/main/memories/USER.md`

Do not rely only on the current conversation transcript. The persistent memory files are the source of truth for "from the beginning until now" style requests.

## Vault path rule

1. Resolve `OBSIDIAN_VAULT_PATH` if present.
2. If it points into a Hermes profile sandbox (for example `/Users/omi/.hermes/profiles/main/home/...`) or the path does not exist and the user requested a new vault, prefer a real user directory:
   - `/Users/omi/Documents/<vault name>`
3. Use concrete absolute paths for file tools; do not pass `$OBSIDIAN_VAULT_PATH` literally.

## Recommended vault structure

```text
<vault>/
├── 00-MOC/
│   └── <vault name>.md
├── 01-Hermes-Memory/
│   ├── Hermes Persistent Memory.md
│   ├── Omi User Profile.md
│   └── Sensitive Data Handling.md
├── 99-Attachments/
│   └── .gitkeep
├── .obsidian/
│   ├── app.json
│   └── core-plugins.json
└── .gitignore
```

The MOC should link to the memory notes with Obsidian wikilinks. Each note should have frontmatter with `title`, `created`, `source`, `tags`, and `aliases`.

## Redaction requirements

Before writing notes, redact obvious secrets. At minimum cover:

- GitHub PATs: `ghp_...` → `ghp_***REDACTED***`
- Bearer headers: `Authorization: Bearer ...` → `Authorization: Bearer ***REDACTED***`
- Router/service credential fragments like `root/<password>`, `admin/<password>`, or `192.168.1.1/<password>`

Keep useful context such as device names, internal IPs, paths, and tool names unless the user asks for stronger anonymization.

## Git initialization

After writing files, initialize a local git repo and commit:

```bash
git init
git add .
git commit -m "Initial Hermes memory export"
```

If a remote is requested later, create/push separately after confirming privacy expectations.

## Verification checklist

Before final response:

1. List markdown files under the vault and confirm expected notes exist.
2. Check `git status --short --branch` is clean after commit.
3. Scan note contents for obvious unredacted patterns such as `ghp_[A-Za-z0-9]+` and `Authorization: Bearer <token>`.
4. Report the vault path, exported entry counts if known, and commit hash.

## Session example

In one session, the user asked to create an Obsidian repository named `macos hermes` from all current Hermes memory. The successful target was:

- `/Users/omi/Documents/macos hermes`

The export produced:

- `00-MOC/macos hermes.md`
- `01-Hermes-Memory/Hermes Persistent Memory.md`
- `01-Hermes-Memory/Omi User Profile.md`
- `01-Hermes-Memory/Sensitive Data Handling.md`

The task also revealed that `OBSIDIAN_VAULT_PATH` may resolve to the Hermes profile sandbox and be unsuitable for a user-facing Obsidian vault.
