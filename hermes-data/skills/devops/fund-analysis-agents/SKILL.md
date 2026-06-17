---
name: fund-analysis-agents
description: Deploy and operate the Fund Analysis Agents (hexliulab/fund-analysis-agents) multi-agent Chinese fund market AI analysis system. Covers installation, bug fixes, configuration, and usage.
version: 1.0
author: hermes
---

# Fund Analysis Agents — 部署与运维

基于多智能体协作的中国公募基金 AI 智能分析系统。Java 21 + Spring Boot 3.4 + Vue 3 + MySQL + Redis。

GitHub: https://github.com/hexliulab/fund-analysis-agents

## 环境要求

- Java 21 (`brew install openjdk@21`)
- Maven 3.9+ (`brew install maven`)
- Docker + Docker Compose（macOS 用 `brew install docker colima docker-compose`，然后 `colima start`）
- Node.js 18+

## 部署步骤

```bash
git clone https://github.com/hexliulab/fund-analysis-agents.git ~/fund-analysis-agents
cd ~/fund-analysis-agents
cp .env.example .env
# 编辑 .env，至少填 DEEPSEEK_API_KEY
bash scripts/setup.sh
```

默认账号：`admin` / `admin2026`  
访问地址：http://localhost:8080

## 已修复的 Bug

部署时会遇到以下问题，均已修复，详见 `references/bug-fixes.md`：

1. **Java 版本检测失败**：setup.sh 用 GNU grep 语法，macOS BSD grep 不兼容。修复：`grep -oE '"[0-9]+"'` → `awk -F'"' '{print $2}' | cut -d. -f1`
2. **前端构建失败**：路由引用 `views/logs/LogsView.vue` 但文件未提交。修复：创建占位组件
3. **管理员密码无法登录**：V2 迁移的 BCrypt hash 与 V4 不匹配。修复：用 Python bcrypt 生成新 hash 并 UPDATE
4. **Decryption failed**：API key 需通过 `/api/ai/providers` 接口提交（`enabled` 传 `1` 而非 `true`），系统自动 AES-256-ECB 加密存储（密钥：`FundAnalysis2026FundAnalysis2026`）
5. **Prompt not found**：Spring Boot 嵌套 JAR 中 `ClassPathResource` 无法加载 `fund-agent-core` 的 prompt 文件。修复：`PromptLoader.readResource()` 先用 `getContentAsString()` 尝试 classpath，失败后回退到文件系统绝对路径。**关键：必须用 `System.getProperty("user.dir") + "/prompts/"`，不能用 `user.home`！** 因为 `~/fund-analysis-agents` 是 symlink 指向 `~/.hermes/profiles/main/home/fund-analysis-agents`，`user.home` 返回 `/Users/omi` 不做 shell expansion，拼接后路径不存在。`user.dir` 才是 `cd ~/fund-analysis-agents && java -jar` 启动后解析过的真实路径

## 故障排查

### Redis 连接异常（运行时，非启动时）

**症状**：应用启动成功，运行一段时间后 `CacheRefreshService.evictSpringCache` 抛出 `org.springframework.data.redis.RedisSystemException` → `io.lettuce.core.RedisConnectionException: Unable to connect to localhost`。

**根因**：Spring Boot 与 Docker Redis 之间的 Lettuce 连接偶尔断连（长时间运行后 TCP 连接超时/被 Docker 网络回收）。**不是配置问题、不是 Docker 容器挂了。**

**验证**：
```bash
docker exec fund-redis redis-cli PING   # → PONG（容器健康）
docker ps --filter "name=fund-"          # → Up + healthy（都在跑）
```

**修复**（只重启应用，不要动 Docker 容器）：
```bash
lsof -ti:8080 | xargs kill -9
export JAVA_HOME="/usr/local/opt/openjdk@21"
export PATH="/usr/local/opt/openjdk@21/bin:$PATH"
cd ~/fund-analysis-agents && source .env
java -jar fund-application/target/fund-application-0.0.1-SNAPSHOT.jar &
```

重启后 6 个系统定时任务重新注册即可。**不需要** `docker restart fund-redis`，容器本身完全健康。

## 使用方法

### 浏览器 UI 工作流

1. 浏览器打开 http://localhost:8080，用 `admin` / `admin2026` 登录
2. 仪表盘 → 快速分析 → 输入基金代码 → 点击"开始分析"
3. 按钮会短暂 disabled（显示"提交中..."），恢复后分析在后台异步执行
4. 等待约 3-5 分钟（6 个分析师并行 → 3 轮辩论 → 交易员 → 风控 → 组合顾问 → 报告入库）
5. 刷新仪表盘 → "最近分析报告"表格出现新行 → 点击"查看"

### 监控分析进度

前端提交后无实时反馈。两种方式监控后台：

```bash
# 方式1：tail 应用日志（实时）
tail -f logs/app.log | grep -E "开始分析|辩论第|分析报告已保存"

# 方式2：grep 检查完成状态
grep "分析报告已保存.*<fund_code>\|分析执行失败.*<fund_code>" logs/app.log | tail -3
```

### 命令行提取关键结论

```bash
# 获取操作建议、仓位、置信度
grep "<batch_id>" logs/app.log | grep -oP '"(操作建议|建议仓位比例|置信度|风险评级)":\s*"[^"]*"' | head -10
```

### 完整流程

1. 登录 http://localhost:8080（`admin` / `admin2026`）
2. 管理后台 → AI 配置 → 填写 DeepSeek API Key
3. 自选基金 → 添加 ETF/基金代码
4. 仪表盘 → 快速分析 → 输入代码 → 开始分析
5. 等 3-5 分钟 → 刷新 → 查看分析报告

## 修改代码后重建

修改 `fund-agent-core` 源码后必须**先编译这个模块**，再打 fat JAR，否则嵌套依赖不会更新：

```bash
export JAVA_HOME="/usr/local/opt/openjdk@21"
export PATH="/usr/local/opt/openjdk@21/bin:$PATH"
cd ~/fund-analysis-agents
mvn clean package -pl fund-agent-core -am -DskipTests
mvn clean package -pl fund-application -am -DskipTests
```

仅改 UI（`fund-administration`）时可以跳过 agent-core 编译。

## 分析流程架构

6 个分析师并行 → 3 轮多空辩论 → 交易员 → 风控经理 → 组合顾问 → HTML 报告。平均耗时 3-5 分钟。日志输出在 `logs/app.log`，完整报告内容可通过 `grep "分析报告已保存"` 定位批次号。

## API 关键端点

- `POST /api/auth/login` — 登录获取 token
- `POST /api/watchlist/add` — 添加自选基金 `{"fundCode":"159326"}`
- `POST /api/analysis/trigger` — 触发分析 `{"fundCode":"159326"}`
- `POST /api/ai/providers` — 配置 AI provider
- `GET /api/analysis/reports` — 获取分析报告列表
