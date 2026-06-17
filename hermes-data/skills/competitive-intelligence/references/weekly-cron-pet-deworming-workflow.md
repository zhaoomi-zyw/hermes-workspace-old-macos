# Weekly Cron: Pet Deworming Competitive Intelligence Report

## Overview
Automated weekly (Monday–Friday) competitive intelligence collection for China's pet deworming medication market. Runs as a scheduled cron job, generates a structured Markdown report saved to `~/knowledge/competitor-intel/`.

## Schedule
- Frequency: Weekly (Friday)
- Week range: Monday–Friday of current ISO week
- Output naming: `YYYY-WXX周-YYYYMMDD.md`

## Search Strategy

### 5 Key Competitors
| Company | Key Products | Search Focus |
|---------|-------------|-------------|
| 勃林格殷格翰 (BI) | 超可信, 博来恩, 福来恩, 福味恩, 尼可信, 犬心保 | New launches, channel strategy, market activities, annual reports |
| 硕腾 (Zoetis) | 大宠爱, 妙宠爱 | China market dynamics, new product approvals, channel partnerships, financials |
| 默沙东动保 (MSD) | 贝卫多 (BRAVECTO, 12-week) | China collaborations, channel dynamics, industry events |
| 礼蓝动保 (Elanco) | 可立奥, 索来多, 拜宠清 | New product ramp-up, China market, e-commerce/hospital channels |
| 国产竞品 | 海乐妙, 海乐旺, 莫爱佳, 赛乐滴, 倍宠恩 | 海正动保 (600267), 瑞普生物, 普莱柯 |

### Search Batches (3 rounds)

**Batch 1 — Competitors (5 queries):**
1. `勃林格 宠物 驱虫 超可信 博来恩 2026`
2. `硕腾 Zoetis 大宠爱 妙宠爱 宠物 驱虫 2026`
3. `默沙东 MSD 贝卫多 BRAVECTO 宠物 2026`
4. `礼蓝 Elanco 可立奥 拜宠清 宠物 驱虫 2026`
5. `海正动保 海乐妙 海乐旺 瑞普 普莱柯 倍宠恩 宠物 驱虫 2026`

**Batch 2 — Market/Industry (5 queries):**
1. `宠物驱虫药 618 电商 大促 价格 2026`
2. `宠物药 新兽药 注册 审批 行业标准 2026`
3. `勃林格殷格翰 宠物 动保 战略 研发 年报 2026`
4. `海正动保 海妙哆 猫三联 处方粮 出海 2026`
5. `宠物驱虫药 市场份额 趋势 新品 2026`

**Batch 3 — Supplementary Financials (3 queries):**
1. `硕腾 Zoetis 2025 财务 年报 业绩 中国 宠物`
2. `礼蓝 Elanco 2025 2026 财报 业绩 宠物 驱虫`
3. `默沙东 动保 MSD 宠物 中国 2026 贝卫多 渠道`

## Report Structure
```markdown
# 宠物驱虫药市场竞争情报 | YYYY年第XX周 | YYYYMMDD

## 本周要闻摘要（5条最重要，🔵 标注战略级情报）
## 竞品动态详情
### 勃林格殷格翰（BI）
### 硕腾（Zoetis）
### 默沙东动保（MSD）
### 礼蓝动保（Elanco）
### 国内竞品（海正动保、瑞普生物、普莱柯等）
## 产品与市场（新品/展会/618电商）
## 本周数据（表格，每项标注来源和日期）
## 行业趋势观察（3-5条，不添加主观评价）
## 下周关注点（5条）
```

## Reporting Requirements
- **Language**: Chinese (中文)
- **Sources**: Every data point tagged with source name + date
- **Strategic intel**: Marked with 🔵 prefix; prioritize financial data, new product approvals, strategic partnerships, channel changes
- **Tone**: Objective facts only, no subjective evaluation
- **Exclusions**: 维克/Virbac (not a deworming drug competitor)

## Source Priority
1. AnySearch real-time search (primary)
2. 新浪财经、东方财富 (financial data)
3. 163.com 网易新闻 (industry news)
4. Official company websites/IR pages
5. 21世纪经济报道 (domestic competitor analysis)

## Content Extraction Workflow
1. Run 3 batch_search calls to gather snippets and URLs
2. Identify ~8-10 high-value URLs for deep extraction
3. Attempt AnySearch extract first; if proxies exhausted, fall back to:
   - `browser_navigate` + `browser_snapshot` for JS-rendered pages
   - `curl` with desktop User-Agent for plain HTML pages (good for 163.com, petdhw.com)
   - If a page is blocked (ERR_BLOCKED_BY_CLIENT like paper.ce.cn), find an alternate source with the same content
4. Cross-reference financial data between multiple sources
5. If a key article is behind WeChat (mp.weixin.qq.com), use the search snippets — WeChat pages rarely render in browser/browser tools

## Output
- **Directory**: `~/knowledge/competitor-intel/`
- **File**: `YYYY-WXX周-YYYYMMDD.md`
- **If nothing new**: Respond with `[SILENT]` to suppress delivery

## Key Metrics to Track
| Metric | Companies | Source Type |
|--------|-----------|-------------|
| Annual/quarterly revenue | All 5 | IR pages, press releases |
| R&D spending | BI, Zoetis, Elanco | Annual reports |
| New product approvals | All | 农业农村部 announcements |
| E-commerce pricing | All | 慢慢买, 天猫, 京东 |
| Channel partnerships | BI, MSD, Elanco | Press releases |
| Market share data | Industry-wide | QYResearch, 白皮书 |
