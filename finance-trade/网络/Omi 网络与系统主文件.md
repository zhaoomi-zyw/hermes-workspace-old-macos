---
tags: [network, system, macos, openclash, docker, hermes]
aliases: [网络系统, 网络与系统]
updated: 2026-09-01
---

# 网络与系统主文件

> 最后更新：2026-09-01
> 用途：承载网络拓扑、系统配置、排障方法的详细内容，MEMORY.md 只留精简指针。

## 一、网络拓扑
中国移动ONT → TP-Link TL-XDR3050(192.168.1.1/3Mcn7077，Hermes MAC绑定192.168.1.109) → iStoreOS(WAN 192.168.1.7, LAN 192.168.100.1, root/password) → OpenClash透明代理
- Alist：192.168.100.1:5244, admin/123456，启动 `/usr/bin/alist server --data /etc/alist`，夸克挂载/夸克网盘，WebDAV /dav/夸克网盘
- TP-Link TL-XDR3050 管理密码：3Mcn7077。注意：TP-Link 的 Canvas 界面无法浏览器自动化操作，静态路由等需手动

## 二、macOS 开发环境
- Java 21（Homebrew /usr/local/opt/openjdk@21），Maven（Homebrew），Colima 替代 Docker Desktop，Node.js v24
- Java 项目需 export JAVA_HOME 和 PATH。MySQL/Redis 用 Docker Compose
- Docker Hub mirror for China：colima config 在 ~/.colima/default/colima.yaml，docker: 段加 registry-mirrors: [https://docker.m.daocloud.io, https://dockerproxy.com]，然后 colima restart。docker pull/compose 在中国无VPN时 EOF 用此法

## 三、OpenClash 规则管理（重要）
- custom_rules.list 有时不生效。可靠做法是改 dog2.yaml 的 rules 段
- **勿在 ssh+sed 里用 \x27 表示单引号**——双层嵌套不解析转义，会写入字面 x27 损坏配置，且重启后 OpenClash 崩溃恢复会把 enable 归 0
- **正确流程**：下载配置到本地 → Python 替换 → scp 上传 → uci set openclash.config.enable=1; uci commit; /etc/init.d/openclash start
- 规则列表(python-list格式)一律用此法，勿 sed
- 详见 openclash-diagnosis skill（需 curator adopt 后才可改）

## 四、OpenClash SSRDOG 排障
- SSRDOG 节点全挂/订阅刷新后 GLOBAL 可能卡 DIRECT（store-selected:true）
- 流程：1) 重启 /etc/init.d/openclash restart；2) GLOBAL 回退 DIRECT 则 curl -X PUT http://127.0.0.1:9090/proxies/GLOBAL -d '{"name":"🔰 代理"}'；3) 仍不行找 Omi 要新订阅
- SSRDOG 后端 zhgfomdkck.hss16lexbb.sbs:601（62节点单后端=单点故障），重启通常恢复

## 五、Hermes WebUI（/Users/omi/hermes-webui/）
- launchd 管理：~/Library/LaunchAgents/com.parantoux.hermes-webui.plist，监听 0.0.0.0:8787，开机自启+崩溃重启(KeepAlive)
- 局域网访问 http://<MacIP>:8787
- 排障：8787 无法访问 → 先 launchctl list | grep webui 确认服务已加载；未加载则 launchctl load ~/Library/LaunchAgents/com.parantoux.hermes-webui.plist（load 即完整修复，2026-08-26验证）
- 启动瞬间可能报 errno49 Can't assign requested address（网络未就绪），重启服务即可
- 注意与 Hermes 内置 dashboard/API Server(8642) 不同

## 六、macOS 排障经验
- **流量诊断三层法**：1) nettop -x -P -m tcp -J bytes_out,bytes_in -n -l 1；2) Colima VM: ssh -o ControlPath=~/.colima/_lima/colima/ssh.sock lima "cat /proc/net/dev"；3) docker stats --no-stream
- macOS 26 Sequoia TCC 保护阻止 `defaults write com.apple.universalaccess` 写入辅助功能设置。替代：AppleScript 通过 System Events GUI 脚本操作。详见 skill macos-optimization
- 键盘快捷键自定义通过 ~/Library/Preferences/com.apple.symbolichotkeys.plist 的 AppleSymbolicHotKeys 字典（第4.5节）

