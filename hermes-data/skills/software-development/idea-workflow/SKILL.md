---
name: idea-workflow
version: 0.1.0
tags: [idea-workflow, product-design, specification, implementation, planning]
requirements: []
description: >
  Structured workflow for turning rough ideas into build-ready specification documents.
  Use when the user wants to develop a new product, app, tool, or feature — from
  initial concept through design doc, implementation spec, and final build handoff.
  Loads the four sub-skills: idea-superpowers-suite, idea-to-design-doc,
  idea-to-ui-design-brief, idea-to-implementation-doc.
  Triggers on: "I have an idea", "plan this project", "turn idea into spec",
  "design doc", "implementation spec", "build handoff", or any product
  development workflow request.
---

# idea-workflow

Structured idea-to-spec workflow using four sub-skills. Installed at:
`~/.hermes/skills/idea-workflow/` (umbrella + sub-skills) or individual
top-level skills: `idea-superpowers-suite`, `idea-to-design-doc`,
`idea-to-ui-design-brief`, `idea-to-implementation-doc`.

## Workflow Stages

```
rough idea
  -> idea-superpowers-suite (capture + research + handoff structure)
  -> idea-to-design-doc (product/UX design document)
  -> idea-to-ui-design-brief (optional UI design brief, image-gen prompts)
  -> idea-to-implementation-doc (implementation spec + build handoff)
  -> spec review
  -> coding (via Superpowers for GPT or similar)
```

## Modes

| Mode | Use case | Output |
|------|----------|--------|
| **Lite** | Quick idea capture, sketches, early thoughts | `ideas/<slug>.md` |
| **Full** | Serious product/app/tool development | 6-stage document package |

## Usage

**Full Mode:**
```
Load: idea-superpowers-suite, idea-to-design-doc, idea-to-implementation-doc
Prompt: "I have an idea for [X]. Use idea-workflow in Full mode and help me
turn it into a build-ready handoff."
```

**Lite Mode:**
```
Prompt: "Use idea-workflow in Lite mode and just capture this idea."
```

## Key Override Phrase

```
GREENLIGHT NEXT STAGE
```
Say this to skip further questions and advance to the next artifact. Unresolved
issues go into **Open Questions** or **Assumptions** in the next document.

## Sub-Skills

| Skill | Purpose |
|-------|---------|
| `idea-superpowers-suite` | Idea capture, research, interview引导，handoff结构 |
| `idea-to-design-doc` | Product/UX design document |
| `idea-to-ui-design-brief` | Optional UI stage + image-generation prompts |
| `idea-to-implementation-doc` | Implementation spec + agent build handoff |

## Install Location

Installed at: `~/.hermes/skills/idea-workflow/`

**Critical:** Sub-skills must be copied to top-level for Hermes discovery:
```bash
cp -r ~/.hermes/skills/idea-workflow/idea-superpowers-suite \
       ~/.hermes/skills/idea-workflow/idea-to-design-doc \
       ~/.hermes/skills/idea-workflow/idea-to-implementation-doc \
       ~/.hermes/skills/idea-to-ui-design-brief \
       ~/.hermes/skills/
```
After copying, restart Hermes session or run `hermes skills list` to verify.