---
name: obsidian
description: Read, search, create, and edit notes in the Obsidian vault.
platforms: [linux, macos, windows]
---

# Obsidian Vault

Use this skill for filesystem-first Obsidian vault work: reading notes, listing notes, searching note files, creating notes, appending content, adding wikilinks, and managing vault sync across computers.

## Vault path

Use a known or resolved vault path before calling file tools.

The documented vault-path convention is the `OBSIDIAN_VAULT_PATH` environment variable, for example from `~/.hermes/.env`. If it is unset, use `~/Documents/Obsidian Vault`.

File tools do not expand shell variables. Do not pass paths containing `$OBSIDIAN_VAULT_PATH` to `read_file`, `write_file`, `patch`, or `search_files`; resolve the vault path first and pass a concrete absolute path. Vault paths may contain spaces, which is another reason to prefer file tools over shell commands.

If the vault path is unknown, `terminal` is acceptable for resolving `OBSIDIAN_VAULT_PATH` or checking whether the fallback path exists. Once the path is known, switch back to file tools.

### Omi: Hermes memory mirror vault

For Omi's Hermes-memory mirror workflow, the target vault is `/Users/omi/Documents/macos hermes`. This vault stores a readable mirror of Hermes durable memory and longer project/background notes. When saving a new Hermes durable memory for Omi, mirror it into this vault as well, redact secrets first, and commit the vault's git changes if it is a git repo. Details: `references/hermes-memory-mirroring.md`.

## Read a note

Use `read_file` with the resolved absolute path to the note. Prefer this over `cat` because it provides line numbers and pagination.

## List notes

Use `search_files` with `target: "files"` and the resolved vault path. Prefer this over `find` or `ls`.

- To list all markdown notes, use `pattern: "*.md"` under the vault path.
- To list a subfolder, search under that subfolder's absolute path.

## Search

Use `search_files` for both filename and content searches. Prefer this over `grep`, `find`, or `ls`.

- For filenames, use `search_files` with `target: "files"` and a filename `pattern`.
- For note contents, use `search_files` with `target: "content"`, the content regex as `pattern`, and `file_glob: "*.md"` when you want to restrict matches to markdown notes.

## Create a note

Use `write_file` with the resolved absolute path and the full markdown content. Prefer this over shell heredocs or `echo` because it avoids shell quoting issues and returns structured results.

## Append to a note

Prefer a native file-tool workflow when it is not awkward:

- Read the target note with `read_file` only for inspection and stable anchors.
- Do **not** rewrite a note from `read_file` output verbatim: the tool output includes `LINE_NUM|CONTENT` prefixes, and writing it back will corrupt the Markdown with line numbers.
- Use `patch` for an anchored append when there is stable context, such as adding a section after an existing heading or appending before a known trailing block.
- Use `write_file` when rewriting the whole note is clearer than constructing a fragile patch; if you need current raw content for a full rewrite, read the file via a script/helper that returns raw text, not the line-numbered `read_file` display.

For an anchored append with `patch`, replace the anchor with the anchor plus the new content.

For a simple append with no stable context, `terminal` is acceptable if it is the clearest safe option.

## Targeted edits

Use `patch` for focused note changes when the current content gives you stable context. Prefer this over shell text rewriting.

## Wikilinks

Obsidian links notes with `[[Note Name]]` syntax. When creating notes, use these to link related content.

## Vault structure (organization pattern)

Organize vaults with numbered folders and a Map of Content (MOC):

```
vault/
├── 00-MOC/          # Main index page(s) — central hub with [[links]] to everything
├── 01-TopicA/       # Split by category, numbered for fixed ordering
├── 02-TopicB/
├── ...
├── 99-Attachments/  # Images, PDFs, PPTX — not committed to git if large
└── .obsidian/       # Auto-generated config
```

- Use frontmatter `tags:` and `aliases:` in every note for discoverability
- The MOC note serves as the vault homepage; link everything back to it
- Commit `app.json` and `core-plugins.json`; omit `workspace.json` and `hotkeys.json`

## GitHub sync for multi-computer access

To enable Obsidian on multiple computers sharing the same vault:

1. Initialize git in the vault directory, push to a GitHub repo (private recommended)
2. `.gitignore` large attachments (PPTX, PDFs) and session-only Obsidian files
3. On the second computer: install Obsidian, `git clone` the repo, open as vault
4. Install the **Git** community plugin for in-app push/pull
5. Configure auto pull on startup + auto backup interval

Full setup steps: see `references/github-sync-setup.md`.

### Pitfall: plugin naming in the community store

The git sync plugin is registered as **"Git"** (author: Vinzent), NOT "Obsidian Git". Searching "Obsidian Git" returns irrelevant results. Tell the user: search only "Git", then pick the one with the most downloads (hundreds of thousands, usually the top result).

## Saving research results

When using Obsidian as a knowledge base for ongoing research:

- **Always ask the user** before writing new research findings or search results to the vault. Do not auto-save.
- After user confirms, write the note, then `git add` + `git commit` + `git push` so all computers stay in sync.

## Hermes memory mirror for Omi

Omi wants future Hermes durable memories mirrored into the Obsidian vault at `/Users/omi/Documents/macos hermes` when they are saved.

Use this workflow whenever you call the `memory` tool to add/replace durable memory for Omi:

1. Save/update Hermes memory first with the `memory` tool.
2. Mirror the same durable fact into the Obsidian vault:
   - user/profile/preference facts → `01-Hermes-Memory/Omi User Profile.md`
   - environment/project/tool/workflow facts → `01-Hermes-Memory/Hermes Persistent Memory.md`
   - policy/procedure notes → create or update a focused note under `01-Hermes-Memory/` and link it from `00-MOC/macos hermes.md` when useful.
3. Redact secrets before writing Obsidian notes: API keys, PATs, bearer tokens, passwords, and `account/password` fragments.
4. If the vault is a git repo, commit the mirror update locally with a concise message such as `Mirror Hermes memory update`.

Do not mirror temporary task progress, PR numbers, issue numbers, commit SHAs, or stale session outcomes — the same durability rules as Hermes memory apply.

## Exporting Hermes memory to an Obsidian vault

When the user asks to put Hermes memory into Obsidian, use the workflow in `references/hermes-memory-export.md`:

- Treat Hermes persistent memory files (`MEMORY.md` and `USER.md`) as the source of truth, not only the visible current chat context.
- If the configured `OBSIDIAN_VAULT_PATH` points into a Hermes profile sandbox or does not exist, create/target a real user directory such as `~/Documents/<vault name>`.
- Always redact obvious secrets before writing notes: PATs/API keys, bearer tokens, router/service passwords, and `username/password` credential fragments.
- Create a class-level vault structure with a MOC, memory notes, a sensitive-data handling note, `.obsidian` basics, `.gitignore`, and a local git commit.
- Verify the result: list markdown files, check git status, and scan for obvious unredacted token patterns before telling the user it is done.
