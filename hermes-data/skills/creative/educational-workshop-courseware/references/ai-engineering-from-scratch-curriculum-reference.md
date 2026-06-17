# AI Engineering from Scratch — Curriculum Reference for Workshop Design

**Repo**: https://github.com/rohitg00/ai-engineering-from-scratch (⭐32.8k, MIT)
**Web**: https://aiengineeringfromscratch.com
**Local clone**: clone to workspace for offline access

## Why this matters for workshop design

503 lessons, 20 phases, ~320 hours. Every lesson ships a reusable artifact: a prompt, a skill, an agent, an MCP server. The "Build It → Use It → Ship It" pedagogical pattern maps directly to hands-on workshop module design.

## Key phases for agent workshop design

| Phase | Focus | Workshop use |
|-------|-------|-------------|
| **13** — Tools & Protocols | MCP servers from scratch | Students build a tool their agent can call |
| **14** — Agent Engineering | Agent loop, ReWOO, Reflexion | ~120-line ReAct loop = perfect live demo |
| **15** — Autonomous Systems | Memory, reflection, skill libraries | Memory patterns for agent persistence |
| **16** — Multi-Agent & Swarms | Orchestrator-worker, role-based crews | Advanced multi-agent demo patterns |

## Best practices drawn from this curriculum

1. **BUILD IT → USE IT → SHIP IT** — Don't just teach concepts. Every module should produce a student artifact (prompt, skill, agent, MCP server).
2. **Placement first** — The `/find-your-level` 10-question quiz can be adapted as workshop pre-assessment.
3. **Lesson structure template**: MOTTO → PROBLEM → CONCEPT → BUILD IT → USE IT → SHIP IT — Reusable for any workshop module.
4. **Output artifacts** are the student's portfolio, not homework. Design workshop modules so each produces something the student can take away and reuse.

## Installing curriculum skills into Hermes

```bash
cd ~/workspace/ai-engineering-from-scratch
python3 scripts/install_skills.py ~/.hermes/profiles/main/skills/ --type skill --layout skills --force
```

This installs ~388+ skill artifacts from `phases/*/outputs/` into the Hermes skills directory.

**Caveat**: The built-in placement quiz (`find-your-level`) and per-phase quiz (`check-understanding`) live in `.claude/skills/` and are NOT included by `install_skills.py`. Copy them manually if needed:

```bash
cp -r ~/workspace/ai-engineering-from-scratch/.claude/skills/find-your-level ~/.hermes/profiles/main/skills/
cp -r ~/workspace/ai-engineering-from-scratch/.claude/skills/check-understanding ~/.hermes/profiles/main/skills/
```
