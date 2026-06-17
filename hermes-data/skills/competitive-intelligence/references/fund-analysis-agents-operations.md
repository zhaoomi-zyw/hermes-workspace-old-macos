# fund-analysis-agents Operations Reference

Deployment and troubleshooting for the fund-analysis-agents multi-agent analysis platform.

## Quick Start

```bash
# Ensure Docker containers are running
docker start fund-redis fund-mysql

# Start application
cd ~/fund-analysis-agents && source .env && \
  JAVA_HOME="/usr/local/opt/openjdk@21" \
  java -jar fund-application/target/fund-application-0.0.1-SNAPSHOT.jar &

# Verify
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080
```

## Platform Details

- URL: http://localhost:8080
- Login: admin / admin2026
- LLM backend: DeepSeek (configured in .env)
- Analysis pipeline: 6 analysts + 3-round bull/bear debate
- Duration per fund: 3-4 minutes
- Data source: Eastmoney (东方财富)

## Critical Bug: PromptLoader Nested JAR Failure

### Symptom
```
Caused by: java.io.FileNotFoundException: class path resource [prompts/debate/bullish-researcher-system.txt]
cannot be opened because it does not exist
```

### Root Cause
Spring Boot nested JAR (JAR-in-JAR) packaging means `ClassPathResource` cannot resolve paths that work during IDE development. The `fund-agent-core` module is packaged as a nested JAR inside `fund-application`.

### Fix (Iterations)

**Attempt 1 (FAILED): Filesystem fallback with `user.home`**
```java
private static final String FALLBACK_DIR =
    System.getProperty("user.home") + "/fund-analysis-agents/prompts/";
```
Failed because `~/fund-analysis-agents` is a symlink → `/Users/omi/.hermes/profiles/main/home/fund-analysis-agents`, but `user.home` = `/Users/omi`, so the concatenated path doesn't exist.

**Attempt 2 (WORKED): Filesystem fallback with `user.dir`**
```java
private static final String FALLBACK_DIR =
    System.getProperty("user.dir") + "/prompts/";
```
Works because the app is started with `cd ~/fund-analysis-agents`, so `user.dir` resolves to the actual (non-symlinked) path.

### Full PromptLoader Patch

File: `fund-agent-core/src/main/java/com/hex/fund/agent/prompt/PromptLoader.java`

Change:
```java
private static final String FALLBACK_DIR = "prompts/";  // original
```
To:
```java
private static final String FALLBACK_DIR =
    System.getProperty("user.dir") + "/prompts/";  // fixed
```

### Rebuild Commands
```bash
cd ~/fund-analysis-agents
JAVA_HOME="/usr/local/opt/openjdk@21" mvn clean package -DskipTests
```

## Common Operational Issues

### App crashes: "Failed to validate connection" (MySQL/Redis heartbeat failures)
Docker containers stopped. Restart:
```bash
docker start fund-redis fund-mysql
```

### Port 8080 already in use by stale Java process
```bash
kill $(lsof -ti :8080)
```

### App "APPLICATION FAILED TO START" but port responds
Multiple stale Java processes competing. Kill all and restart cleanly:
```bash
kill $(lsof -ti :8080) 2>/dev/null
docker restart fund-redis fund-mysql
# Then restart app
```

### Analysis stuck at "提交中..." (submitting)
Frontend state stale. Refresh browser or navigate directly to /dashboard.

### "所有数据源均不可用" (All data sources unavailable)
Eastmoney API rate limiting or network issue. Wait and retry. Redis cache fallback may still work.

## Verification After Rebuild

Check that PromptLoader has the user.dir fix:
```bash
cd ~/fund-analysis-agents
jar xf BOOT-INF/lib/fund-agent-core-0.0.1-SNAPSHOT.jar \
  com/hex/fund/agent/prompt/PromptLoader.class
javap -c -p com/hex/fund/agent/prompt/PromptLoader.class | grep -c "user.dir"
# Should return 1
```

Check debate phase passes (the failure point):
```bash
grep "开始辩论" logs/app.log | tail -1
# If no "分析执行失败" after this, fix is working
```

## Output Extraction

Report is saved to MySQL. Extract from app.log:
```bash
grep "分析报告已保存" logs/app.log | tail -5
grep "操作建议\|建议仓位\|置信度" logs/app.log | tail -10
```
