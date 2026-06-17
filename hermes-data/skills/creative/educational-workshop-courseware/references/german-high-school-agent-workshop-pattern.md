# German High School AI Agent Workshop Pattern

Use this reference when planning a beginner-friendly AI Agent / Hermes workshop for an international high school student, especially a German student doing a short internship in China.

## Audience pattern

- German high school student.
- Temporarily in China for a short internship.
- Technical level may be unknown.
- Interest profile may be unknown before the session.
- Working discussion with Omi can be in Chinese, but student-facing materials should be in English unless Omi says otherwise.

## Recommended course shape

For a 2-hour session, use a balanced workshop:

1. Curiosity and concept building.
2. Guided hands-on experience.
3. Future learning and career reflection.

Avoid turning the first session into a configuration lecture. Installation and advanced modules should be optional follow-up content.

## Core message

Use simple contrasts:

- A chatbot answers questions.
- An agent completes tasks.
- ChatGPT is like a smart person in a chat window.
- An AI agent is like a smart assistant sitting at a computer.
- The next skill after search literacy and prompt literacy is agent literacy: learning how to delegate tasks to AI systems.

## Interest discovery first

If the student’s interests are not known, start with a short interest-discovery segment:

- If you had an AI assistant that could use a computer, what would you want it to do for you?
- Would you use it for school, coding, travel, football, games, or career planning?
- Which sounds more interesting: building something, learning something, analyzing something, or automating something?

Map answers to demo routes:

- Coding / AI / technology -> mini website or browser game.
- School / exams -> AI study coach.
- China internship -> China internship diary or survival assistant.
- Football / sports -> match or player analysis assistant.
- Gaming / esports -> gaming stats or strategy assistant.
- Future career -> AI career exploration plan.

## Default demo route

Prepare multiple routes, but use `My China Internship Diary` as the fallback when the student has no strong preference.

Fallback artifact:

- English HTML page about the student’s China internship experience.
- Includes sections such as first impressions, what I learned, cultural observations, useful phrases, and next questions.

Alternative routes:

- Simple browser game for coding/gaming interest.
- AI Learning Portfolio for future study/career interest.
- AI Study Coach prompt/workflow for school focus.

## Hands-on mode

Prefer guided co-piloting:

- The student personally copies and pastes prepared prompts.
- Omi guides, explains, and handles recovery.
- Do not depend on the student inventing prompts live.
- Prepare copy-paste prompts that produce predictable preset outcomes.

Prompt handouts are a core artifact, not optional appendix. Include at least:

1. Interest discovery prompt.
2. Mini artifact creation prompt.
3. Refinement prompt.
4. Personal AI assistant prompt.
5. Study/research/career prompt variants.

## Courseware package format

For this type of session, multiple HTML files usually work better than a single slide deck:

- `index.html` — main course / lesson guide.
- `chatbot-vs-agent.html` — comparison page.
- `live-demo-guide.html` — demo routes and facilitator guide.
- `agent-prompt-templates.html` — copy-paste prompt handout.
- `student-next-steps.html` — setup and follow-up path.
- `ways-to-use-hermes.html` — Hermes usage modes comparison.

Visual style:

- Professional tech, not childish.
- Light background for readability.
- Selective dark/tech sections for contrast.
- Avoid overdone gradients, flashy motion, childish colors, and generic AI marketing visuals.

## Hermes usage comparison page

When explaining ways to use Hermes, compare:

- WebUI.
- CLI.
- Messaging / Gateway.
- Cron / automation.
- Profiles / advanced integrations.

For a beginner student, recommend WebUI-first, with CLI as an advanced next step.

If Omi specifies his current setup, distinguish clearly between:

- API Server: API only, no main chat UI.
- Built-in Dashboard: management UI, not the recommended student chat surface.
- Third-party `nesquena/hermes-webui`: full chat WebUI and the preferred beginner demo surface in Omi’s current setup.

## Two-MacBook classroom setup

If two MacBooks are available:

- MacBook A: fully configured Hermes environment. Use this as the main demo machine.
- MacBook B: clean macOS. Use it to discuss beginner installation path and setup complexity, not as the main live demo machine unless installation is explicitly part of the lesson.

## Pitfalls

- Do not overload a high school beginner with Gateway, Profiles, MCP, provider configuration, or cron internals in the main lesson.
- Do not rely on live improvisation for prompts. Prepare copy-paste prompts and fallback artifacts.
- Do not make the first experience primarily about installation. Show a visible artifact first.
- Do not over-localize examples for a German student. Use China internship examples, but keep language and scenarios internationally understandable.
