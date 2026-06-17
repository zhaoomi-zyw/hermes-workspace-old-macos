---
name: a-stock-etf-analysis
description: Analyze Chinese A-share stocks — find related funds/ETFs, check holdings overlap, compare ETFs by key metrics, filter by stock inclusion/exclusion. Use when the user asks about funds/ETFs related to specific stocks, or wants to compare sector ETFs.
version: 1.0
---

# A-Share Stock → Fund/ETF Analysis

## Trigger

- User shows a stock screenshot and asks about related funds/ETFs
- User wants to know which funds hold their stocks
- User asks to compare ETFs in a sector (光模块, 通信, 电网, etc.)
- User wants to filter ETFs by whether they include/exclude a specific stock
- User provides one or more fund codes (A-share or QDII) and asks for analysis, outlook, DCA allocation, or portfolio diversification advice
- Recurring cron job generates a weekly DCA portfolio report (see `references/dca-weekly-report-format.md` for the full report template, search strategy, and pitfalls)

## Workflow

### Phase 1: Stock Identification

If user sends a screenshot:
```bash
# Use mmx vision (read-image skill), NOT vision_analyze
mmx vision describe --image <path> --prompt "请详细描述这张图片中的所有内容..." --quiet
```

### Phase 2: Fund/ETF Search

Use anysearch batch_search with multiple targeted queries:

```
- "<stock> <code> 重仓基金 持仓 2026 一季报"
- "<stock> <code> 基金持仓明细"
- "<sector> ETF 基金 2026 持仓 表现"
```

Key data sources (in priority order):
1. 同花顺 F10 (basic.10jqka.com.cn) — fund holdings, industry classification, index membership
2. 天天基金 (fundf10.eastmoney.com) — ETF full holdings
3. 中财网 (cfi.cn) — fund position changes over time
4. 搜狐证券 (q.stock.sohu.com) — fund holdings by report period
5. 中证指数官网 (csindex.com.cn) — index factsheets (PDF)

### Phase 3: ETF Comparison

When comparing ETFs in the same sector, use these standard metrics:

| Metric | What to check |
|---|---|
| 跟踪指数 | Which index does it track? |
| 核心持仓纯度 | Weight of the key stocks the user cares about |
| 规模 | Fund AUM (affects liquidity) |
| 费率 | Management + custody fees |
| 今年以来收益 | YTD performance |

### Phase 4: Stock Inclusion/Exclusion Check

To determine if a specific stock is in an ETF:

1. **Check the stock's industry classification first** — use 同花顺诊股 page or search:
   ```
   "<stock> 所属行业 申万行业 所属指数"
   ```

2. **Check the ETF's tracking index** — the index name reveals sector scope:
   - 中证电网设备主题 (931994) → power grid equipment ONLY
   - 中证全指通信设备 (931160) → communication equipment ONLY
   - 中证5G通信主题 (931079) → 5G communication chain

3. **Logic check**: If the stock's industry ≠ the index's sector, it's NOT in the ETF
   - 菲菱科思 = 通信设备 → in 931160, NOT in 931994
   - This logic check is more reliable than trying to scrape full component lists

4. **For confirmation**: Search `"<stock>" "所属指数" OR "指数成分"` — 同花顺 often lists index membership

### Phase 5: Filtering & Recommendation

Present in table format for easy comparison, then give clear recommendations with rationale.

## Key Domain Knowledge

See `references/dca-weekly-report-format.md` for the weekly DCA portfolio report workflow, search strategy, QDII limit checking, and common pitfalls.

See `references/qdii-fund-portfolio-analysis.md` for QDII fund identification, overlap analysis, subscription status checking, and portfolio construction methodology.

See `references/optical-module-etf-comparison.md` for detailed 光模块/CPO ETF comparison data.

See `references/feilingkesi-institutional-exodus.md` for a case study on interpreting fund position changes.

See `references/robot-ai-chain-etfs.md` for robot ETF comparison, AI token supply chain ETF data, and upstream component stocks.

See `templates/monitor-limit.py` for a reusable watchdog script that scrapes 天天基金网 for purchase limit changes and alerts on delta.

See `templates/monthly-portfolio-report.py` for a generic monthly portfolio report script: fetches NAVs for cash-pool + DCA funds, compares month-over-month, outputs a formatted WeChat-friendly report. Set up as a no_agent=True cron job on the last few weekdays of each month (schedule e.g. `30 20 26-31 * 1-5`). Customise the fund config block at the top of the file for the user's holdings.

