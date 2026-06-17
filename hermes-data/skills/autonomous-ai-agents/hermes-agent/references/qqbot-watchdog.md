# QQBot 掉线问题：诊断与自动恢复

## 问题现象

Pet-competitor 和 Sakura 两个 profile 的 QQ 机器人每天都会不在线，需要通过 main profile 手动重启。

## 根本原因

QQ 平台的 WebSocket 连接**每 60 秒主动断开一次**（QQ 服务器端心跳策略）。Hermes qqbot adapter 会在断开后尝试重连：

```
WebSocket closed → Reconnecting in 2s → WebSocket connected → Session resumed
```

这个循环在短期内正常，但**最终会卡住**——adapter 不再重连，而 `gateway_state.json` 的状态仍显示 `connected`，QQBot 进程也还在。

**诊断特征**：
- `gateway_state.json` 显示 `qqbot.state: "connected"` 但 `qqbot.updated_at` 时间停止更新
- `gateway.log` 最后一条日志停在某个时间点，之后无新日志
- 进程 `ps aux` 显示 running，但实际不工作

## 检测方法

每 5-15 分钟检查 `gateway_state.json` 的 `qqbot.updated_at` 时间戳：

```bash
# 获取 qqbot 最后活动时间戳
python3 -c "
import json
from datetime import datetime
with open('/Users/omi/.hermes/profiles/<profile>/gateway_state.json') as f:
    d = json.load(f)
qqbot = d['platforms']['qqbot']
updated = qqbot['updated_at']
print(f\"qqbot.last_update: {updated}\")
dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
age_minutes = (datetime.now().astimezone() - dt).total_seconds() / 60
print(f\"age: {age_minutes:.1f} minutes\")
"
```

如果 `age_minutes > 10` 且持续增长，说明 adapter 已卡住。

## 自动恢复方案

### Watchdog 脚本

位置：`~/.hermes/scripts/watchdog_qqbot.sh`

核心逻辑：
1. 读取 `gateway_state.json` 的 PID（比 `gateway.pid` 文件可靠）
2. 检查进程是否存活
3. 检查 `qqbot.updated_at` 是否超过 10 分钟
4. 超过阈值则 `kill` 旧进程 + 重启 gateway

### Cron Job

```
hermes cron create "*/15 * * * *" --name qqbot-watchdog --script watchdog_qqbot.sh --no-agent
```

Job ID: `287f6e53c900`

## 为什么 `gateway.pid` 不可靠

`gateway.pid` 文件只在 gateway **首次启动时**写入一次。如果 gateway 重启（哪怕是正常重启），PID 变化后 `gateway.pid` 不会更新。而 `gateway_state.json` 的 `pid` 字段会随着每次启动更新，所以应该从 `gateway_state.json` 读取当前 PID。

## 已知行为

- QQ WebSocket 断开是**正常的服务器端行为**，不是 Hermes 的错
- Hermes 的重连机制短期内有效，最终会卡住
- 状态显示 `connected` 不代表真正在线——必须看 `updated_at` 是否持续更新
- Sakur profile 的 qqbot 比 pet-competitor 更频繁地出现此问题

## 相关文件

- Watchdog 脚本：`~/.hermes/scripts/watchdog_qqbot.sh`
- Cron Job：ID `287f6e53c900`（qqbot-watchdog）
- Profile 状态：`~/.hermes/profiles/<profile>/gateway_state.json`
