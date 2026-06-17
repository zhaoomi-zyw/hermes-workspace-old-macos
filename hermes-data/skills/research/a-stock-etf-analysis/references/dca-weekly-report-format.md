# DCA Weekly Report Format

## Trigger

This reference applies when generating a recurring weekly fund DCA (定投) portfolio report. The report is delivered via WeChat or similar messaging platforms as a cron job — no user interaction, fully autonomous.

## Report Structure

### 普通周报（非月末、非首周）

```
# 📊 Omi 基金定投周报
## YYYY年M月D日 — M月D日（第N周）

---

## 一、本周净值表现

| 基金 | 代码 | 最新净值 | 本周涨跌 | 今年以来 | 定投日额 |
|------|------|:--:|:--:|:--:|:--:|
| <name1> | <code1> | X.XXXX (MM/DD) | +/-X.X% | +/-X.X% | X元 |
| <name2> | <code2> | ... | ... | ... | ... |
| <name3> | <code3> | ... | ... | ... | ... |

> ⚠️ QDII基金净值有T+2滞后，<code> 最新披露至MM/DD。

## 二、净值走势详析

### 🟢 <fund_name> — 本周亮点/回调

| 日期 | 单位净值 | 日涨跌 |
|------|------|:--:|
| MM/DD (五) | X.XXXX | +/-X.X% |
| ... | ... | ... |

<1-2 sentence narrative per fund explaining the move>

## 三、本周市场关键动态

### 🇨🇳 A股
- 指数涨跌、板块轮动、资金方向（2-3条要点）

### 🇺🇸 美股科技
- NASDAQ/NDX走势、重大事件（英伟达/苹果/联储等）、估值水平

### 🌍 全球
- 地缘、宏观事件对组合的影响

## 四、定投扣款状态

| 基金 | 日定投额 | 申购状态 | 扣款判断 |
|------|:--:|------|:--:|
| <code> | X元 | 开放申购/限大额X元/暂停 | ✅/⚠️/🔴 |

> 🚨 限大额金额 ≤ 定投金额时为**红色警报**。如果限额低于定投金额（如限额10元 vs 定投100元），标注 🔴**无法执行**并提供替代方案。

## 五、本周小结

> 一句话总结 + 关键亮点或隐忧。不超过3句。
```

### 首周报告（定投启动周）

在普通周报基础上：
- 第一节增加"成立以来"列（如数据可得）
- 第四节强调"今日为定投首日"，提示确认扣款
- 第五节用"开局"语气

### 月末周报（每月最后一个周五）

在普通周报基础上增加：
- 第六节：本月定投总额、累计投入、当前市值
- 第七节：每只基金的月收益率和累计收益率
- 第八节：组合整体收益率
- 第九节：下月展望（1-2句）

## Content Rules

- **Language**: Chinese only, WeChat 直接可读
- **Headers**: Markdown is fine (cron delivers as text), use `#`/`##`/`###` for hierarchy
- **Tables**: Use markdown tables for NAV data, subscription status
- **Tone**: 数据优先，简洁有力，不啰嗦
- **Data**: Search-sourced, always cite date cutoff and source
- **Missing data**: Note the cutoff date, explain QDII lag — don't say "数据缺失" when it's just T+2 delay
- **Anomalies**: Flag prominently with 🚨 or 🔴 for critical issues, ⚠️ for warnings

## Efficient Search Strategy

**⚠️ The dates in the query templates below are EXAMPLES. Always replace with the actual current week's dates before executing. Use `freshness: "week"` for the most relevant results.**

**Round 1: batch_search (5 queries)** — fund NAVs + market overview

```json
[
  {"query": "<fund1_code> <fund1_name> 净值 2026年6月4日 6月5日 申购状态", "max_results": 3},
  {"query": "<fund2_code> <fund2_name> 净值 2026年6月4日 6月5日 申购状态", "max_results": 3},
  {"query": "<fund3_code> <fund3_name> 净值 2026年6月 最新", "max_results": 3},
  {"query": "A股 上证指数 本周行情 2026年6月1日 6月5日 周报", "max_results": 3},
  {"query": "纳斯达克100 美股 本周行情 2026年6月 科技股", "max_results": 3}
]
```

**Round 2: batch_search (5 queries)** — granular NAV + index specifics + market events