See `references/omi-monitored-funds.md` for Omi's specific monitored QDII funds, limit history, and cron job configuration.

See `references/short-debt-cash-pool-allocation.md` for Omi's prior 35–40万 allocation pattern: equity/QDII daily DCA as the growth sleeve plus a short-debt cash pool split into stable and flexible sleeves.

See `references/monthly-portfolio-report-setup.md` for the automated month-end portfolio report cron job and the DCA fund purchase-limit monitoring script created during this session. Both are reusable for recurring fund tracking. Also documents:
- Lock-up type distinctions (滚动持有 ❌ vs 持有期 ✅ vs 开放申赎 ✅) with Omi's explicit preference
- Purchase limit checking workflow with regex patterns
- Full yield/risk ladder from 同业存单 (1.28%) through 长债 (4.54%), all within no-rolling-lockup constraint
- Fund-specific caveats (019112 size risk, 485119 100元/day limit landmine, 019872 as top balanced pick)
- Sample allocation templates at conservative/balanced/aggressive/very-aggressive tiers

### Short-Debt Cash Pool + Equity DCA Pattern

When Omi asks about large idle cash allocation (35–40万) or asks to resend a prior fund allocation conclusion, use the short-debt cash-pool framework instead of giving only sector/ETF analysis:

1. **Retrieve prior conclusion first** with session search if the user asks “之前/上次的配比”. Do not reconstruct from memory alone.
2. Present as **权益进攻 + 短债防守**: daily DCA for QDII/A500-style equity exposure; short-debt funds for the defensive cash pool.
3. For short-debt cash pools, split into stable main sleeve + flexible/dry-powder sleeve. See `references/short-debt-cash-pool-allocation.md` for current fund candidates, yield/risk ladder, and purchase limit data. **Do NOT hardcode old fund codes** (001497/019112) from prior sessions without first checking current purchase limits and the user's lock-up preferences — those specific funds may no longer be suitable due to 1万/day limits, small scale, or 滚动持有 rules.\
4. **Lock-up type constraint is the FIRST filter**, not an afterthought. Before discussing any cash-pool fund, determine which lock-up type(s) the user accepts. Omi's explicit hierarchy: 开放申赎(最偏好) > 持有期(可接受) > 滚动持有(明确排斥). Do not recommend 60天/90天/6个月 unless the user explicitly extends their max. When in doubt, ask.\
5. Explain rolling-holding rules precisely: “30天滚动/一个月滚动” means each purchase is locked for one cycle, opens only on a redemption window, and if not redeemed rolls into the next cycle. Do **not** imply “满30天后任意一天都能赎回.”\
6. Preserve the original conclusion when resurfacing old advice, but include caveats discovered later in that same conversation.

### QDII Purchase Limit Monitoring

QDII 基金频繁因外汇额度耗尽调整每日申购上限。Monitoring workflow:

1. **Look up current limit**: Scrape `https://fundf10.eastmoney.com/jjgg_{code}.html`, regex: `单日累计购买上限(\d+)\s*元`
2. **Set up watchdog cron**: Use `templates/monitor-limit.py` with `no_agent=True`. On first run exits silently (baseline), on change outputs alert. Cron with `script='monitor-<fund>-limit.py'`, `no_agent=True`, deliver to origin.
3. **Key pattern**: `python3 monitor-limit.py FUND_CODE FUND_NAME STATE_FILE` — state file at `~/.hermes/profiles/main/cron/state/<fund>_limit.json`
4. **Pitfall**: 天天基金网 may cache stale data; cross-reference with 基金公司官方公告 for authoritative limits. Different share classes (A/C/USD) have separate limits.

Common QDII funds: 摩根纳斯达克100 (019172), 华夏全球科技先锋 (005698), 广发纳斯达克100 (270042), 博时标普500 (050025).

### 光模块/CPO ETF 核心指标："易中天"含量

"易中天" = 新易盛(300502) + 中际旭创(300308) + 天孚通信(300394) — the three core 光模块 stocks. Their combined weight in an ETF directly measures its 光模块 purity.

