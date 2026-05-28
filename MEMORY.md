# MEMORY.md

## 当前进行中项目
- **勃林格宠物药竞品生态报告** — [已完成] — 2026-05-28
  - 已完成：产品线对比、超可信vs大宠爱深度分析、竞争格局、舆情策略、数字化机会
  - 已完成：四家动保2026Q1营收对比 + 竞品威胁矩阵
  - 已完成：HTML报告（含BI产品线、硕腾/礼蓝/海正/默沙东竞品分析、核心洞察）
  - 已完成状态更新：礼蓝Credelio Quattro未入华+Zenrelia非驱虫药，硕腾汪宠爱®是主要威胁
  - 报告路径：`generate file/pet2026/index.html`



## User Preferences

- **Browser**: Always use local Google Chrome (`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`) for web browsing, NOT the bundled Chromium. Close agent-browser first, then use `--executable-path` flag.

## 工作准则
- **搜索信息必须严谨**：不确定的内容注明"不确定"，不臆测；关键产品归属（如福来恩归勃林格、爱沃克归礼蓝/拜耳）须核实后书写

## Identity
- **Name**: pet-competitor
- **Role**: 市场分析专家 🔍📊
- **Theme**: Knowledge synthesis and structured reporting
- **Vibe**: 高效、客观、条理清晰
- **Avatar**: avatars/research.png
- **Capabilities**: Web搜索（Chrome）、社媒内容获取（微信/小红书/抖音）、数据分析与报告生成
- **Example Prompts**: 搜索最新AI趋势并整理、分析数据总结结论

## System

- Mac: omi的MacBook Pro, Darwin 25.4.0
- OpenClaw workspace: `/Users/omi/.openclaw/workspace-pet-macos`
- Chrome: v136 installed at `/Applications/Google Chrome.app`
- Tavily API key: configured in `~/.openclaw/.env`
- openclaw-tavily-search skill installed (via cn mirror)
- **GitHub 仓库**：https://github.com/zhaoomi-zyw/openclaw-workspace-pet-macos（Private）
- **GitHub 同步**：每次 commit 后必须 `git push`，确保本地与 GitHub 同步
- **生成文件存放规则**：所有新生成的 html/pdf/png 文件必须放在 `generate file/` 文件夹中，然后再 commit + push（不要放在根目录）

## 市场研究成果

### 勃林格殷格翰中国宠物药产品线（2025年）

**外驱/内外同驱：**
- 超可信（NexGard Spectra）：阿福拉纳米尔贝肟咀嚼片，内外同驱，每12周一次
- 尼可信（NexGard）：阿福拉纳咀嚼片，外驱，每月一次；2025年新获批治疗犬螨虫适应证
- 福味恩（FrontPro）：阿福拉纳咀嚼片，外驱，每月一次，2025年亚宠展新上市
- 福来恩（Frontline）：非泼罗尼滴剂，外驱，每月一次
- 博来恩（Broadline）：复方非泼罗尼吡喹酮滴剂，内外同驱（猫用）

**内驱：**
- 犬心保（Heartgard Plus）：伊维菌素双羟萘酸噻嘧啶，预防心丝虫+治疗蛔虫，每月一次

**心脏/治疗：**
- 勃欣定（Vetmedin）：匹莫苯丹，犬充血性心力衰竭

### 勃林格产品 — 中国市场最大竞争对手

| 勃林格产品 | 最大竞争对手 | 竞争对手公司 |
|-----------|------------|------------|
| 超可信（NexGard Spectra） | 大宠爱（Revolution）/ **汪宠爱®（Simparica Trio）** | 硕腾 Zoetis |
| 博来恩（Broadline） | 妙宠爱（Revolution Plus） | 硕腾 Zoetis |
| 福味恩（NexGard） | 欣宠克（Simparica） | 硕腾 Zoetis |
| 尼可信（NexGard） | 欣宠克（Simparica） | 硕腾 Zoetis |
| 福来恩（Frontline） | 拜宠爽（Advantix） | 礼蓝 Elanco |
| 犬心保（Heartgard Plus） | 海乐妙（Milbemax） | 海正动保 |
| 勃欣定（Vetmedin） | 活心宁（Cardalis） | 礼蓝 Elanco |

**竞争格局总结：**
- 硕腾（Zoetis）是勃林格在中国宠药市场最大竞争对手，覆盖外驱/内驱全线
  - ⚠️ 2026年1月，硕腾复方沙罗拉纳咀嚼片（商品名：**汪宠爱®**）在中国获批，三合一（沙罗拉纳+莫昔克丁+噻嘧啶）内外同驱，是超可信的直接竞品
  - 汪宠爱® 为欣宠克（单方沙罗拉纳，仅驱体外）的升级版，2026年1月29日获批，正在铺货中
  - 短期上市铺货+医生教育仍需时间
- 礼蓝（Elanco）是第二竞争对手，主攻心血管和体外驱虫产品线
  - ⚠️ 注意：礼蓝2026Q1全球增速王（+15%），但Credelio Quattro（四合一驱虫）尚未进入中国，Zenrelia（夫速宁）是皮肤病药而非驱虫药，**短期内礼蓝在中国驱虫市场不构成直接威胁**
