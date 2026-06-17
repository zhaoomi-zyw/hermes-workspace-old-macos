# Skill Update: idea-workflow (2026-05-24)

## What happened
- User explored hermes-desktop skill (agent-desktop), discovered it's a CLI-only tool with no GUI, deleted it
- User asked to install idea-workflow from github.com/AkoliteZA/hermes-agent-idea-workflow
- Skill files were cloned but placed in `~/.hermes/skills/idea-workflow/` as a nested umbrella — sub-skills did NOT appear in `hermes skills list`
- Created umbrella `idea-workflow` skill at `software-development/idea-workflow`
- Sub-skills still need to be copied to top-level `~/.hermes/skills/` for discovery

## Fix applied
Created umbrella skill at `software-development/idea-workflow` referencing the 4 sub-skills.

## TODO
Copy the 4 sub-skills to top-level for discovery:
```bash
cp -r ~/.hermes/skills/idea-workflow/idea-superpowers-suite \
       ~/.hermes/skills/idea-workflow/idea-to-design-doc \
       ~/.hermes/skills/idea-workflow/idea-to-implementation-doc \
       ~/.hermes/skills/idea-workflow/idea-to-ui-design-brief \
       ~/.hermes/skills/
```

## Lesson
Hermes skills must be at `~/.hermes/skills/<skill-name>/SKILL.md` (top level or correct category subdir) to appear in `hermes skills list`. Nested subdirectories under a skill directory are NOT auto-discovered as separate skills. For multi-skill repos, either install each as a top-level skill, or ensure the umbrella skill is properly categorized and sub-skills are referenced by path.