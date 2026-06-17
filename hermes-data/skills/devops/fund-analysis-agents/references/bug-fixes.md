# Bug Fixes for fund-analysis-agents Deployment

All bugs encountered and fixed during initial deployment on macOS (26.4.1, Apple Silicon).

---

## Bug 1: Java Version Detection Fails on macOS

**Symptom**: setup.sh step 1 reports "Java 21+ required, found: " even though Java 21 is installed.

**Root Cause**: setup.sh uses GNU grep syntax `grep -oE '"[0-9]+"'` which doesn't work on macOS BSD grep.

**Fix**: Replace in `scripts/setup.sh`:
```bash
# BEFORE (broken):
local java_ver=$(java -version 2>&1 | head -1 | grep -oE '"[0-9]+"' | tr -d '"')

# AFTER (fixed):
local java_ver=$(java -version 2>&1 | head -1 | awk -F'"' '{print $2}' | cut -d. -f1)
```

**Detection**: `grep "grep -oE.*\[0-9\]\+" scripts/setup.sh`

---

## Bug 2: Frontend Build Fails — Missing LogsView.vue

**Symptom**: `npm run build` fails with `ENOENT: no such file or directory, open '.../LogsView.vue'`

**Root Cause**: The Vue router (`src/router/index.ts`) imports `@/views/logs/LogsView.vue` but the file was not committed to the repository.

**Fix**: Create a minimal placeholder component:
```bash
mkdir -p fund-administration/src/main/webapp/src/views/logs
cat > fund-administration/src/main/webapp/src/views/logs/LogsView.vue << 'EOF'
<template>
  <div class="logs-container">
    <el-card>
      <template #header><span>系统日志</span></template>
      <el-empty description="日志功能开发中" />
    </el-card>
  </div>
</template>
<script setup lang="ts"></script>
<style scoped>.logs-container { padding: 20px; }</style>
EOF
```

---

## Bug 3: Admin Login Fails — "invalid username or password"

**Symptom**: Login with `admin`/`admin2026` returns HTTP 60001 "invalid username or password".

**Root Cause**: The V2 migration (`V2__init_data.sql`) inserts a BCrypt hash that does NOT match `admin2026`. The V4 migration (`V4__auth_enhancement.sql`) is supposed to update it, but the hash in V4 also doesn't match. The actually-inserted hash comes from `sql/02_data.sql` which is for a different password.

**Fix**: Generate correct BCrypt hash and update the database:
```python
import bcrypt, pymysql
h = bcrypt.hashpw(b'admin2026', bcrypt.gensalt()).decode()
c = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='fund_analysis_2026', database='fund_analysis')
c.cursor().execute('UPDATE TM_USER SET PASSWORD_HASH=%s WHERE USERNAME=%s', (h, 'admin'))
c.commit()
```

**Verification**: `curl -s http://localhost:8080/api/auth/login -X POST -H "Content-Type: application/json" -d '{"username":"admin","password":"admin2026"}'` should return HTTP 200 with JWT token.

---

## Bug 4: "Decryption failed" on Analysis Trigger

**Symptom**: Triggering analysis succeeds but task execution shows STATUS=FAILED with "Decryption failed". Stack trace: `NullPointerException: Cannot invoke "String.getBytes" because "src" is null` at `CryptoUtil.decrypt:44`.

**Root Cause**: The DeepSeek API key is in `.env` but NOT in the database table `TM_AI_PROVIDER_CONFIG`. The `API_KEY_ENCRYPTED` column is NULL. The application reads the key from the database (not from env), and attempts to decrypt a NULL value.

**Fix**: Use the API to save the provider config — the application will encrypt and store the key internally:
```python
import urllib.request, json
# Login first to get token, then:
api('POST', '/api/ai/providers', {
    'id': 1,
    'providerCode': 'deepseek',
    'providerName': 'DeepSeek',
    'providerType': 'openai',
    'apiKeyEncrypted': raw_api_key,  # plaintext — server encrypts it
    'baseUrl': 'https://api.deepseek.com',
    'enabled': 1  # Must be Integer, NOT boolean true!
}, token)
```

**Critical**: `enabled` must be passed as `1` (Integer), NOT `true` (boolean). Jackson deserialization fails with `MismatchedInputException: Cannot deserialize value of type Integer from Boolean value`.

**Encryption details**: AES-256-ECB, key = `FundAnalysis2026FundAnalysis2026` (32 bytes), PKCS5Padding, Base64-encoded. Defined in `fund-common/.../CryptoUtil.java`.

---

## Bug 5: "Prompt not found: debate/bullish-researcher-system"

**Symptom**: Tasks fail with `RuntimeException: Prompt not found: debate/bullish-researcher-system`. The prompt `.txt` files exist in `fund-agent-core/src/main/resources/prompts/debate/` and are inside the nested JAR at `BOOT-INF/lib/fund-agent-core-0.0.1-SNAPSHOT.jar`, but `ClassPathResource` cannot read from nested Spring Boot JARs.

**Root Cause**: Spring Boot's `ClassPathResource` uses the application classloader, which cannot resolve resources from nested JARs inside the fat JAR on some Java versions.

**Fix (two parts)**:

1. Modify `fund-agent-core/.../PromptLoader.java` to add filesystem fallback:
```java
private String readResource(String path) {
    // 1. Try classpath
    try {
        var resource = new ClassPathResource(BASE_PATH + path + ".txt");
        return resource.getContentAsString(StandardCharsets.UTF_8);
    } catch (IOException e) {
        log.debug("classpath 加载失败, 尝试文件系统: {}", path);
    }
    // 2. Fallback: filesystem
    Path filePath = Paths.get("prompts", path + ".txt");
    if (Files.exists(filePath)) {
        return Files.readString(filePath, StandardCharsets.UTF_8);
    }
    throw new RuntimeException("Prompt not found: " + path);
}
```

2. Create symlink in project root:
```bash
ln -sfn fund-agent-core/src/main/resources/prompts prompts
```

3. Rebuild: `mvn clean package -DskipTests`

---

## Bug 6: `.env` Inline Comments Break `source`

**Symptom**: Bash `source .env` executes `openai` CLI with invalid arguments.

**Root Cause**: Writing env vars with comments on the same line like `DASHSCOPE_API_KEY=*** OpenAI API Key` causes bash to interpret the comment text as a command after the assignment. The `openai` CLI from the Hermes venv gets invoked.

**Fix**: Always keep env var assignments on their own line. Use `# ` prefix for comments on separate lines.
