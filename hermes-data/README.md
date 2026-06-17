# Hermes Data Backup

> Hermes Agent 配置、Skills 和 Memory 的备份快照。
> 上传于 2026-06-17。

## 目录结构

```
hermes-data/
├── README.md         # 本文件
├── skills/           # Hermes skills（422个，包含内置 + 自定义）
└── memories/
    ├── MEMORY.md     # 记忆（已脱敏）
    └── USER.md       # 用户画像（已脱敏）
```

## 说明

- `skills/` 是从 `~/.hermes/profiles/main/skills/` 完整的备份
- `memories/` 已脱敏处理（移除了密码、Token、IP 等敏感信息）
- 原始文件位于 `~/.hermes/profiles/main/memories/`

## 恢复方式

```bash
# Skills
cp -r skills/* ~/.hermes/profiles/main/skills/

# Memories
cp memories/MEMORY.md ~/.hermes/profiles/main/memories/MEMORY.md
cp memories/USER.md ~/.hermes/profiles/main/memories/USER.md
```
