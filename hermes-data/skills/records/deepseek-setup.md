# DeepSeek V4 Pro 配置记录

**日期：** 2026-05-28
**添加方式：** 在微信中直接给出 API Key，通过终端写入 `.env` + `hermes config set`

## 配置内容

- **API Key（已脱敏）：** `DEEPSEEK_API_KEY=sk-2244e748...`
- **Model Provider：** `deepseek`
- **Default Model：** `deepseek-v4-pro`（后修正为 `deepseek-v4-pro`）

## 操作步骤

1. `echo "DEEPSEEK_API_KEY=sk-xxxx" >> ~/.hermes/profiles/main/.env`
2. `hermes config set model.provider deepseek`
3. `hermes config set model.default deepseek-v4-pro`
4. `/restart` 重启 gateway
5. 验证成功：通过 `/model deepseek` 切换后可正常对话

## 切换方式

- 微信中发送 `/model` 可查看当前模型
- `/model deepseek` 切换到 DeepSeek
- `/model minimax-cn` 切换回 MiniMax

## 注意事项

- DeepSeek 国内节点响应正常，未遇到网络阻塞
- 刚切换时首次请求可能稍慢（模型加载），后续响应正常
