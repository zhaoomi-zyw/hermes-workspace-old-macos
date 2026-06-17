---
name: educational-workshop-design
description: Design beginner-friendly educational workshops, slide decks, and hands-on lesson materials through iterative requirement discovery.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [education, workshop, courseware, lesson-plan, html-deck, teaching]
---

# Educational Workshop Design

Use this skill when the user asks to design a class, workshop, training session, lesson plan, HTML courseware, hands-on lab, or teaching material for a specific audience.

## Core Principle

Design the learning experience before designing the artifact.

Do not jump straight into slides. First clarify:

1. Who the learner is
2. What they already know
3. Why they should care
4. What they should be able to do by the end
5. What concrete artifact or takeaway they should leave with
6. How much time is available
7. What language and tone the final materials should use

## Iterative Q&A Workflow

When the user wants to co-design the workshop, proceed as a structured interview:

1. Create or update a working-notes file in the active workspace.
2. Create an outline file early, even if it is v1.
3. Ask one key question at a time.
4. After each answer, immediately update the outline and notes.
5. Summarize the confirmed decision briefly.
6. Ask the next question.

Avoid asking a long survey all at once unless the user explicitly requests it.

Good question sequence:

1. Audience background and interests
2. Desired style: inspirational, hands-on, career-oriented, or balanced
3. Final student takeaways
4. Delivery format: slide deck, handouts, demo files, setup guide
5. Main demo path
6. Time allocation
7. Visual style
8. Language of final materials
9. Installation or setup scope
10. Safety/guardrails and what not to teach

## Output Artifacts

Common artifact set:

- `working-notes.md` — evolving requirements and decisions
- `references/ai-agent-hermes-german-high-school-workshop.md` — example reference for a 2-hour English workshop introducing AI agents/Hermes to a German high school intern in China
- `outline-v1.md`, `outline-v2.md`, etc. — learner-facing structure
- HTML slide deck — for projection and teaching
- HTML handout — for the learner to revisit later
- Prompt-template handout — reusable prompts for the learner
- Setup guide — minimal installation path if needed
- Demo starter or completed file — the hands-on artifact made during class

For HTML decks, combine with the `claude-design` skill when available, and follow its deck rules: fixed 16:9 canvas, keyboard navigation, sparse slides, verified local file.

## Language Handling

Separate working language from delivery language.

If the user wants to discuss in one language but deliver in another:

- Keep notes in the working language if useful for the user.
- Keep final slides, learner-facing outlines, prompts, and handouts in the delivery language.
- Translate ideas culturally, not literally.
- Avoid local jokes or cultural references the learner may not understand.

## Teaching Beginner Audiences

For beginners, especially teenagers or non-specialists:

- Start from relatable scenarios, not architecture diagrams.
- Prefer analogies over jargon.
- Use “see it work” demos early.
- Make the learner choose or influence the demo.
- Keep one concrete takeaway they can show or reuse.
- Explain advanced terms only after the learner has seen why they matter.

Useful framing pattern:

- Old way: ask a chatbot a question.
- New way: delegate a task to an agent.
- Future skill: learning how to direct agents.

## Hands-on Workshop Structure

For a 2-hour beginner workshop, a balanced structure works well:

1. Interest discovery and icebreaker
2. Core concept explanation
3. Live demo from idea to artifact
4. Second demo showing research/study assistance
5. Learner hands-on challenge
6. Future trend / career connection
7. Setup and next steps

Always keep the schedule adjustable. If the learner becomes excited by one path, spend more time there and compress abstract discussion.

## Pitfalls

- Do not overfit the lesson before discovering the learner's interests.
- Do not make installation the first experience; setup friction kills curiosity.
- Do not explain tool architecture before demonstrating value.
- Do not create a deck full of text and call it a workshop.
- Do not assume the final delivery language is the same as the planning conversation language.
- Do not promise a hands-on artifact unless there is enough time to create and verify it.

## Verification

Before final delivery:

- Confirm all stated requirements are represented in notes or outline.
- Confirm timing adds up to the total session length.
- Confirm final learner-facing language matches the user's requested output language.
- If HTML files are generated, verify they exist and open without obvious errors.
- If prompts are provided, make them copy-paste ready.
