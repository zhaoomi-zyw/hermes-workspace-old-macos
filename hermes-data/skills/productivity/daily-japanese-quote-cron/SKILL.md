---
name: daily-japanese-quote-cron
description: 管理每天8:30发送日语实用生活短语到Home频道的cron job，包括发送格式、tracker文件位置
---

# 日语每日实用短语 Cron Job 管理

## 概述
管理每天 8:30 发送一条实用生活日语短语到 Home 频道的 cron job。
**内容类型已从"励志语录"改为"实用生活短语"**（出行、吃饭、购物、问候、道歉等日常场景）。

## 核心发现

### Cron Auto-Delivery 机制
- Cron job 配置了 `deliver: origin`，最终 response 内容自动送达 Home 频道
- **不要使用 `send_message`** 发送内容——会报错或被跳过
- **直接把内容放在最终 response 中**，系统自动处理投递

### Tracker 文件位置
- 路径：`/Users/omi/.hermes/profiles/main/home/quotes/tracker.json`（NOT `~/quotes/tracker.json` — `~` expansion differs）
- 格式：
```json
{
  "last_date": "2026-05-06",
  "last_index": 1,
  "total": 30
}
```

### 短语库文件位置
- 路径：`/Users/omi/.hermes/profiles/main/home/quotes/phrases.json`
- 格式：JSON 数组，每个元素包含 `jp`/`reading`/`cn`/`example_jp`/`example_cn`/`scene`
- **不要从 session JSON 中提取短语** — session 文件中的短语数组有复杂的转义字符（`\\\` in raw file → `\` in JSON string），难以可靠解析
- 直接读写 `phrases.json` 文件

## 发送格式（严格按此）
```
★原句：
（日语原文）

★读音：
（假名注音）

★中文：
（中文意思）

★例句：
（生活场景例句，中日双语）

★使用场景：
（什么时候用）
```

### 内容要求（2026年5月更新）
### 短语库文件位置
- 路径：`/Users/omi/.hermes/profiles/main/home/quotes/phrases.json`
- 格式：JSON 数组，每个元素包含 `jp`/`reading`/`cn`/`example_jp`/`example_cn`/`scene`
- **不要从 session JSON 中提取短语** — session 文件中的短语数组有复杂的转义字符（`\\\` in raw file → `\` in JSON string），难以可靠解析
- 直接读写 `phrases.json` 文件

## 发送流程
1. 读取 `~/quotes/phrases.json` 加载短语库
2. 读取 `~/quotes/tracker.json` 获取当前 index
3. 判断是否同日：同日则用相同 index，新日期则 index + 1
4. 取对应短语（0-based index）
5. 更新 tracker（last_date + last_index）
6. **将内容作为 final response 输出**（自动投递）

### 索引推进逻辑
```python
if last_date == today:
    current_index = last_index
else:
    current_index = (last_index + 1) % len(quotes)
```

## 学習リソース (Study Resources)

- `references/japanese-grammar-qa.md` — Grammar points (ら抜き言葉 etc.), vocabulary (麻辣烫 etc.), and study notes from tutoring sessions
- `/Users/omi/.hermes/profiles/main/home/workspace/japanese-dining-shopping-qa.md` — Full 25-scenario dining & shopping Q&A

## 関連 Cron Job ID
- 当前 job: `7b72bb66b9a2`（每天 8:30，deliver: origin）
- 注意：系统里可能还有旧格式的重复 job（`6e134680c3c9`、`4220baf564f1`），已清理

## 注意事项
- 不要对 "home" 平台使用 send_message
- 内容直接放在 final response
- tracker 更新必须先读后写，避免并发覆盖
- 内容类型变了：从励志语录 → 实用生活短语
