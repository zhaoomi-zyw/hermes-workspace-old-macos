---
name: educational-workshop-courseware
description: Design educational workshops and HTML courseware/decks through iterative Q&A, especially for beginner or student audiences.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [education, workshop, courseware, html, deck, curriculum, beginner-friendly]
    related_skills: [claude-design, powerpoint, pdf-generation]
---

# Educational Workshop Courseware

Use this skill when the user wants to plan, refine, or produce teaching materials, workshop decks, interactive HTML lessons, student handouts, or installation/learning guides.

This is a class-level skill for turning a loose teaching goal into a structured courseware package. It works especially well when the audience is a beginner, student, intern, non-specialist, or cross-cultural learner.

## Core Principle

Do not jump directly to a polished deck. First build a teaching brief, then refine it through Q&A, then generate artifacts.

For Omi, it is acceptable and often preferred to discuss and refine requirements in Chinese, while producing final audience-facing outlines, slide copy, HTML pages, prompts, and handouts in English when the learner/audience is international.

## Workflow

1. **Capture the teaching brief**
   - Audience: age, background, country/language, technical level, motivation.
   - Duration: total time, preferred pacing, hands-on vs lecture ratio.
   - Goal: what the student should understand, feel, and be able to do by the end.
   - Constraints: available computer, installed tools, internet/API access, classroom format.

2. **Create a living notes file**
   - For multi-turn planning, create a project folder under the active workspace.
   - Save `working-notes.md` with audience, goals, constraints, candidate demos, and decisions.
   - Keep appending or patching the notes as the user answers questions.
   - Do not rely only on conversation context when the user says the final artifact will come later.

3. **Produce a versioned outline early**
   - Write `outline-v1.md` in the target output language.
   - Include title, audience, duration, learning goals, timed agenda, demos, hands-on activity, and open questions.
   - Update the outline after each major requirement clarification.

4. **Use iterative Q&A to refine**
   - Ask one important question at a time unless the user requests a batch.
   - Prefer questions that change the artifact: audience interest, tone, main demo, hands-on depth, installation scope, final format.
   - After the user answers, update the notes/outline before asking the next question.
   - If the user wants student-facing materials in a different language than the planning conversation, keep internal notes in the working language and explicitly mark final artifact language in the outline.

5. **Design for guided co-piloting when students will operate the agent**
   - Do not rely on live prompt improvisation for beginner workshops.
   - Prepare copy-paste-ready prompts that produce predictable outcomes.
   - Let the student paste and run the prepared prompts so they feel they are directing the agent.
   - Keep the instructor in the loop to explain, choose branches, recover from errors, and guide feedback.
   - Include refinement prompts, not only first-shot creation prompts, so the student sees iterative agent control.

6. **Design for engagement before completeness**
   - For students and beginners, use relatable scenarios before terminology.
   - Use analogies, concrete demos, and visible artifacts.
   - Avoid starting with architecture diagrams, acronyms, provider setup, or low-level configuration.

6. **Separate instructor planning from student-facing content**
   - Internal notes can be in the user’s working language.
   - Student-facing slides, handouts, prompts, and installation guide should use the chosen audience language.
   - Mark instructor notes separately if included.

7. **Generate HTML courseware when ready**
   - Use a self-contained HTML deck or pages unless the user requests another format.
   - Include keyboard navigation for decks, clear section titles, timed agenda, demos, and activity prompts.
   - For a workshop, consider multiple artifacts:
     - main slide deck
     - interactive comparison/demo page
     - hands-on challenge cards
     - setup guide
   - Verify files exist and, where possible, open them and check browser console before finalizing.

## Beginner-Friendly Teaching Pattern

A useful structure for technology workshops:

1. Hook: a relatable problem or question.
2. Simple contrast: old way vs new way.
3. Analogy: explain the concept without jargon.
4. Live demo: show something real being created or changed.
5. Hands-on challenge: let the learner direct the tool.
6. Reflection: what changed, why it matters, what to learn next.
7. Optional setup path: how to continue safely after the session.

## AI Agent / Hermes Courseware Pattern

When teaching AI agents versus chatbots:

- Core message: “A chatbot answers questions; an agent completes tasks.”
- Analogy: “ChatGPT is like a smart person in a chat window; an agent is like a smart assistant sitting at a computer.”
- Show capabilities in concrete terms: files, browser, code, memory, automation, scheduled tasks.
- Avoid overloading first-time learners with gateway, profiles, MCP, provider configuration, and cron internals.
- First experience should produce a visible artifact: a mini website, browser game, study plan, or research summary.
- Installation should usually be delayed until after the learner sees a successful demo.

For beginner/intern workshops that must be delivered live:

