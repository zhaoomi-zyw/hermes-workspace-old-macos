# Codex CLI — Platform Install Paths

## Windows

npm global install (`npm install -g @openai/codex`):

| 内容 | 路径 |
|------|------|
| 包文件根目录 | `%APPDATA%\npm\node_modules\@openai\codex` |
| 可执行入口 | `%APPDATA%\npm\codex.cmd` / `codex.ps1` |
| 实际展开 | `C:\Users\<用户名>\AppData\Roaming\npm\...` |

安装后 `%APPDATA%\npm` 通常在系统 PATH 中，所以终端直接敲 `codex` 即可。

## macOS / Linux

npm global install:
- 使用 nvm: `~/.nvm/versions/node/<version>/lib/node_modules/@openai/codex`
- 使用 Homebrew node: `/usr/local/lib/node_modules/@openai/codex`
- 使用系统 node: `/usr/lib/node_modules/@openai/codex`

确认位置: `which codex` 或 `npm list -g @openai/codex`
