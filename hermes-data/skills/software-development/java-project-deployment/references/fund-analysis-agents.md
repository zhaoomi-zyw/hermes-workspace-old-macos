# Fund Analysis Agents — Deployment Notes

## Project
- GitHub: hexliulab/fund-analysis-agents
- Tech: Java 21, Spring Boot 3.4, Spring AI 1.0, Vue 3, MySQL 8.0, Redis 7
- Default credentials: admin / admin2026
- Port: 8080

## Known Bugs & Workarounds

### 1. Prompts not loading from nested JAR (FIXED)

The `PromptLoader` uses `ClassPathResource` to load prompt templates from `prompts/` inside `fund-agent-core` JAR. When packaged as a Spring Boot fat JAR, these nested JAR resources fail to load.

**Root cause**: `ClassPathResource` cannot read from `BOOT-INF/lib/fund-agent-core-0.0.1-SNAPSHOT.jar!/prompts/`.

**Permanent fix** (applied to `PromptLoader.java`):
```java
// Fallback: use user.dir (resolves symlinks), NOT user.home
private static final String FALLBACK_DIR =
    System.getProperty("user.dir") + "/prompts/";
```
- `System.getProperty("user.home")` → `/Users/omi` — does NOT resolve `~/fund-analysis-agents` symlink
- `System.getProperty("user.dir")` → real path because app starts with `cd ~/fund-analysis-agents`

After changing PromptLoader, rebuild:
```bash
cd ~/fund-analysis-agents && \
  JAVA_HOME="/usr/local/opt/openjdk@21" \
  mvn clean package -DskipTests
```

**Old workaround** (no longer needed): Extract prompts to /tmp and add to classpath.

### 2. AES encryption key
The application uses AES-256-ECB with key `FundAnalysis2026FundAnalysis2026` (32 bytes, hardcoded in CryptoUtil.java). API keys stored in `TM_AI_PROVIDER_CONFIG.API_KEY_ENCRYPTED` must be encrypted with this key using `Cipher.getInstance("AES")` (which defaults to AES/ECB/PKCS5Padding).

### 3. User password BCrypt bug
The V2 migration seed hash does NOT match "admin2026". Must regenerate via admin API or direct SQL update with a known-good BCrypt hash.

## Database Tables
- TM_USER: user accounts
- TM_AI_PROVIDER_CONFIG: LLM provider keys (encrypted)
- TM_ANALYSIS_TASK: scheduled analysis tasks
- TM_TASK_EXECUTION: task execution history with STATUS/PROGRESS/ERROR_MESSAGE
- TM_ANALYSIS_REPORT: completed analysis results with JSON columns per agent
- TM_WATCH_LIST: user's tracked funds
