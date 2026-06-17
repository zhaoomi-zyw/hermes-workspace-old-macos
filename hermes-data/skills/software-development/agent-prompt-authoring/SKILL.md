---
name: agent-prompt-authoring
description: Writing LLM agent / Copilot agent instructions — pitfalls, formatting, output constraints. Use when creating or debugging agent system prompts.
category: software-development
---

# Agent Prompt Authoring

## When to Use
- Writing a new Copilot / LLM agent instruction (system prompt)
- Debugging agent output formatting issues (bold, large text, broken layout)
- User complains agent output looks wrong in the display layer

## Core Rule: Output Format ≠ Markdown

The most common pitfall: **Markdown syntax in your instruction's output template gets rendered by the display layer** (WebUI, Teams, etc.).

| What you write in the instruction | What the user sees | Fix |
|------|------|------|
| `---` separators | Horizontal rule / heading style | Use blank lines or `-` (single dash) |
| `**text**` | Bold | Remove the `**` |
| `# Title` / `## Title` | Enlarged heading | Use plain text label |
| `* bullet` / `- bullet` | Bullet list rendering | Use plain text with spaces |

## Instruction Writing Checklist

1. **Check for user-provided templates FIRST** — if the user says they already have an output template (Excel, Word, form, etc.), do NOT include output format in the agent description. Just write "输出格式由用户另行提供" or "output format is provided separately." Defer entirely to their template.
2. **Specify output format explicitly** — include "no Markdown, no bold, no headings, no separators"
3. **Use plain text templates** — emoji flags (🇨🇳 🇯🇵 🇬🇧) are fine, but avoid `---`, `**`, `#`
4. **State the anti-rule** — `不使用任何 Markdown 语法（不要加粗、不要标题、不要分隔线）`
5. **Test the output** — paste the agent's first response into the target display environment before iterating

## Agent Templates (References)

See `references/agent-templates-procurement-knowledge-base.md` for:
- Vendor proposal scoring agent (SOW/KPI evaluation)
- Memory knowledge base agent (file-based personal KB)
- Copilot vs Hermes memory comparison

## Translation Agent Template

When building multi-language translation agents, include this block:

```
## 输出格式
严格按以下格式输出，使用纯文本，不使用任何 Markdown 语法（不要加粗、不要标题、不要分隔线）：

🇬🇧 EN: [翻译]
🇯🇵 JP: [翻译]
```

## Reusable Templates

See `references/agent-templates.md` for ready-to-use agent descriptions:
- **Vendor Proposal Scoring Agent** — 供应商技术方案评审，SOW+KPI 逐项打分，证据驱动
- **Memory Knowledge Base Agent** — 个人记忆知识库，分类存储+检索

## Pitfalls

- **Copilot/ChatGPT will faithfully reproduce whatever format you give it** — if your template has `---`, the output will too, and it WILL render wrong
- **The fix is always in the instruction, not in post-processing** — tell the agent "don't use Markdown" rather than trying to strip it later
- **Omi prefers plain text, no bold, no enlarged text** — keep output visually flat
- **Don't define output format when the user already has a template** — if the user mentions an existing Excel/Word/form, strip the output format block from the agent description and defer to their template. Including a redundant format will frustrate the user.
- **Copilot agents cannot persist memory across sessions** — unlike Hermes, Copilot has no explicit memory tool and no auto-save mechanism. Its only indirect persistence is reading existing workspace files. When user wants cross-session memory, recommend a file-based workaround (agent reads/writes a `memory-bank/` directory). See `references/copilot-agent-capabilities.md`.
