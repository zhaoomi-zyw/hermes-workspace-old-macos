# Workshop Outline v1

## Working Title

From Chatbots to AI Agents: How Tools Like Hermes Turn AI into a Real Digital Assistant

## Audience

- German high school student
- Currently doing a short internship in China
- Beginner-friendly, no deep technical background assumed
- Interested in practical, relatable examples rather than abstract AI theory

## Duration

2 hours

## Learning Goals

By the end of the workshop, the student should understand:

1. The difference between a chatbot and an AI agent
2. Why agents are becoming an important future trend
3. How an agent can use tools such as files, browser, terminal, coding, memory, and automation
4. How Hermes can help with real tasks, not just conversations
5. How to start using an agent safely and productively as a student

## Confirmed Requirements

- The student’s specific interests are not known in advance.
- The workshop should start with a short interest-discovery segment.
- The deck and live demos should be flexible enough to adapt to the student’s answer.
- Default examples should cover several likely interest areas: school, AI/coding, China internship, football/sports, gaming/esports, and future career planning.
- Overall workshop style: balanced.
  - First: inspire curiosity and explain why agents matter.
  - Middle: let the student experience a hands-on mini project.
  - End: connect agent literacy to future learning, university choices, and careers.
- Final takeaways for the student:
  - One small HTML artifact created during the workshop, such as a personal page, internship diary, mini game, or interest-based page.
  - A set of reusable AI agent prompt templates, such as study coach, research assistant, career explorer, internship diary helper, and coding buddy.
- Final courseware format: multiple HTML files, not a single slide deck.
  - Main course page / lesson guide
  - Chatbot vs Agent comparison page
  - Live demo guide page
  - Prompt template handout page
  - Student follow-up / installation guide page
  - Hermes usage comparison page
  - Instructor runbook page for Omi
- Visual style: professional tech, but not childish.
  - Modern, clean, and credible
  - Light background as the default for readability
  - Use selective dark/tech sections for contrast
  - Avoid overdone gradients, flashy effects, childish colors, and generic AI marketing visuals
  - Suitable for a German high school student in a China internship context
- Hermes coverage depth: layered.
  - During the workshop: introduce Hermes at a medium depth as an example of an AI agent framework that can use tools, files, browser, code, memory, and automation.
  - Avoid detailed configuration during the main lesson.
  - Add a separate “If you want to go deeper” section/page covering CLI, WebUI, Gateway, Skills, Memory, Cron, Profiles, MCP, and integrations at a high level.
- Hands-on participation level: guided co-piloting.
  - The student should personally paste and run several prepared prompts.
  - Omi guides, explains, and helps choose the path, but the student experiences directing the agent.
  - All important prompts should be pre-written and copy-paste ready.
  - The prompts should produce predictable preset outcomes, so the workshop does not depend on improvising under time pressure.
- Default demo strategy: prepare multiple routes, but use “My China Internship Diary” as the fallback.
  - If the student has no strong preference, build an English HTML page about his China internship experience.
  - If he likes coding/gaming, switch to a simple browser game.
  - If he cares about future study/career, switch to an AI Learning Portfolio.
  - If he focuses on school, switch to an AI Study Coach prompt/workflow.
- Classroom hardware setup: two MacBooks.
  - MacBook A: Omi’s current machine, already has Hermes fully installed and configured. This is the main demo machine.
  - MacBook B: a clean macOS machine with only macOS installed. This is used to explain the beginner installation path and contrast setup complexity.
- Add one dedicated HTML page comparing ways to use Hermes.
  - Compare WebUI, CLI, messaging/gateway, cron/automation, profiles/advanced integrations.
  - Recommended approach for this student: WebUI-first, with CLI shown as an advanced next step.
  - For the WebUI path, use Omi’s current third-party `nesquena/hermes-webui` setup, not the official/built-in Hermes dashboard/plugin route.

## Draft Structure

### 1. Icebreaker: Interest Discovery — 10 min