```json
[
  {"query": "<fund1_code> <fund1_name> 净值 6月4日 6月5日 2026", "max_results": 3},
  {"query": "<fund2_code> <fund2_name> 净值 6月4日 6月5日 2026 限大额", "max_results": 3},
  {"query": "<fund3_code> <fund3_name> 净值 6月4日 6月5日 2026", "max_results": 3},
  {"query": "<tracking_index> <index_code> 6月5日 收盘 本周涨跌幅", "max_results": 3},
  {"query": "纳斯达克100指数 6月1日 6月5日 2026 本周涨跌", "max_results": 3}
]
```

**Round 3 (if needed):** individual `search` calls for missing NAV points or subscription status details.

**Key data sources per fund type:**
- A-share funds (022430): chinaamc.com + 天天基金 eastmoney
- QDII funds (005698, 019172): company official site FIRST (chinaamc.com / cifm.com), then danjuanfunds.com
- Market data: 163.com 周报 summaries, Investing.com historical data for NDX, 同花顺 for A-share indices
- Latest trading day data if first batch missed it

## Critical Checks

### QDII Subscription Status

QDII funds (005698, 019172, etc.) frequently hit foreign exchange quota limits. Check status on EVERY report:

| Status | Action |
|--------|--------|
| 开放申购 | Normal, proceed |
| 限大额 (e.g. ≤100元/日) | Flag if user's daily DCA equals or exceeds limit |
| 暂停申购 | **Blocked** — DCA plan cannot execute, provide alternatives immediately |

**Source priority**: Official fund company site (chinaamc.com, cifm.com) > eastmoney > other aggregators

### Fund Code Verification

Code vs name mismatches happen. If user provides both, verify they match:
- Search the code to get the actual fund name
- If mismatch, flag prominently and provide the correct code

### NAV Data Lag

QDII funds report NAVs with T+1 or T+2 delay. The "latest" NAV may reflect 1-2 market days ago. Always:
- Note the data cutoff date
- If US markets moved significantly since last NAV update, mention the expected direction ("下个净值日料将回调")

## Pitfalls

1. **Don't use extract on Chinese fund sites** — eastmoney, 同花顺, sina finance all block it. Search snippets are the primary data source.
2. **QDII NAV delay confusion**: 6/3 US market data reflects in 6/4 or 6/5 NAV. Don't claim missing data just because it hasn't posted yet.
3. **Multiple data sources conflict**: Different aggregators may show different NAVs for the same date (QDII valuation timing differences). Use the official fund company site as authoritative.
4. **A-share vs NASDAQ week mismatch**: Chinese markets and US markets have different holiday calendars. Verify trading days independently.
5. **batch_search 5-query limit**: The CLI enforces max 5 queries per call. Split into 2 calls if needed.

6. **chinaamc.com main page staleness**: The fund overview page (`index.shtml`) can show severely stale data — e.g., April 30 NAV and "暂停申购" in mid-June when the fund is actually open. The `lishijingzhi.shtml` subpage has more current NAVs. Always cross-reference status with eastmoney (天天基金), which scrapes daily and is often more timely than official fund company pages for subscription status.

7. **同花顺 history net JS rendering**: `fund.10jqka.com.cn/pc/<code>/historynet.html` shows daily NAV history tables but is JS-rendered. Search snippets only capture the first few rows. Use for confirmation of latest NAV but not for full historical extraction.

8. **cifm.com limit invisibility**: The official cifm.com fund page (`cifm.com/fund/019172/`) shows NAV but NOT the limit amount in search snippets. Always check eastmoney for the actual limit figure — it's in the status bar: "交易状态：限大额（单日累计购买上限X元）".

9. **Search query date adaptation**: The search query templates above use hardcoded example dates. Replace with the actual current week's date range before executing. For the weekly market overview query, prefer "本周涨跌" or "周报" keywords to get pre-computed summaries from 163.com rather than computing week-over-week changes manually.

10. **Limit ≤ DCA is 🔴, not just equal**: The alert triggers when the fund's single-day purchase limit is **less than or equal to** the user's daily DCA amount. If the limit drops below the DCA (e.g., 10元 limit vs 100元 DCA), the DCA plan cannot execute at all — this is more severe than when they're equal. Flag with 🔴 and provide alternative fund suggestions immediately.
