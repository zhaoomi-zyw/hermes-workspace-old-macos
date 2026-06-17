---
name: java-project-deployment
description: Deploy Java/Spring Boot multi-module projects on macOS — environment setup, build fixes, database config, and troubleshooting.
version: 1.0
---

# Java Project Deployment on macOS

Deploy Java/Spring Boot projects on macOS with colima (Docker alternative), Homebrew-installed JDK/Maven, and MySQL/Redis via Docker Compose.

## Environment Setup

```bash
# Install dependencies
brew install openjdk@21 maven docker colima

# Start colima (lightweight Docker for macOS)
colima start --cpu 2 --memory 4

# Install docker-compose plugin for colima
brew install docker-compose

# Set JAVA_HOME for the session
export JAVA_HOME="/usr/local/opt/openjdk@21"
export PATH="/usr/local/opt/openjdk@21/bin:$PATH"
```

## Common macOS Traps

### 1. BSD grep vs GNU grep
macOS uses BSD grep. Patterns like `grep -oE '"[0-9]+"'` that work on Linux may fail.
**Fix**: Use `awk` for extraction: `awk -F'"' '{print $2}' | cut -d. -f1`

### 2. sed quoting
BSD sed handles escaping differently. Avoid complex sed with double-quote escaping.
**Fix**: Use Python for non-trivial string replacements in config files.

### 3. .env file format for bash source
When bash sources a `.env` file, inline "comments" like `KEY=value # comment` will try to execute `#` as a command if the value contains special characters or glob patterns.
**Fix**: Always put comments on separate lines. Never mix values and comments on the same line.

### 4. BCrypt password hashes
Pre-generated BCrypt hashes in SQL migration scripts may not match the expected password — always verify with `bcrypt.checkpw()` in Python and regenerate if needed.

```python
import bcrypt
new_hash = bcrypt.hashpw(b'desired_password', bcrypt.gensalt()).decode()
# Update database with new_hash
```

### 5. MySQL root password with $ signs
If MySQL root password contains `$`, bash will try to expand it as a variable.
**Fix**: Use single quotes: `-p'password_here'` not `-p"$password"`.

## Spring Boot Multi-Module Traps

### Nested JAR resource loading

When a fat JAR contains dependency JARs with resources (e.g., prompt templates), `ClassPathResource.getInputStream()` and `getContentAsString()` can fail with `FileNotFoundException` because Spring Boot's nested JAR loader (`org.springframework.boot.loader`) doesn't expose nested-JAR resources as file system paths.

**Check if this is the issue:**
```bash
jar tf fat-jar.jar | grep "your-resource"
jar tf BOOT-INF/lib/dependency.jar | grep "your-resource"
```

**Two-tier fix (preferred):**

1. Try `getContentAsString()` first (works for non-nested resources)
2. Fall back to filesystem with **absolute path** — do NOT use relative paths (`prompts/`) because the JAR's working directory is unpredictable:

```java
// PREFER user.dir (resolves symlinks) over user.home (raw string)
private static final String FALLBACK_DIR =
    System.getProperty("user.dir") + "/prompts/";

private String readResource(String path) {
    try {
        var resource = new ClassPathResource(BASE_PATH + path + ".txt");
        return resource.getContentAsString(StandardCharsets.UTF_8);
    } catch (IOException e) {
        log.debug("classpath failed, trying filesystem: {}", path);
    }
    Path filePath = Paths.get(FALLBACK_DIR, path + ".txt");
    if (Files.exists(filePath)) {
        return Files.readString(filePath, StandardCharsets.UTF_8);
    }
    throw new RuntimeException("Prompt not found: " + path);
}
```

**Key pitfalls**:
- `Paths.get("prompts/", "file.txt")` resolves relative to CWD, which when running `java -jar` can be anything — the user's home, `/`, or the JAR directory.
- **`System.getProperty("user.home")` does NOT resolve symlinks.** If `~/project` is a symlink to `~/.some/deep/path/project`, `user.home + "/project"` will produce a path that doesn't exist. Use `System.getProperty("user.dir")` instead — when the app is started with `cd ~/project && java -jar`, `user.dir` returns the symlink-resolved real path.
- If neither `user.dir` nor `user.home` works, fall back to detecting the JAR location via `getClass().getProtectionDomain().getCodeSource().getLocation()`.

**Rebuild note**: When the resource lives in a sub-module (e.g., `fund-agent-core`), you MUST rebuild that module first before the fat JAR, or the old nested JAR persists:

```bash
mvn clean package -pl fund-agent-core -am -DskipTests  # rebuild sub-module FIRST
mvn clean package -pl fund-application -am -DskipTests  # then fat JAR
```

## Database Debugging with Docker

```bash
# Check tables
docker exec <container> mysql -uroot -p'pass' db -e "SHOW TABLES;"

# Check schema
docker exec <container> mysql -uroot -p'pass' db -e "DESCRIBE table_name;"

# Query with \G for vertical output
docker exec <container> mysql -uroot -p'pass' db -e "SELECT * FROM table\G"
```

## Pre-installed Tool Paths

On this user's macOS:
- Java 21: `/usr/local/opt/openjdk@21`
- Maven: Homebrew-managed
- Docker: via colima
- Node.js: via nvm or Homebrew
