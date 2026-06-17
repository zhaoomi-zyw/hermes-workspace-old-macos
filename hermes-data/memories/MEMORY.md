全球动保五强2025财报+驱虫Q1 2026：硕腾94.67亿(+2%),默沙东63.54亿,勃林格56.84亿,礼蓝47.15亿,爱德士43.04亿(+10.4%)。BI中国驱虫对手：硕腾汪宠爱+海正海乐妙。详见 competitive-intelligence skill。
§
DeepSeek V4 Pro 已配置（2026-05-28）：provider=deepseek，模型=deepseek-v4-pro。与 MiniMax-CN 并存，微信内 /model 切换。配置文档：deepseek-setup.md
§
家庭网络拓扑：中国移动ONT→TP-Link TL-XDR3050(LAN侧, WiFi绑定)→iStoreOS软路由。iStoreOS跑OpenClash透明代理；Alist 已安装，夸克网盘 + WebDAV 已挂载。
§
AnySearch：batch_search 最多 5 次/调用，extract 无法处理 PDF；财报用官方新闻稿 > 业绩会记录 > 新闻摘要；私企不发布季报。已 symlink 集成到 pet-competitor。周报 cron skills 含 anysearch，~30s vs 浏览器 685s。cronjob list 只看当前 profile scheduler，跨 profile 任务需读 jobs.json。
§
GitHub Personal Access Token 已配置 — 用于 zhaoomi-zyw 仓库 API 操作。
§
DeepSeek 账号邮箱已配置，API key 在 main profile .env。余额查询: curl https://api.deepseek.com/user/balance。
§
DeepSeek v4 系列（pro 和 flash）都有推理 token 开销（reasoning_tokens），会占用 max_tokens 配额。OCR 等校正任务需要 max_tokens ≥ 4000，否则推理 token 吃完全部预算，正文输出为空（finish_reason=length, content=''）。简单校对任务用 v4-flash 即可，pro 无优势且更慢。
§
Omi prefers MiniMax vision (mmx vision describe) for image OCR tasks as the default. Tesseract + DeepSeek v4-flash pipeline was tried but abandoned due to DeepSeek v4-flash reasoning tokens consuming the entire max_tokens budget and producing empty output on complex/garbled OCR text. Use read-image skill's mmx approach.
§
Omi 活跃投资A股，自选股集中在通信/光通信/电网设备板块：亨通光电(600487)、中天科技(600522)、锐捷网络(301165)、菲菱科思(301191)。关注相关ETF（159326电网设备ETF、515880通信设备ETF、515050 5GETF、159363/159381 AI ETF等）。分析偏好：会排除机构大幅撤离的个股（如菲菱科思基金从87家降至4家）。也在为小白用户评估GitHub开源AI投资工具。
§
Omi 的 macOS 开发环境：Java 21 通过 Homebrew 安装，Maven 通过 Homebrew，Docker 使用 colima 而非 Docker Desktop，Node.js v24。部署 Java 项目时需要显式 export JAVA_HOME 和 PATH。MySQL/Redis 通过 Docker Compose 管理。
§
Omi 自选组合（2026-06-04）—— 9只ETF+4只个股，覆盖AI/Token全产业链：机器人(562500,159530)、信息安全(159613,562920)、软件(159590,159068)、大数据(516700)、通信(515880)、电网(159326)、光缆(亨通光电/中天科技)、网络设备(锐捷/菲菱科思)。精简建议：保留562500+159590+159326+515880+159613，删除重叠和迷你基。
§
hermes-webui (nesquena/hermes-webui) 通过 launchd 管理，监听 8787 端口。开机自启+崩溃自动重启（KeepAlive）。git post-merge hook 实现 git pull 后自动 kickstart 重启。注意：Hermes 内置 dashboard（hermes dashboard）和 API Server（端口 8642）与此 webui 是不同的东西。ctl.sh 用于管理，但日常用 launchctl。
§
血常规异常阈值（用于化验单照片检查）：WBC<2.5×10⁹/L、NEUT<1.5×10⁹/L、Hb<90g/L、PLT<75×10⁹/L。任一项低于阈值即判异常。发照片后逐项对照输出。
§
BI 文档/报告视觉风格偏好（PET 项目采用的绿色系）：深绿底 #08312A、霓虹绿强调 #00E47C、浅绿辅助 #b8f5d4、暖白底色 #FAF9F8。替代旧的海军蓝 (#003b5c) + 橄榄绿 (#70ad47) 风格。参考文件位于 pet-competitor profile 输出目录。
§
Omi 对双语需求文档的翻译质量有明确要求：每条需求的"中文解读"必须是对该条英文原文的具体翻译/解释，不能使用模板占位符。每条翻译需体现该条需求的具体技术含义和用途。发现模板化翻译时应主动指出并修正。
§
Hermes WebUI HTML preview 按文件路径缓存。修改后的 HTML 如果 preview 显示旧版，用新文件名保存（如加 v2/v3 后缀）即可绕过缓存。
§
Copilot disambiguation: Omi 说的 "Copilot" 指 Microsoft 365 Copilot（网页版 m365copilot.microsoft.com），不是 GitHub Copilot。用于公司（BI）账号下的 agent 创建和知识库管理。
§
macOS 网络流量诊断三层法：1) host 进程级 nettop；2) Colima VM 接口级；3) 容器级 docker stats。三层递进定位流量来源。
§
macOS 26 Sequoia TCC 保护阻止 defaults write 写入辅助功能设置。替代方案：用 AppleScript 通过 System Events GUI 脚本操作。键盘快捷键自定义通过 ~/Library/Preferences/com.apple.symbolichotkeys.plist 的 AppleSymbolicHotKeys 字典。
§
sakura 和 glp1-research 两个 profile 的 gateway 已永久卸载，重启后不再自启。当前仅保留 main 和 pet-competitor 的 gateway。
§
Omi 基金组合（2026-06-15最终版）：现金池35万全开放申赎无锁定。20万 020080 华富恒稳纯债D（2.88%）+ 15万 019872 长城短债D（2.49%）。日定投（交易日）：005698 华夏全球科技先锋QDII A 150元（已投1,150，限额2,500/日）+ 022979 华夏中证A500ETF联接A 150元（已投650，开放申购）。偏好：不接受滚动持有，只接受开放申赎/7天持有/30天持有期。Cron：月末月报(月末交易日20:30,微信)、定投限额监控(每日9/21点,微信,静默不变)、定投周报(周五22:00,微信)。已移除：纳指限额监控。
§
For BI NAC enforcement work: prefer simple Site + IP Range/VLAN summaries: current NAC mode, connected switches, switch/port type, reason/evidence, enforcement required?, and owner/action; avoid port-level detail unless needed.
§
BI NAC/IT4OT hostname判断规则：除非交换机 hostname 中明确包含 NWOTHON、NWOTABB 等特殊 DCS/Honeywell/ABB 标识，否则按标准 OT configuration 判断；不要仅因端口是 trunk 就推断为 Honeywell FTE/ABB exception。
§
NAC switch raw configs stored in workspace/NAC_switch_configs/{SITE}/. BIB_G144 site has 13 IE switches. Each site folder gets a raw config file + assessment summary .md.