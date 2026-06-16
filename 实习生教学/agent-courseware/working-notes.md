# AI Agent / Hermes 高中生介绍课件工作记录

## 项目目标

为一名高中实习生设计一套关于 AI Agent 的入门介绍材料，让他理解：

- 传统 ChatGPT/chatbot 与 AI Agent 的区别
- Hermes 这类 Agent 的优势与未来趋势
- Agent 能结合电脑、文件、网页、代码、自动化、记忆、定时任务等能力完成真实任务
- 最终输出一个或多个 HTML 课件/介绍页面

## 目标受众

- 高中学生
- 背景：德国人，在德国读高中，来中国短暂实习
- 对抽象技术概念不一定熟悉
- 需要通过感兴趣的场景建立直观认知
- 重点不是讲复杂架构，而是让他感受到“AI 从聊天变成做事”
- 课件需要考虑跨文化表达：案例可以结合德国高中生可能感兴趣的学习、足球/电竞、旅行、中国体验、未来专业选择等场景
- 工作沟通语言：Omi 与助手讨论课件内容时可以使用中文
- 最终交付语言：HTML 课件、页面文案、课程大纲和对学生展示的内容使用英文

## 已确定的讲解主线

核心类比：

- ChatGPT 像一个会聊天的学霸
- Agent 像一个会使用电脑、会查资料、会写文件、会运行代码、会长期记住你并主动做事的数字同学/助理

核心一句话：

> ChatGPT 是会说话的大脑；Agent 是会使用电脑和工具的大脑。

或：

> 以前 AI 是“你问我答”；现在 AI 是“你给目标，它自己想办法完成”。

## 已讨论的高中生感兴趣场景

1. AI 学习教练
   - 总结错题
   - 分类知识点
   - 制定复习计划
   - 每周生成学习周报
   - 记住薄弱点

2. 游戏/电竞/体育数据分析助手
   - 查询比赛数据
   - 分析选手或队伍表现
   - 生成战术复盘
   - 自动追踪比赛信息

3. 个人网站 / 小游戏制作助手
   - 创建 HTML/CSS/JS 文件
   - 运行和检查网页
   - 根据反馈修改
   - 适合现场 demo

4. AI 研究助理
   - 研究 AI、专业选择、未来职业、推荐算法等话题
   - 搜索资料
   - 提炼重点
   - 生成适合高中生理解的解释

5. 个人自动化秘书
   - 每天提醒学习
   - 每晚总结
   - 每周复盘
   - 自动推送单词、练习题、新闻或比赛信息

6. AI 编程陪练
   - 解释报错
   - 修改代码
   - 运行代码
   - 生成练习项目

## 建议现场教学流程

总时长：2 小时。

课程形式建议从“快速演示”升级为完整 workshop：先建立概念，再做 Hermes 演示，随后让学生亲自参与完成一个小作品，最后讨论未来趋势和个人学习路径。

初步结构：

1. 10 分钟：破冰与兴趣确认
   - 了解学生兴趣：学习、AI、编程、足球/电竞、旅行、中国实习体验、未来专业
   - 用生活化问题引出：如果有一个会用电脑的 AI 助手，你想让它帮你做什么？

2. 20 分钟：概念讲解
   - Chatbot 只能聊天
   - Agent 可以使用工具完成任务
   - 讲清楚 memory、tools、files、browser、automation、coding 的直观含义

3. 25 分钟：Hermes 现场演示 1 —— 从想法到作品
   - 推荐 demo：My China Internship Diary / personal mini website / simple browser game
   - 展示 Agent 创建文件、写代码、修改页面、检查结果

4. 20 分钟：Hermes 现场演示 2 —— 学习/研究助理
   - 让 Agent 解释一个高中生关心的话题
   - 如 AI career, study plan, China internship notes, football/esports analysis
   - 展示 Agent 如何搜索、总结、结构化输出

5. 25 分钟：学生动手环节
   - 学生选择一个 mini challenge
   - 例如 personal website、quiz game、AI study coach prompt、China survival assistant
   - Omi 用 Hermes 带着他完成第一版

6. 10 分钟：Agent 未来趋势
   - 从“asking AI questions”到“delegating tasks to AI”
   - AI literacy = learning how to direct agents
   - 讨论未来职业和学习建议

7. 10 分钟：安装/后续学习路径
   - 第一次用 Omi 这台电脑上的 WebUI
   - 如果有兴趣，后续安装 VS Code + Hermes CLI
   - 暂不一开始讲 gateway、profiles、MCP 等高级配置

## 安装/体验建议

第一次教学建议：

- 直接使用 Omi 这台电脑上已经配置好的 Hermes WebUI
- 不要一开始让学生自己安装完整 Hermes + Gateway + Profile + Cron
- 先让他完成一个小作品，建立兴趣

后续如果学生想继续学：

1. 安装 VS Code
2. 安装 Hermes CLI
3. 使用 `hermes` 开始
4. 之后再逐步学习 skills、cron、memory、GitHub、网页部署等

## 课件形式初步设想

