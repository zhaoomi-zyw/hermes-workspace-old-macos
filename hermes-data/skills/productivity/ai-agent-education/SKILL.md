---
name: ai-agent-education
description: Teach non-technical or beginner audiences what AI agents are, how they differ from chatbots, and how to design motivating demos/onboarding paths using Hermes-style agent capabilities.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [ai-agents, education, onboarding, demos, hermes, beginners, students]
---

# AI Agent Education

Use this skill when the user wants to explain AI agents to beginners, students, interns, executives, or other non-specialist audiences; compare agents with traditional chatbots; design demo sessions; or choose a beginner-friendly Hermes installation/onboarding path.

## Core framing

Start with outcomes and relatable metaphors before architecture.

- Traditional chatbot: answers questions in a conversation.
- AI agent: uses tools, files, web, code, memory, schedules, and other systems to complete tasks.
- Beginner-friendly one-liner: **ChatGPT is a smart brain that talks; an agent is a smart brain that can use a computer and tools.**
- Task framing: **chatbot = you ask, it answers; agent = you give a goal, it works toward completion.**

Avoid leading with jargon such as MCP, gateway, tool schemas, provider routing, profiles, or cron internals. Introduce those only after the audience has seen a concrete demo.

## Audience-first demo design

1. Ask what the learner already cares about: games, sports, school, coding, anime, music, short videos, college/career planning, or productivity.
2. Pick one concrete task they can see working in minutes.
3. Demonstrate that the agent acts, not just explains: create a file, run code, search, summarize, schedule, or preview output.
4. Let the learner supply the theme or constraints so the artifact feels personal.
5. Explain the underlying agent capabilities only after the artifact works.

## High-interest beginner scenarios

### Student learning coach

Show how an agent can remember goals, classify mistakes, generate practice plans, and schedule review prompts.

Good demo prompts:

```text
You are my high-school learning coach. Ask me 5 questions to build my study profile, then create a 7-day plan for improving math and English.
```

```text
Classify these three wrong problems by knowledge point, explain the mistake pattern, and make a 30-minute review plan for tomorrow.
```

Teaching point: a chatbot gives advice once; an agent can become an ongoing study system with memory and scheduled reminders.

### Personal webpage or mini-game

This is often the strongest first demo because the learner can see a working artifact.

Good demo prompts:

```text
Create a single-file HTML personal homepage for a high-school student. Use a blue-purple tech style. Sections: self-introduction, hobbies, favorite games, future goals. Save it as an HTML file and tell me how to open it.
```

```text
Create a browser-based guess-the-number game with an input box, guess button, attempt counter, hints, and restart button. Make the UI fun for a teenager.
```

Teaching point: a chatbot gives code to copy; an agent can create files, run/check them, and revise based on feedback.

### Sports, esports, or fandom analyst

Use interests like basketball, football, League of Legends, Valorant, CS, Formula 1, or local teams.

Good demo prompt:

```text
Help a high-school student understand how an AI agent could track a favorite team/player. Give 5 useful things it could monitor and a sample weekly report.
```

Teaching point: agents can combine web search, data organization, scheduled updates, and personalized summaries.

### Research assistant for curious questions

Good topics: how recommendation algorithms work, whether AI will replace programmers, how autonomous driving works, what careers are safer in the AI era, how AI image generation works.

Good demo prompt:

```text
Explain why AI agents are a future trend for a high-school student. Use three analogies: game NPC, Iron Man's Jarvis, and a study assistant.
```

Teaching point: agents can search current information, judge relevance, organize sources, and produce a student-level explanation.

### Personal automation assistant

Examples: homework reminders, daily vocabulary, exam countdowns, weekly learning reports, workout tracking, competition/news alerts.

Teaching point: agents can work when the user is not actively chatting; scheduled tasks are a major difference from one-off chatbot usage.

## Recommended teaching flow for a first session

For a 30-minute intro:

1. 5 minutes — concept: chatbot answers; agent completes tasks.
2. 10 minutes — visible build demo, preferably a webpage or mini-game chosen by the learner.
3. 5 minutes — research/summarization demo on a topic they care about.
4. 5 minutes — automation concept: daily reminders, learning coach, weekly reports.
5. 5 minutes — learner drives: ask them to give one goal and let the agent attempt it.

## Installation/onboarding recommendations

For a first exposure, do **not** start with a complex installation if a working Hermes environment already exists.

Preferred path:

1. Use an already-configured WebUI or CLI session for the first demo.
2. If the learner wants to continue and has technical interest, install Hermes CLI next.
3. Add WebUI, cron, messaging gateway, profiles, MCP, or custom providers only after they have completed 2-3 small wins.

For a high-school beginner:

- Best first experience: WebUI on a preconfigured machine.
- Best technical next step: Hermes CLI plus VS Code.
- Avoid initially: gateway setup, multi-profile architecture, MCP servers, custom provider debugging, and advanced cron configuration.

## Hermes-specific teaching points

Use Hermes features as concrete examples of agent capabilities:

- Tools: the agent can read/write files, run terminal commands, search, browse, and analyze media.
- Skills: reusable workflows make the agent better at repeated classes of tasks.
- Memory: the agent can remember durable preferences and context across sessions.
- Cron: the agent can run scheduled tasks and send reports without being manually prompted.
- Profiles: separate identities/projects keep contexts isolated.
- Gateway/WebUI: the same agent can be used through web, CLI, messaging platforms, or APIs.

## Pitfalls

- Do not over-explain architecture before the learner sees a working result.
- Do not make installation the first experience unless the learner explicitly wants system setup.
- Avoid promising magic autonomy. Emphasize that agents are powerful but still need clear goals, verification, and permissions.
- For young learners, keep demos safe: no destructive commands, no credential sharing, no uncontrolled spending on API keys.

## References

- `references/high-school-agent-onboarding.md` — condensed session pattern for teaching a high-school intern why agents matter and how to pick the first Hermes onboarding mode.
