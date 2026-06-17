---
name: competitive-intelligence
description: "Market research, competitor analysis, intelligence gathering, and portfolio/fund research — structured reporting workflows"
version: 1.1.0
author: Agent
platforms: [macos, linux]
metadata:
  hermes:
    tags: [market-research, competitive-analysis, bi, boehringer-ingelheim, pet-industry, fund-research, portfolio-analysis]
---

# Competitive Intelligence

Research workflows for building competitor ecosystems, market landscapes, structured reports, and investment portfolio analysis. Originally designed for BI pet/animal health intelligence; extended to AI/tech fund research.

## Portfolio Analysis Workflow (Fund/ETF Research)

When analyzing a user's watchlist of funds and stocks:

1. **Deconstruct the supply chain** — map each holding to its position in the industry value chain
2. **Detect overlaps** — identify ETFs tracking same index, ETF-vs-stock overlap, cross-ETF duplicate holdings
3. **Deep analyze key funds** — use fund-analysis-agents multi-agent platform for AI-driven analysis
4. **Consolidate** — merge duplicates, drop mini-funds (<2亿), keep best-in-category
5. **Allocate** — 5-direction framework with cash reserve for dips

See `references/ai-token-supply-chain-fund-mapping.md` for the full methodology.
See `references/fund-analysis-agents-operations.md` for platform setup and troubleshooting.

## Research Workflow (AnySearch)

### Key AnySearch Commands

```bash
# Batch search (max 5 queries per call)
python3 scripts/anysearch_cli.py batch_search --queries '[
  {"query":"勃林格 宠物驱虫药 最新动态","max_results":5},
  {"query":"硕腾 Zoetis 宠物驱虫药 新产品","max_results":5}
]'

# Extract article content
python3 scripts/anysearch_cli.py extract "https://example.com/article"

# Single search
python3 scripts/anysearch_cli.py search "query keywords" --max_results 5
```

### AnySearch Limitations

| Issue | Workaround |
|-------|-----------|
| batch_search max 5 queries | Split into multiple batch_search calls |
| extract fails on PDF | Find the HTML source instead (press release > PDF) |
| 403 on some sites (Zhihu, WeChat) | Use browser snapshot instead |
| 403 on investor relations pages | Use official press release URL, not IR page |
| extract proxies exhausted ("all 14 extract proxies failed") | Use browser_navigate + browser_snapshot for full-page content; curl with desktop User-Agent as lightweight alternative for plain HTML pages |
| page blocked by client (ERR_BLOCKED_BY_CLIENT) | Try alternate source URL with same content (e.g., petdhw.com instead of paper.ce.cn) |
| WeChat articles (mp.weixin.qq.com) don't render | Rely on search snippets; WeChat pages rarely load in browser/browser tools |

### Best Practices

1. **Search in both Chinese and English** for full coverage
2. **Prefer official press releases** over news summaries for financial data
3. **Private companies** (Boehringer Ingelheim) don't publish quarterly data — use annual reports
4. **Cross-reference revenue data** between competitor sources when possible
5. **Save search results** to reference files for future reuse

### Report Generation

User prefers:
- **HTML** format for visual reports (dark/light theme toggle via CSS variables)
- **JSON** format for structured data storage
- File storage under `generate file/` directory or skill's `references/` directory

### HTML Report Template

```css
/* BI green theme */
--bi-green: #00a651;
--bi-dark: #004d26;
--bg: #ffffff; /* User prefers white background */
--card-bg: #ffffff;
--text: #2c3e2d;
--text-muted: #7f8c8d;
--border: #e8ece8;
--red: #c0392b;
--yellow: #b7950b;
--green: #1a8a4a;
```

---

## References

- `references/weekly-cron-pet-deworming-workflow.md` — Weekly cron job workflow: search queries, report structure, output paths, content extraction fallback patterns
- `references/pet-deworming-competitive-2026.md` — Pet deworming market Q1 2026 competitive landscape (all 5 companies)
- `references/q1-2026-earnings-urls.md` — Official earnings press release URLs for Zoetis, Merck, Elanco, Boehringer
- `references/ai-token-supply-chain-fund-mapping.md` — AI/token industry chain → ETF fund mapping methodology; portfolio analysis workflow; under-the-radar segment discovery
- `references/fund-analysis-agents-operations.md` — Fund Analysis Agents platform deployment, PromptLoader bug fix, operational troubleshooting
- `references/glp-1-survodutide-2026.md` — GLP-1/GCG competitive landscape: survodutide Phase III data, MASH approved drugs (Wegovy/Rezdiffra), mazdutide head-to-head comparison, Phase 3 trial timelines (LIVERAGE vs SYNERGY-Outcomes)
- `references/china-pet-industry-capital-trends-2026.md` — 中国宠物行业资本趋势2026：市场规模3126亿(+4.1%)→4050亿(CAGR 9.6%)，融资从品牌流量→供应链/医疗/AI，四大未来方向
