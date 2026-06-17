# High-school intern onboarding pattern for AI agents

This reference captures a successful framing for teaching a high-school student why Hermes-style agents are different from traditional chatbots.

## Key message

Do not begin with architecture. Begin with a familiar contrast:

- ChatGPT/chatbot: like a smart classmate in a chat window; it answers when asked.
- Agent: like a smart classmate sitting at the computer; it can use tools, create files, run code, search, remember preferences, and work on schedules.

Short version:

> ChatGPT is a smart brain that talks. An agent is a smart brain that can use a computer and tools.

## Scenarios that tend to land well with teenagers

1. Learning coach
   - Builds a study profile.
   - Organizes wrong problems by knowledge point.
   - Creates tomorrow's review plan.
   - Sends recurring practice or reminders.

2. Personal webpage or mini-game
   - Best first live demo.
   - Let the student choose the theme: games, basketball, anime, music, future career, etc.
   - Show that the agent creates an actual file, not just a code block.

3. Sports/esports analyst
   - Tracks favorite teams, players, matches, or schedules.
   - Produces short weekly reports.
   - Good bridge from hobbies to data literacy.

4. Curious research assistant
   - Explains AI, recommendation algorithms, autonomous driving, future careers, or programming learning paths.
   - Ask for a student-level explanation with analogies.

5. Personal automation secretary
   - Daily vocabulary, homework reminders, exam countdowns, weekly learning reports.
   - Teaches the idea that agents can run without an active chat prompt.

6. Programming companion
   - Helps with environment setup, error explanation, code running, and project scaffolding.
   - Start with tiny visible projects: guess-number game, flashcard page, basketball training tracker, to-do list.

## Suggested 30-minute session

1. 5 min — Concept: chatbot answers; agent completes tasks.
2. 10 min — Build a visible artifact, ideally a webpage or mini-game.
3. 5 min — Research/summarization demo on a topic the student chooses.
4. 5 min — Automation concept: daily/weekly scheduled help.
5. 5 min — Student chooses one goal and gives the prompt.

## Recommended first installation path

If teaching on a machine that already has Hermes configured, use that first. Do not let installation friction become the student's first impression.

Recommended progression:

1. First exposure: preconfigured WebUI.
2. If interested in tech: install/use Hermes CLI and VS Code.
3. Later: cron, skills, profiles, gateway/messaging, MCP, provider configuration.

For non-technical high-school beginners, WebUI is the best first interface. For coding-curious students, CLI is a good second step.

## Sample prompts

```text
Help me build a single-file HTML personal homepage for a high-school student. Use a blue-purple tech style and include hobbies, favorite games, and future goals.
```

```text
Make a browser-based guess-the-number game with hints, attempt count, and a restart button. Keep it fun and easy to understand.
```

```text
You are my high-school study coach. Ask me 5 questions, then create a 7-day plan to improve math and English.
```

```text
Explain AI agents versus ChatGPT for a high-school student using three analogies: game NPC, Iron Man's Jarvis, and a study assistant.
```

## Teaching cautions

- Avoid advanced terms until after the demo works.
- Avoid gateway/profile/MCP/provider details during the first exposure.
- Keep claims realistic: agents still need human verification and safe permissions.
- Prefer 'let's make something you can open' over 'let me explain how it works.'
