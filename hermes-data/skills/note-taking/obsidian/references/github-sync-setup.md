# Obsidian GitHub Sync Setup

Step-by-step for syncing an Obsidian vault across multiple computers via GitHub.

## One-time: create the repo and push

```bash
cd /path/to/vault
git init
git config user.name "github-username"
git config user.email "email@example.com"
git remote add origin https://github-username:TOKEN@github.com/owner/repo.git

# .gitignore — omit large attachments and session files
cat > .gitignore << 'EOF'
.obsidian/workspace.json
.obsidian/workspace-mobile.json
.obsidian/hotkeys.json
.DS_Store
EOF

git add -A
git commit -m "Initialize vault"
git branch -m master main   # if needed
git push -u origin main
```

## Second computer: clone and open

```bash
git clone https://github.com/owner/repo.git
# Open Obsidian → "Open folder as vault" → select the cloned directory
```

## Install Git plugin (in-app sync)

1. Obsidian → Settings → Community plugins → turn off Safe Mode
2. Browse → search **"Git"** (NOT "Obsidian Git" — won't find it)
3. Install the one by **Vinzent** (highest download count: hundreds of thousands)
4. Enable the plugin

### Plugin settings

- **Username**: your GitHub username
- **Password/Token**: Personal Access Token (repo scope)
- **Auto pull on startup**: ON
- **Auto backup**: ON (interval: 30 minutes)
- **Commit message**: "auto" (default is fine)

## Daily use

| Action | Shortcut |
|--------|----------|
| Push changes now | `Cmd+P` → "Git: Commit and push" |
| Pull latest | `Cmd+P` → "Git: Pull" |
| Auto | Plugin handles pull on startup + periodic backup push |

## Adding new notes from the agent side

When the agent writes new notes to the vault:

```bash
cd /path/to/vault
git add -A
git commit -m "Describe what was added"
git push
```

The second computer will auto-pull on next Obsidian startup (if auto-pull is enabled).
