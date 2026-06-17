---
name: ai-engineering-from-scratch
description: "503-lesson AI engineering curriculum — from math foundations to autonomous agents. Perfect reference for workshop/courseware design. Every lesson ships reusable artifacts: prompts, skills, agents, MCP servers."
platforms: [linux, macos, windows]
---

# AI Engineering from Scratch

Comprehensive open-source AI engineering curriculum: 503 lessons, 20 phases, ~320 hours. Covers Python, TypeScript, Rust, Julia.

**GitHub**: https://github.com/rohitg00/ai-engineering-from-scratch (⭐32.8k, MIT)
**Web**: https://aiengineeringfromscratch.com

## Why this matters for Hermes workshop design

This curriculum is the **best available reference** for designing AI Agent workshops. Its structure and philosophy map directly to what a good workshop should deliver:

> **Every lesson ships a reusable artifact**: a prompt, a skill, an agent, an MCP server.
> Build it → Use it → **Ship It**.

That "Ship It" output format (prompts, skills, agents, MCP servers) matches Hermes skill-based architecture exactly.

## Curriculum structure (20 phases)

```
Phase  0 — Setup & Tooling (12 lessons)
Phase  1 — Math Foundations (22 lessons)
Phase  2 — ML Fundamentals (18 lessons)
Phase  3 — Deep Learning Core (13 lessons)
Phase  4 — Computer Vision (28 lessons)
Phase  5 — NLP Foundations to Advanced (29 lessons)
Phase  6 — Speech & Audio (18 lessons)
Phase  7 — Transformers (16 lessons)
Phase  8 — Generative AI (21 lessons)
Phase  9 — Reinforcement Learning (20 lessons)
Phase 10 — LLMs from Scratch (29 lessons)
Phase 11 — LLM Engineering (28 lessons)
Phase 12 — Multimodal (14 lessons)
Phase 13 — Tools & Protocols/ MCP (23 lessons) ← **MCP from scratch!**
Phase 14 — Agent Engineering (26 lessons) ← **Agent loop from scratch!**
Phase 15 — Autonomous Systems (31 lessons)
Phase 16 — Multi-Agent & Swarms (19 lessons)
Phase 17 — Infrastructure & Production (32 lessons)
Phase 18 — Ethics & Alignment (24 lessons)
Phase 19 — Capstone Projects (18 lessons)
```

### Key phases for agent workshop design

| Phase | Relevance to workshop |
|-------|----------------------|
| **13 — Tools & Protocols** | Build MCP servers from scratch — can be modular workshop artifact |
| **14 — Agent Engineering** | Agent loop in ~120 lines of Python — perfect live demo |
| **15 — Autonomous Systems** | Memory, reflection, tool use patterns |
| **16 — Multi-Agent & Swarms** | Orchestrator-worker pattern for advanced sessions |
| **17 — Infrastructure & Production** | Deployment, monitoring, evaluation |

## ## Installation into Hermes

### Step 1 — Clone

```bash
cd ~/workspace
git clone https://github.com/rohitg00/ai-engineering-from-scratch.git
```

### Step 2 — Install output artifacts (prompts, skills, agents)

```bash
cd ~/workspace/ai-engineering-from-scratch
python3 scripts/install_skills.py ~/.hermes/profiles/main/skills/ --type skill --layout skills --force
```

This installs ~388+ skill artifacts from `phases/*/outputs/` into your Hermes skills directory. You can then load any of them with `skill_view(name)`.

### Step 3 — Built-in curriculum skills (⚠️ NOT auto-installed)

The repo has two useful agent skills at `.claude/skills/` that **are NOT picked up by install_skills.py** (it only scans `phases/*/outputs/`). You must manually copy them:

```bash
# Copy find-your-level (placement quiz)
cp -r ~/workspace/ai-engineering-from-scratch/.claude/skills/find-your-level ~/.hermes/profiles/main/skills/

# Copy check-understanding (per-phase quiz)
cp -r ~/workspace/ai-engineering-from-scratch/.claude/skills/check-understanding ~/.hermes/profiles/main/skills/
```

| Skill | What it does | Location |
|-------|-------------|----------|
| `find-your-level` | 10-question placement quiz → starting phase + personalized path | `.claude/skills/find-your-level/` |
| `check-understanding` | Per-phase quiz with specific lesson review suggestions | `.claude/skills/check-understanding/` |

## How to learn — practical paths

### Path A: Self-directed from the browser (no install needed)

https://aiengineeringfromscratch.com

Just open and read. Every lesson's narrative (`docs/en.md`) is available on the web. Start at any phase.

### Path B: Use Hermes to guide you

Load the `find-your-level` skill and have me administer the 10-question placement quiz to find your starting phase. Then study phase-by-phase:

```bash
# Read lesson docs from the cloned repo
less phases/14-agent-engineering/01-the-agent-loop/docs/en.md

# Read the code implementations
less phases/14-agent-engineering/01-the-agent-loop/code/agent_loop.py

# Read the shipped artifacts (prompts/skills the lesson produces)
less phases/14-agent-engineering/01-the-agent-loop/outputs/skill-agent-loop.md
```

Then use `check-understanding` to verify mastery before moving to the next phase.

### Path C: Workshop design reference (shortcut)

Skip straight to these phases for agent workshop material:

| Phase | Focus | Key artifacts |
|-------|-------|---------------|
| **13** — Tools & Protocols | MCP servers from scratch | `skill-mcp-server-designer.md` |
| **14** — Agent Engineering | Agent loop, ReWOO, Reflexion, memory | `skill-agent-loop.md`, tool-use skills |
| **15** — Autonomous Systems | Memory, reflection, skill libraries | Voyager-style skill learning |
| **16** — Multi-Agent | Orchestrator-worker, swarms | CrewAI, Autogen patterns |

## Lesson structure (reusable pattern for workshop design)

Each lesson has 6 beats — a great template for structuring workshop modules:

```
MOTTO → PROBLEM → CONCEPT → BUILD IT → USE IT → SHIP IT
```

The **Build It / Use It** split is the pedagogical spine:
1. **Build It**: Implement from scratch (raw math, no frameworks)
2. **Use It**: Same concept via production library (PyTorch, sklearn)
3. **Ship It**: Reusable artifact — prompt, skill, agent, or MCP server

Each lesson folder:
```
phases/<NN>-<phase-name>/<NN>-<lesson-name>/
├── code/      runnable implementations
├── docs/
│   └── en.md  lesson narrative
└── outputs/   prompts, skills, agents, or MCP servers
```

## No API keys needed

This is a reference curriculum — all code runs locally. No API keys required.

## How to use as workshop reference

1. Clone the repo: `git clone https://github.com/rohitg00/ai-engineering-from-scratch.git`
2. Browse phases online: https://aiengineeringfromscratch.com
3. Extract artifact patterns from `outputs/` directories for your workshop materials
4. Use the `/find-your-level` placement quiz concept as template for workshop pre-assessment
5. Use the `BUILD IT → USE IT → SHIP IT` pattern as workshop module structure

## Author

Created by Rohit (also author of [Agent Memory](https://github.com/rohitg00/agentmemory), ⭐8.5k persistent memory for agents). The curriculum naturally integrates with Agent Memory for persistent memory capabilities.