## 七、Hermes 会话绑定（微信⇄WebUI）
- gateway/session_binding.py 读 session_bindings.json（weixin chat_id→shared_session_id），api_server.py run.completed 钩子把 WebUI/API 触发回复投递回绑定微信（API Server supports_async_delivery=False，需手动桥接）
- 微信DM chat_id=o9cq80_QqkAnltK8A4P60TrUwZGk@im.wechat
- 备份 ~/.hermes/backups/session-bind-20260826-*
- 详案待 curator adopt hermes-profile-gateway-troubleshooting 后写入其 references/wechat-webui-session-sync.md

## 八、Profile / Gateway
- sakura 和 glp1-research 两个 profile 的 gateway 已永久卸载（hermes gateway uninstall），重启后不再自启。当前仅保留 main 和 pet-competitor 的 gateway
- Hermes WebUI HTML preview 按文件路径缓存。修改后 HTML 若 preview 显示旧版，用新文件名（加 v2/v3）绕过缓存


## 九、OpenClash「规则缺失」导致个别站点不通（2026-09-26 实证）

**症状**：X / Twitter 上不去，但 Google / YouTube / Telegram 一切正常（含手机）。

**根因**
```
dog2.yaml 的 rules 段【没有】x.com / twitter.com / twimg.com / t.co 规则
        ↓
落到末尾兜底  MATCH → "🐟 Others"
        ↓
"🐟 Others" 当时的手动选择 = "🎯 直连"
        ↓
流量裸奔出国 → 撞墙（超时 15s 或立即 000）
```

**排查路径（每步都是排他性判据）**
| 步骤 | 结果 | 排除了什么 |
|---|---|---|
| 1. 本机测 X vs Google | X=000, Google=200 | 「只有手机不行」|
| 2. 换 6 个地区节点测 X | 全 000 | 单节点被封 |
| 3. `--socks5-hostname`（代理解析 DNS）| 仍 000 | 本地 DNS 污染 |
| 4. `--resolve` 指定 104.244.x.x 真实 IP | 仍 000 | DNS 这一层 |
| 5. **切 global 模式** | **X=200 ✅** | **⇒ 锁定为分流规则问题** |
| 6. 读 rules 搜 x.com | **无任何匹配** | 确认规则缺失 |
| 7. 查 `🐟 Others` 的 now | **= 🎯 直连** | 闭环 |

**⭐ 决定性技巧：Clash 全 局模式(global) 是「规则问题 vs 节点问题」的分野点。**
global 通、rule 不通 ⇒ 一定是分流规则，不要再折腾节点和 DNS。

**修复（运行时 API，无需重启、可逆）**
```bash
# 查看
curl -s http://192.168.100.1:9090/proxies/ -G --data-urlencode 'name=🐟 Others'   # 或直接 GET /proxies
# 修改兜底组指向
curl -X PUT 'http://192.168.100.1:9090/proxies/%F0%9F%90%9F%20Others' \
     -H 'Content-Type: application/json' -d '{"name":"🇭🇰 Hong Kong丨01"}'
```
`profile.store-selected: true` ⇒ 该选择会被持久化，OpenClash 重启不丢。

**顺带发现（同样缺规则，靠同一次修复恢复）**：discord.com、reddit.com、wikipedia.org、amazon.com
**已有规则**：google / youtube / instagram / facebook / openai / chatgpt / anthropic / telegram / t.me

**两种兜底写法的区别**
| 写法 | 换 `🔰 代理` 节点时 | HK01 挂了 |
|---|---|---|
| 指向 `🔰 代理` 组 | 跟着变 | 自动切换 |
| 固定 `🇭🇰 Hong Kong丨01` | 不受影响 | ⚠️ 一起挂 |

**⚠️ 教训：该配置的 rules 是纯手写 DOMAIN-SUFFIX 清单，无 GEOSITE / RULE-SET 兜底** ——
漏一个域名 = 漏一整类服务，且默认静默走兜底组，**不会报错**。新增站点时记得同步补规则。
