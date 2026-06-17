# Spring Boot Nested JAR ClassPath Resource Failure

## Symptom

```
java.io.FileNotFoundException: class path resource [prompts/debate/bullish-researcher-system.txt]
cannot be opened because it does not exist

Caused by: java.io.FileNotFoundException: class path resource [prompts/analyst.txt]
cannot be resolved to absolute file path because it does not reside in the file system:
jar:nested:/.../fund-agent-core-0.0.1-SNAPSHOT.jar/!BOOT-INF/classes/!/prompts/analyst.txt
```

Error appears at `ClassPathResource.getInputStream()` or `ClassPathResource.getFile()`.

## Root Cause

Spring Boot repackages dependencies as nested JARs inside the fat JAR under `BOOT-INF/lib/`. Spring's `ClassPathResource` cannot resolve classpath resources inside these nested JARs — the `jar:nested:` protocol is not supported by the standard classloader.

This affects any code that tries to read resources via `new ClassPathResource(path).getFile()` or `.getInputStream()` from a dependency JAR that was packaged inside the main fat JAR.

## Fix Pattern

Add a filesystem fallback to the resource loader. The key pitfall is choosing the right base path:

### ❌ Wrong: `System.getProperty("user.home")`
```java
// BROKEN when project is symlinked (e.g., ~/project → /real/path/project)
private static final String FALLBACK_DIR =
    System.getProperty("user.home") + "/project-name/prompts/";
```
`user.home` returns the literal home directory (`/Users/username`). If `~/project-name` is a symlink to a different location, the concatenated path won't resolve.

### ✅ Correct: `System.getProperty("user.dir")`
```java
// Works because `cd ~/symlinked-project` resolves the actual path for user.dir
private static final String FALLBACK_DIR =
    System.getProperty("user.dir") + "/prompts/";
```
`user.dir` is set to the resolved (post-symlink) working directory of the JVM process. When the app is started with `cd ~/project && java -jar ...`, `user.dir` gets the actual filesystem path.

### Full PromptLoader Example
```java
@Component
public class PromptLoader {
    private static final String BASE_PATH = "prompts/";
    private static final String FALLBACK_DIR =
        System.getProperty("user.dir") + "/prompts/";

    public String load(String path) {
        return cache.get(path, this::readResource);
    }

    private String readResource(String path) {
        // 1. Try classpath first
        try {
            var resource = new ClassPathResource(BASE_PATH + path + ".txt");
            return resource.getContentAsString(StandardCharsets.UTF_8);
        } catch (IOException e) {
            log.debug("classpath load failed, trying filesystem: {}", path);
        }

        // 2. Fallback: filesystem using user.dir
        Path filePath = Paths.get(FALLBACK_DIR, path + ".txt");
        if (Files.exists(filePath)) {
            return Files.readString(filePath, StandardCharsets.UTF_8);
        }

        throw new RuntimeException("Prompt not found: " + path);
    }
}
```

## Verification

After fix, verify the compiled JAR has the fix:
```bash
# Extract the nested JAR from the fat JAR
jar xf app.jar BOOT-INF/lib/module.jar
jar xf BOOT-INF/lib/module.jar com/example/PromptLoader.class

# Check bytecode has user.dir
javap -c -p com/example/PromptLoader.class | grep "user.dir"
```

## Debugging Steps

1. Check if resource exists in the nested JAR: `jar tf BOOT-INF/lib/module.jar | grep prompts/`
2. Check if files exist on filesystem at the expected path
3. Verify `user.dir` at runtime: add `log.info("user.dir={}", System.getProperty("user.dir"))` at startup
4. Check for symlinks: `ls -la /path/to/project` — if it shows `->`, user.home path will fail