可能输出：

1. 一个主 HTML 课件：AI Agent 入门介绍
2. 一个互动 demo HTML：Chatbot vs Agent 对比
3. 一个实操任务卡 HTML：给学生的 3 个小挑战
4. 一个安装指南 HTML：高中生最小可行安装路径

## 后续新增聊天内容

- 已确认：目前不了解该德国高中生的具体兴趣，因此课程开头需要设置 interest-discovery / icebreaker 环节。
- 课件和 demo 需要保持可切换：根据学生现场回答，在个人网站/小游戏/学习教练/中国实习助手/足球或电竞分析/职业探索之间选择主 demo。
- 已确认：课程整体风格为平衡型。前段启发兴趣与解释趋势，中段让学生亲手体验/完成小作品，最后连接到未来学习、大学专业和职业选择。
- 已确认：学生最终带走两个成果：一个课堂中生成的 HTML 小作品，以及一套可复用的 AI Agent prompt 模板。模板方向包括学习教练、研究助手、职业探索、中国实习日记助手、编程陪练等。
- 已确认：最终课件形式选择“多个 HTML 文件”，不是单一 slide deck。建议拆成主课程页、Chatbot vs Agent 对比页、现场 demo 指南页、prompt 模板 handout、课后安装/继续学习指南。
- 已确认：HTML 视觉风格选择“专业科技但不幼稚”。整体应现代、干净、可信；默认浅色背景保证阅读，局部可使用深色科技模块形成对比；避免过度渐变、炫技动效、儿童化配色和泛泛的 AI 营销视觉。适合德国高中生在中国短期实习的语境。
- 已确认：Hermes 介绍采用分层深度。课堂主线中等介绍：Hermes 是能使用工具、文件、浏览器、代码、记忆和自动化的 AI agent framework；不在主课程深入配置细节。另设 “If you want to go deeper” 页面，高层介绍 CLI、WebUI、Gateway、Skills、Memory、Cron、Profiles、MCP 和 integrations。
- 已确认：课堂现场学生参与程度为“共同操作”。学生需要亲自复制粘贴并运行几条预先准备好的 prompt；Omi 负责引导、解释和兜底。所有关键 prompt 需要提前写好，确保复制粘贴后能产生相对可预期的预设效果，避免现场临时发挥导致失控。
- 已确认：现场主 demo 采用“多路线准备，默认首选 My China Internship Diary”。如果学生没有明确兴趣，就做一个英文 HTML 页面记录他的中国实习体验；如果偏编程/游戏，切到 simple browser game；如果关注未来学习/职业，切到 AI Learning Portfolio；如果关注学校学习，切到 AI Study Coach prompt/workflow。
- 已确认：课堂会准备两台 MacBook。一台是 Omi 当前这台，已经装好 Hermes 并完成所有配置，用作主 demo 机器；另一台是只装了 macOS 的初始环境。第二台不只是理论展示，需要根据最终确定的学生友好方案一步步安装并演示。
- 已确认：需要单独做一页 HTML 主题“Ways to Use Hermes / Which Way Should You Start With?”，比较 WebUI、CLI、Messaging/Gateway、Cron/Automation、Profiles/Advanced integrations 等使用方式，并推荐学生采用方案 4：WebUI-first，最后快速展示 CLI 作为进阶玩法。WebUI 路线使用 Omi 当前的第三方 `nesquena/hermes-webui` 插件/实现，不使用 Hermes 官网/内置 dashboard/plugin 路线。
- 已确认：安装指南需要具体安装命令和截图。截图在最终安装路线确定并实际验证后制作。
- 已确认：prompt 模板数量不先固定，取决于课程各环节时长；每条 prompt 必须对应课堂中的具体操作点，复制粘贴即可产生预设效果。
- 已确认：需要提前准备 fallback HTML 成品，防止现场生成失败、速度慢或效果不佳。fallback 至少覆盖默认路线 `My China Internship Diary`。
- 已确认：最终 HTML 文件需要打包成一个完整目录，方便拷贝给学生。目录包含课程页、prompt 模板、安装指南、fallback demo artifact、必要本地资源，以及给 Omi 使用的 `instructor-runbook.html` 课堂操作脚本。
- 已确认：最终学生课件需要中英德三语对照。英文和德语作为主要显示语言；中文可以小一点，作为辅助说明或讲师备注。
- 视觉设计技能记录：目前已使用本地 `claude-design`、`educational-workshop-courseware` 和 `design-html` 三个 skill。`design-html` 因 GitHub API rate limit 无法通过 `hermes skills install` 安装，已从 raw GitHub URL 手动下载到 `/Users/omi/.hermes/profiles/main/skills/creative/design-html/SKILL.md`，并经 `hermes skills list` / `skill_view` 验证可用。后续生成 HTML 时，用 `claude-design` 控制整体视觉过程，用 `design-html` 做 HTML/CSS 可用性和视觉最终打磨。

后续对话中与本课件相关的需求、素材、结构、风格、标题、demo 点子、安装步骤等都继续追加到本文件。
