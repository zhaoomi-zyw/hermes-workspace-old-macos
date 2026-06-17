# Live Delivery Checklist — AI Agent / Hermes Beginner Workshop

Use this checklist when building a time-boxed AI Agent workshop for first-time learners, especially international interns or students.

## Audience and language

- Confirm learner level and interests early with a short icebreaker.
- Keep the main learner-facing material in the learner's strongest language(s).
- Use instructor notes for local-language explanations instead of mixing too much explanatory text into the student view.
- For Omi's German high-school intern scenario: English + German are primary; Chinese should appear as smaller instructor/assistant notes.

## Course structure

A reliable 2-hour flow:

1. 0:00-0:10 — Icebreaker and interest discovery.
2. 0:10-0:30 — Chatbot vs agent, with concrete examples.
3. 0:30-0:55 — Guided live demo that creates a visible artifact.
4. 0:55-1:15 — Second demo: study/research/career assistant.
5. 1:15-1:40 — Student guided challenge using prepared prompts.
6. 1:40-1:50 — Why agents matter for future work.
7. 1:50-2:00 — Installation or next steps.

## Prompt design

- Every prompt should map to a specific course moment.
- Use prewritten copy-paste prompts for all key learner interactions.
- Keep prompts predictable enough for live classroom success.
- Include optional branches for common interests:
  - China internship diary / survival assistant
  - simple browser game
  - AI study coach
  - learning portfolio
  - sports or gaming analysis
  - career exploration

## Fallback plan

- Prepare at least one complete fallback artifact before class.
- The default beginner-friendly fallback can be `My China Internship Diary`.
- The instructor runbook should state exactly when to abandon live generation and open the fallback.
- Fallback files should be local HTML so they work offline.

## Installation demo

- If using a clean MacBook, rehearse installation on that machine type before class.
- Include exact commands only after verification.
- Add screenshots for the expected successful states.
- Show WebUI first if it is the intended beginner interface; mention CLI only as an advanced follow-up.

## Deliverable packaging

Package as a directory, not a single monolithic file:

- `index.html` landing page
- concept pages, e.g. chatbot vs agent
- live demo guide
- prompt template handout
- Hermes usage overview
- student next steps / installation guide
- `instructor-runbook.html`
- `fallbacks/` containing offline demo artifacts
- `assets/` containing CSS and screenshots
- `README.md` explaining how to open and use the package

## Verification before delivery

- Open the package landing page locally.
- Check browser console for JavaScript errors if the pages use JS.
- Verify internal links and fallback files.
- Zip the folder only after local verification.