- 海正动保在心丝虫/内驱领域快速追赶
- 礼蓝（Elanco）= 礼蓝收购拜耳动保（2020年，68亿美元），爱沃克归礼蓝，与勃林格无直接关系
- 福来恩（Frontline）= 勃林格旗下，非拜耳产品
- 国产替代加速，海正动保、瑞普生物等快速追赶

### 2026年Q1 四大动保企业营收数据

**来源：** 各公司官方财报（2026年4-5月发布），AnySearch 搜索提取

| 公司 | Q1营收 | 同比增速 | 伴侣动物 | 驱虫核心 | 全年指引 |
|------|--------|---------|---------|---------|---------|
| **硕腾** Zoetis | $23亿 | +3% | $15亿(-4%) | Simparica $3.85亿(-1%) | 下调至$96.8-99.6亿 |
| **默沙东** MSD AH | $17.9亿 | +13% | $7.27亿(+9%) | Bravecto $3.79亿(+16%) | 集团$658-670亿 |
| **礼蓝** Elanco | $13.7亿 | **+15%**🏆 | $7.1亿(+12%) | Credelio Quattro加速 | **上调**至$50.1-50.85亿 |
| **勃林格** BI | 无Q1(2025全年~€50亿) | +7.3%(2025) | 中国驱虫#1 | 超可信+博来恩+福味恩 | N/A(私企) |

### 竞品威胁矩阵

| BI 产品 | 主要竞品 | 威胁等级 | 说明 |
|---------|---------|---------|------|
| 超可信 | 汪宠爱®(硕腾) | 🔴高 | 三合一内外同驱，2026.1获批 |
| 超可信 | 海乐妙(海正) | 🟡中 | 内驱出货量大，4500万片/年 |
| 博来恩(猫) | 妙宠爱(硕腾) | 🔴高 | 猫驱虫正面竞争 |
| 博来恩(猫) | 爱沃克(礼蓝) | 🟡中 | 部分重叠 |
| 福来恩 | 拜宠爽(礼蓝) | 🟡中 | 体外驱虫竞争 |
| 福来恩 | 贝卫多(默沙东) | 🟡中 | 12周长效分流 |
| 尼可信/福味恩 | 欣宠克(硕腾) | 🟡中 | 口服外驱竞争 |
| 犬心保 | 海乐妙(海正) | 🔴高 | 出货量碾压 |
| 犬心保 | 大宠爱(硕腾) | 🟡中 | 心丝虫预防重叠 |
| 勃欣定(心脏) | 活心宁(礼蓝) | 🟡中 | 心脏治疗竞争 |

### 核心洞察

1. **🔴 最大威胁**：硕腾汪宠爱®（复方沙罗拉纳）2026年1月中国获批，三合一内外同驱，超可信最直接对标产品
2. **🟢 短期不构成威胁**：礼蓝Credelio Quattro未进入中国，夫速宁(Zenrelia)是皮肤病药非驱虫药
3. **🟡 国产替代加速**：2025年国产宠物驱虫药市占率登顶，海正海乐妙4500万片/年首款破亿
4. **🔵 BI优势**：2025年重夺驱虫#1（+3pts份额），硕腾-3pts；福味恩2025.9新上市+全价位产品矩阵

### 报告索引

- 📄 **竞品生态HTML报告（最新）**：`generate file/pet2026/index.html`
  - GitHub: https://github.com/zhaoomi-zyw/openclaw-workspace-pet-macos/blob/main/generate%20file/pet2026/index.html
- 📄 **硕腾汪宠爱® 情报详情**：`competitor-intel/2026-05-28_zoetis-simparica-trio-china.md`
- 📄 **2026Q1 营收数据JSON**：`skills/records/pet-deworming-Q1-2026-revenue.json`


## 教训/错误记录

### SSH隧道访问OpenClaw（2026-04-18）
- **问题：** 局域网另一台电脑通过 `http://192.168.1.112:18789` 访问 OpenClaw 报 `control ui requires device identity (use HTTPS or localhost secure context)`
- **原因：** 浏览器安全策略禁止非HTTPS/非localhost的设备身份API
- **解决：** 用 SSH 隧道 `ssh -L 18789:localhost:18789 omi@192.168.1.112`，然后访问 `http://localhost:18789`
- **已记录到：** TOOLS.md

## 市场情报（来源：QQ用户图片，2026-04-15）

### 勃林格殷格翰2025大中华区动保市场 - 宠物相关

**数据来源：** CEESA

**宠物（Pet）领域：**
- FY25 净销售额同比增长：**+10%**
- **成就：宠物驱虫药（para）重夺#1**（自2022年Q3以来重新夺回第一）⭐

**市场份额变化（宠物领域）：**
- 勃林格：**+3pts**（占有率增加）
- 硕腾（Zoetis）：**-3pts**（占有率减少）

**备注：** 勃林格宠物驱虫份额增长10%，重新夺回#1地位（自2022年Q3）。硕腾在此领域份额下滑。
