# Copilot Agent Capabilities & Limitations

## Memory: No Persistent Memory

Copilot agents do NOT have Hermes-style persistent memory. Key differences:

| Feature | Hermes Agent | Copilot Agent |
|---------|-------------|---------------|
| Explicit memory tool | Yes (`memory` tool, user-managed) | No |
| Auto-save after session | Yes (facts auto-persisted) | No |
| Cross-session recall | Full (memory injected into system prompt) | None (session-isolated) |
| Indirect persistence | `~/.hermes/profiles/*/memories/` | Workspace files only |

### Workaround: File-Based Memory Bank

To simulate persistent memory in Copilot, instruct the agent to read/write a `memory-bank/` directory:

```
核心规则：
1. 所有记忆存储在工作区的 memory-bank/ 目录下。
2. 接收记忆时分类存储为 .md 文件。
3. 查询记忆时搜索 memory-bank/ 下所有文件。
4. 记忆中没有的内容，回复"记忆库中暂无相关信息"。
```

This relies on Copilot's ability to read/write files in the workspace. If file write is disabled, this won't work.

## File I/O

Copilot agents can read and write files, but:
- Write capability depends on workspace permissions and Copilot configuration
- Some enterprise Copilot deployments restrict file writes

## Context

- Copilot agents have access to open workspace files as context
- `.github/copilot-instructions.md` serves as static system prompt supplement (does not auto-update)
- No equivalent to Hermes's dynamic skills system
