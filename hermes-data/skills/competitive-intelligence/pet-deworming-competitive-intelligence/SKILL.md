---
name: pet-deworming-competitive-intelligence
description: Weekly competitive intelligence report on the Chinese pet deworming drug market. Covers BI, Zoetis, MSD, Elanco, and domestic competitors (海正动保, 瑞普生物, 普莱柯). Uses AnySearch batch_search for multi-company + industry queries.
version: 1.0.0
---

## Trigger

This skill fires for the weekly cron job that collects competitive intelligence on the Chinese pet deworming drug market. Run every Friday (or the last business day of the week).

## Prerequisites

- AnySearch CLI accessible (uses `python3` runtime; runtime.conf maps to the pet-competitor profile's CLI)
- Output directory: `~/knowledge/competitor-intel/`
- The `anysearch` skill must be available

## Competitor Focus (5 companies, deworming drugs only)

### 1. 勃林格殷格翰 (BI)
- Products: 超可信 (NexGard), 博来恩 (Broadline), 福来恩 (Frontline), 福味恩, 尼可信 (NexGard Spectra), 犬心保
- Focus: new launches, channel strategy, market activities, financials, strategic moves

### 2. 硕腾 (Zoetis)
- Products: 大宠爱 (Revolution/Stronghold), 妙宠爱 (Revolution Plus/Stronghold Plus)
- Focus: China market dynamics, new approvals, channel partnerships, financials

### 3. 默沙东动保 (MSD / Merck Animal Health)
- Products: 贝卫多 (BRAVECTO, fluralaner, 12-week long-acting)
- Focus: China partnerships, channel dynamics, industry events

### 4. 礼蓝动保 (Elanco)
- Products: 可立奥 (Credelio, oral), 索来多 (Seresto collar), 拜宠清 (Drontal, oral internal)
- Focus: new product ramp-up, China market, e-commerce/vet hospital channels

### 5. Domestic competitors
- 海正动保: 海乐妙, 海乐旺, 莫爱佳, 喜倍安, 赛乐滴, 海妙哆 (cat triple vaccine)
- 瑞普生物: pet deworming drugs, pipeline reserves
- 普莱柯: 倍宠恩 (compound fipronil drops)

## Search Methodology

Use AnySearch `batch_search` in two batches of 5 queries each, `max_results=8` per query. The CLI command is read from `runtime.conf` in the anysearch skill directory (points to pet-competitor profile's CLI).

### Batch 1 — 5 competitors:
```
勃林格 宠物 驱虫 超可信 博来恩 2026
硕腾 Zoetis 大宠爱 妙宠爱 宠物 驱虫 2026
默沙东 MSD 贝卫多 BRAVECTO 宠物 2026
礼蓝 Elanco 可立奥 拜宠清 宠物 驱虫 2026
海正动保 海乐妙 海乐旺 瑞普 普莱柯 倍宠恩 宠物 驱虫 2026
```

### Batch 2 — Market/Industry:
```
宠物驱虫药 618 电商 大促 价格 2026
宠物药 新兽药 注册 审批 行业标准 2026
勃林格殷格翰 宠物 动保 战略 研发 年报 2026
海正动保 海妙哆 猫三联 处方粮 出海 2026
宠物驱虫药 市场份额 趋势 新品 2026
```

### Information Source Priority
1. AnySearch real-time search (primary)
2. 新浪财经, 东方财富 (financial data)
3. 163.com 网易新闻 (industry news)

## Extraction Strategy

After batch search, identify the highest-value articles and extract them via `anysearch extract <URL>`. Prioritize:
- Financial reports / annual results
- New drug approvals / regulatory announcements
- Strategic partnerships / channel changes
- Industry white papers with market sizing data

**Note:** Some URLs (腾讯新闻, 财联社, 21经济网, moa.gov.cn) may fail with "all extract proxies exhausted." The search snippet alone is sufficient for those — do not retry excessively. The economic daily (经济日报), BI official site, MSD official site, and chinapp.net.cn typically extract well.

## Report Structure

Save to: `~/knowledge/competitor-intel/YYYY-WXX周-YYYYMMDD.md`

**Reference files:**
- `references/report-template.md` — Markdown template with all sections pre-formatted. Copy this and fill in the sections.

Sections:
1. **本周要闻摘要** (5 most important items, prioritize financial/regulatory/strategic)
2. **竞品动态详情** (per-company subsections)
3. **产品与市场** (new products, exhibitions, 618 e-commerce)
4. **本周数据** (table with source and date for each data point)
5. **行业趋势观察** (3-5 observations, no subjective commentary)
6. **下周关注点** (5 forward-looking items)

## Report Requirements
- Use Chinese throughout
- Every piece of information must cite date and source
- 🔵 marks newly identified strategic intelligence
- Objective facts only, no subjective evaluation
- Market data must cite source
- Prioritize: financials/annual reports, new drug approvals, strategic partnerships, channel changes
- Exclude Virbac/维克 (not a deworming competitor)

## Pitfalls
- **Do NOT use execute_code** for searches in cron mode — it will be blocked. Use terminal() directly.
- The anysearch `runtime.conf` may point to a different profile's CLI (e.g., pet-competitor). Trust the configured path.
- Some government URLs (moa.gov.cn, agri.cn) and paywalled news sites may fail extraction. Use search snippets as fallback.
- The week number format is ISO week (`date +%Y-W%V`). Verify with `date` command.
- When search results are sparse for a competitor, note it honestly rather than fabricating content.