| ETF | 代码 | 易中天含量 | 光模块占比 | 规模 (2026Q1) |
|---|---|---|---|---|
| 创业板AI 华宝 | 159363 | ~41% ★最高 | ~50% | ~74亿 |
| 创业板AI 华夏 | 159381 | ~39% | ~50% | ~22亿 |
| 通信ETF 国泰 | 515880 | ~37% | ~40% | ~332亿 ★最大 |
| 华夏5G通信 | 515050 | — | — | ~78亿 |
| 富国通信设备 | 159583 | ~37% | 高 | ~14亿 |

### 电网设备 ETF

| ETF | 代码 | 规模 | 亨通光电权重 | 中天科技权重 |
|---|---|---|---|---|
| 华夏电网设备 | 159326 | ~336亿 | 8.49% | 6.71% |

### Fund Holding Data Interpretation

- **持有基金家数 trend**: Increasing = institutional confidence; decreasing rapidly (87→4 in one year) = red flag
- **基金持仓占流通股比例**: >10% = strong institutional backing; <5% = thin
- **加仓 vs 减仓**: Net inflow direction matters more than total count

## Pitfalls

1. **anysearch extract frequently fails on Chinese financial sites** (eastmoney, 同花顺, sina finance) due to anti-scraping measures. Fall back to search snippets and logic-based deduction instead of expecting full page extraction.

2. **CSI index factsheet PDFs are image-based** — text extraction via `strings` or `pdftotext` won't work. Use search snippets or the lixinger.com component list instead.

3. **ETF "全部持股" pages are often dynamic-load** (JS-rendered). Browser tools are too slow. Prefer logical deduction from the index name + stock's industry classification.

4. **Don't confuse "机构持仓" with "基金持仓"** — 机构 includes 社保, QFII, 保险, 信托, 券商, not just funds. For fund-specific analysis, filter to 基金 only.

5. **基金持仓数据有滞后** — quarterly reports are filed 15-45 days after quarter end. Q1 2026 data was published late April 2026. Always note the data date.

6. **"30天滚动持有"不是"30天后每天能赎"**. 滚动持有类基金每笔买入单独锁定期，到期有赎回窗口（通常1-2天），不赎就自动续约下一周期。不要误读为"满30天后随时可赎"。这是Omi明确排斥的类型。

7. **分清三种锁定期模式**：①**滚动持有**（如"XX天滚动持有"）— 到期窗口可赎，不赎续约，Omi明确不选；②**持有期**（如"XX天持有期"，无"滚动"）— 持有满X天后任意交易日可赎，Omi可接受；③**开放申赎**（无"持有期"、无"滚动"字样）— 无锁定，当天或T+1可赎，Omi最偏好。

8. **同类基金可能有不同购买限制，必须逐一检查.** 同系列的不同份额（A/B/E类）可能分别有独立的每日申购限额、暂停申购等状态。推荐前必须检查当前最新限制，不要假定"同系列都一样"。数据源：天天基金基金详情页 `fundf10.eastmoney.com/jjgg_{code}.html`，正则 `单日累计购买上限[\d.]+万`。

9. **推荐短债/现金池基金时必须检查当前购买限额和持有规则**，不能只看历史收益排名。优先级：持有规则是否匹配 → 规模是否够大（>5亿较安全） → 购买限额是否够用 → 近1年/近3月收益节奏。

10. **QDII基金申购状态是定投计划的关键前提** — QDII基金频繁因外汇额度耗尽而暂停申购或限大额。任何涉及QDII的定投建议，必须先确认申购状态（开放/限大额/暂停）。官方基金公司官网（chinaamc.com, cifm.com等）的信息比第三方平台更权威。状态可能快速变化（如4月暂停、6月调整额度），需搜索最新公告。如果状态是"暂停申购"，定投计划无法执行，需立即提供替代方案。

11. **anysearch batch_search 最多5个查询** — CLI 限制每次调用最多5个 query。如需更多查询，拆分为2次调用（先5后N）。

12. **限大额刚好卡在定投金额上的情况是红色警报** — 如 QDII 基金限大额 100元/日，用户定投恰好 100元/日，需醒目标注 🔴**临界**。如果额度进一步收紧，定投将中断。建议提示用户关注官方公告并准备替代方案。

13. **QDII 净值 T+2 滞后是常态，不是数据缺失** — 搜索到的"最新净值"可能反映 1-2 个市场日前。不要在报告中标注"数据缺失"，而是标注净值日期并说明滞后原因。
