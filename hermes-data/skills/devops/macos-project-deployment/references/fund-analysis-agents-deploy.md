# Fund Analysis Agents Deployment — macOS Playbook

## Project
- Repo: https://github.com/hexliulab/fund-analysis-agents
- Stack: Java 21 + Spring Boot 3.4 + Spring AI + Vue 3 + MySQL + Redis
- Deploy: `scripts/setup.sh` (one-click)

## Prerequisites

```bash
brew install openjdk@21 maven docker colima docker-compose
colima start --cpu 2 --memory 4
export JAVA_HOME="/usr/local/opt/openjdk@21"
export PATH="$JAVA_HOME/bin:$PATH"
```

## .env Setup

The project needs at least one LLM API key (DashScope/OpenAI/DeepSeek).
Copy `.env.example` → `.env` and inject the key.

**Critical**: The .env must NOT have inline comments. The example file is clean.

## setup.sh Fixes Required

### 1. Java version detection (line ~66)

Original (GNU-only):
```bash
java_ver=$(java -version 2>&1 | head -1 | grep -oE '"[0-9]+"' | tr -d '"')
```

Fixed (macOS compatible):
```bash
java_ver=$(java -version 2>&1 | head -1 | awk -F'"' '{print $2}' | cut -d. -f1)
```

### 2. Docker Compose plugin

Ensure `docker-compose` formula is installed:
```bash
brew install docker-compose
```

## Common Failure Modes

1. **"openai: error: invalid choice: 'API'"** — .env has inline comments after values. The `OPENAI_API_KEY=*** OpenAI API Key` format causes bash to try executing `OpenAI` as a command after sourcing. Fix: remove all inline comments.

2. **"Docker Compose not found"** — Only `docker` CLI from colima, not the compose plugin. Fix: `brew install docker-compose`.

3. **"Java 21+ required, found: "** — BSD grep can't parse the version. Fix: use awk as above.