Purpose:
- Discover what the student is actually interested in
- Connect AI agents to his daily life, school, internship, hobbies, and future plans
- Choose the most relevant live demo path based on his answer

Possible prompts:
- If you had an AI assistant that could use a computer, what would you want it to do for you?
- Would you use it for school, coding, travel, football, games, or career planning?
- Which sounds more interesting: building something, learning something, analyzing something, or automating something?

Interest-to-demo mapping:
- Coding / AI / technology → build a mini website or browser game
- School / exams → create an AI study coach
- China internship → create a China internship diary or survival assistant
- Football / sports → create a match or player analysis assistant
- Gaming / esports → create a gaming stats or strategy assistant
- Future career → create an AI career exploration plan

### 2. Chatbot vs Agent — 20 min

Core message:
- A chatbot answers questions.
- An agent completes tasks.

Key comparison:
- Chatbot: talks
- Agent: talks + uses tools + works with files + searches + codes + remembers + automates

Analogy:
- ChatGPT is like a smart person in a chat window.
- An AI agent is like a smart assistant sitting at a computer.

### 3. Live Demo 1: From Idea to Mini Website — 25 min

Suggested demo:
- Build a small HTML page: “My China Internship Diary” or “My AI Learning Portfolio”

What to show:
- The agent creates a file
- Writes HTML/CSS/JS
- Revises based on feedback
- Produces a real artifact the student can open

### 4. Live Demo 2: Agent as Study / Research Assistant — 20 min

Suggested topics:
- How should a German high school student start learning AI?
- What careers will be changed by AI agents?
- How can I summarize my China internship experience?

What to show:
- The agent can structure information
- Explain concepts at the right level
- Produce a study plan or summary

### 5. Student Hands-on Challenge — 25 min

Student chooses one:

A. Personal mini website
B. Simple browser game
C. AI study coach prompt
D. China internship survival assistant
E. Football/esports analysis assistant

Goal:
- Student experiences directing an agent, not just watching a demo

### 6. Why AI Agents Are the Future — 10 min

Core idea:
- The future skill is not only asking AI questions, but delegating tasks to AI systems.

Message:
- Search literacy was important in the 2000s.
- Prompt literacy is important now.
- Agent literacy will be important next.

### 7. How to Start After Today — 10 min

Recommended path:

1. First experience: use Omi’s Hermes WebUI during the workshop
2. Next step: install VS Code and Hermes CLI if interested
3. Later: learn skills, memory, automation, GitHub, and deployment

## Additional Confirmed Requirements

### Clean MacBook installation demo

- The second clean MacBook should not be only theoretical.
- The workshop should include a step-by-step installation and setup demo based on the final recommended path.
- This demo should use the chosen student-friendly path, not the full advanced Hermes setup.

### Installation guide content

- The courseware must include concrete installation commands.
- The guide should include screenshots for the installation and first-use path.
- Screenshots should be prepared after the final installation route is confirmed and tested.

### Prompt template count

- The number of prompt templates should be determined by the timing of each workshop section.
- Prompts should map directly to the hands-on moments, not be an oversized template library.
- Each prompt should be copy-paste ready and produce a predictable result.

### Fallback artifacts

- Prepare fallback completed HTML artifacts in advance.
- These are used if live generation fails, runs too slowly, or produces a poor result during class.
- The fallback should still match the workshop’s main routes, especially “My China Internship Diary”.

### Packaging

- Final HTML files should be packaged into one folder that can be copied to the student.
- The package should include course pages, prompt templates, installation guide, fallback demo artifacts, and any local assets.

### Language format

- Student-facing courseware should be trilingual: English + German + Chinese.
- English and German should be the primary visible languages.
- Chinese can be smaller, secondary, or used as instructor support text.
- Discussion with Omi remains in Chinese.

## Still Open / Needs Refinement

1. What exact installation path should be demonstrated on the clean MacBook?
2. Which screenshots are required for the installation guide?
3. How many prepared prompts fit into each timed section?
4. Which fallback HTML artifacts should be built first?
5. Should we create an instructor run-of-show script in addition to student-facing HTML files?