- Prepare all student-facing prompts as copy-paste blocks. The student should experience directing the agent, but the prompts should be constrained enough to produce predictable outcomes.
- Create fallback artifacts before class, especially for the default demo route, so a slow model call or poor live generation does not break the session.
- If a clean machine will be used, treat installation as a tested demo path, not a theoretical appendix. Include exact commands and screenshots after verification.
- For international learners, generate student-facing courseware in the audience language(s). For Omi’s cross-cultural workshops, English and German may be primary, with smaller Chinese instructor notes.
- When a courseware card or goal contains the same point in English, German, and Chinese, prefer grouping by learning point and stacking the languages vertically inside that card when legibility matters: English first, German second, Chinese third. If the user asks for consistent fonts, set the multilingual lines in that section to the same font family, size, and line-height; do not leave Chinese smaller unless explicitly requested.
- For German high-school intern workshops, keep German translations supportive and concise rather than full duplicate paragraphs when the English is the primary student copy.
- Design live-demo prompts as interactive collection flows when personalization matters: the first prompt should ask the student several guided questions, wait for answers, then generate the final artifact from those answers. This is better than a one-shot artifact prompt for internship diary or reflection pages.
- Package the final courseware as one copyable folder containing HTML pages, prompt handouts, setup guide, screenshots/assets, fallback artifacts, and an instructor runbook.
- Add an instructor runbook when the session is time-boxed: it should say which page to open, what to say, which prompt to paste, what fallback to use, and when to switch machines.

See `references/agent-workshop-for-german-high-school-intern.md` for a concrete session brief and outline pattern.
See `references/agent-workshop-live-delivery-checklist.md` for the live-delivery checklist that emerged from a two-MacBook Hermes workshop plan.
- For beginner Hermes onboarding, prefer WebUI-first in the main lesson and present CLI as an advanced next step unless the user explicitly wants a terminal-first workshop.

See `references/agent-workshop-for-german-high-school-intern.md` for a concrete session brief and outline pattern.
See `references/german-high-school-agent-workshop-pattern.md` for a reusable German high school intern in China pattern, including multi-page HTML courseware, two-MacBook setup, prepared prompt handouts, and Hermes usage-mode comparison.

## Variant: Personal Diary / Reflection Slide Deck

When the user wants a **personal reflection diary** (not a workshop) for a student/intern, presented as a **scroll-snap PPT-style slide deck** with bilingual English + German, use the pattern in `references/personal-diary-slide-deck-pattern.md`.

Key differences from courseware:
- Collect personal experiences via guided Q&A before generating (first impression, what they did, what they learned, cultural observations, AI tools tried, next questions).
- Generate a single scroll-snap slide deck HTML (7 slides: Hero → First Impression → What I Learned → Cultural Observations → AI Tools → Next Steps → Closing).
- Cards within slides for grouped insights, accent boxes for key callouts, checklist for "what I want to learn next."
- Brief German translations under slide headings and in accent boxes (`.de-note` pattern) — never full paragraph duplication.
- Progress dot navigation on the right edge.
- See the reference for the complete component inventory, CSS patterns, and bilingual rules.

See `references/agent-workshop-for-german-high-school-intern.md` for a concrete session brief and outline pattern.
See `references/guided-agent-workshop-prompt-pack.md` for a reusable prompt-pack pattern for beginner agent workshops.
- When the user wants modular courseware, produce multiple linked HTML files rather than one monolithic deck: main guide, comparison page, live demo guide, prompt-template handout, and next-steps/setup guide.
- When editing an existing HTML courseware package, scope CSS changes to the specific section or block being changed, then verify the browser-rendered computed styles and console. See `references/multilingual-html-courseware-layout.md` for the multilingual goal-card pattern.
- For international students, keep final audience-facing content in English and use cross-cultural examples: school, AI/coding, China internship, football/sports, gaming/esports, and career exploration.

See `references/agent-workshop-for-german-high-school-intern.md` for a concrete session brief and outline pattern.

## Pitfalls

- Do not treat courseware generation as only a writing task; it is instructional design plus artifact design.
- Do not ask ten questions at once at the start. Use progressive Q&A and update the outline each time.
- Do not design around the teacher's technical interests if the learner is a beginner; design around learner motivation.
- Do not make the first session primarily about installation. A successful visible demo is usually more motivating.
- Do not mix working-language notes and final-language slide copy without labeling them.
- Do not over-localize examples when the student is international; choose cross-cultural examples and explain local context when useful.
- Do not overlook existing curriculum references. The [AI Engineering from Scratch](https://aiengineeringfromscratch.com) repo (⭐32.8k, 503 lessons) is a free, open-source reference for workshop structure — see `references/ai-engineering-from-scratch-curriculum-reference.md` for key phases and patterns.

## Verification Checklist

Before final response for generated courseware:

- Working notes and outline are saved in the project folder.
- The final audience language matches the requirement.
- The timed agenda sums to the target duration.
- Demos are feasible on the available machine.
- HTML files exist at the stated paths.
- If browser tools are available, the primary HTML opens without console errors.
- The final reply includes exact file paths and a concise summary of what was created.
