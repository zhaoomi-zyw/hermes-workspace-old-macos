# QDII Fund Analysis & Portfolio Construction

## When This Applies

User provides one or more fund codes (usually 6-digit, starting with 0 or 5) and asks for:
- Fund identification (what is this fund?)
- Performance analysis and outlook
- Portfolio review: overlap detection, concentration risk
- Third-fund recommendation for diversification
- Daily DCA (定投) amount allocation

## Workflow

### Phase 1: Identify Funds

Search for each fund code with 2-3 queries in one batch_search:

```
"<code> 基金 是什么基金 持仓 基金经理 2026"
"<code> 基金 净值 收益 申购状态"
```

Extract from search snippets:
- Full name, fund company, manager
- Type (QDII/混合/指数/债券), inception date
- AUM (净资产规模), subscription status (申购状态)
- Recent returns (近1年, 今年以来, 成立以来)

### Phase 2: Get Holdings

Search for holdings separately:

```
"<code> 持仓股票 2026一季报 前十大"
"<code> 持股明细"
```

Key data sources:
- fund.stockstar.com/funds/f10/fundzg_<code>.html — detailed holdings table
- fundf10.eastmoney.com/ccmx_<code>.html — fund holdings
- danjuanfunds.com/funding/<code> — clean summary with YTD/returns

**Pitfall**: `extract` almost always fails on stockstar.com and eastmoney.com. Rely on search snippets — the top 3-5 holdings usually appear inline.

### Phase 3: Check Subscription Status (CRITICAL for QDII)

QDII funds frequently hit foreign investment quota limits. Always search:

```
"<code> 申购状态 限购 暂停申购 2026"
```

Statuses and implications:
| Status | Meaning | DCA OK? |
|--------|---------|---------|
| 开放申购 | Fully open | ✅ |
| 限大额 (e.g. 单日≤1万元) | Capped | ✅ for small DCA |
| 暂停申购 | Closed to new money | ❌ Plan blocked |
| 暂停申购 + 调整公告 | May be reopening soon | ⚠️ Monitor |

Official fund company site (chinaamc.com, cifm.com) is the most authoritative source for status.

### Phase 4: Overlap & Correlation Analysis

When user holds 2+ funds, check:

1. **Asset class overlap**: Both QDII? Both US? Both tech? → High correlation
2. **Holdings overlap**: Do top positions overlap (NVDA, TSMC, AAPL appear in both)?
3. **Style overlap**: Active vs passive, but both tech-growth → same factor exposure

If correlation is obviously high (both US tech QDII), quantify with:
- NASDAQ 100 PE and historical percentile (use danjuanfunds.com/dj-valuation-table-detail/NDX)
- Each fund's volatility (标准差) from fundf10 eastmoney 特色数据

### Phase 5: Gap Identification

Typical gaps in a tech-heavy QDII portfolio:
| Gap | Diversifier | Correlation to US Tech |
|-----|-------------|:---:|
| Fixed income / stability | 短债纯债基金 (C类) | ~0 |
| Inflation hedge | 黄金ETF联接 | Low |
| Domestic exposure | A股宽基 (沪深300/A500) | Medium |
| Value/dividend | 红利低波指数 | Low-Medium |

**Default recommendation**: Short-term bond fund (短债C类) — genuinely uncorrelated, <1% max drawdown, 3-4% annualized, acts as "dry powder" for rebalancing when equities dip.

### Phase 6: Allocation Recommendation

Present as a table:

| Fund | Code | Daily | Monthly | Weight | Role |
|------|------|:--:|:--:|:--:|------|
| ... | ... | ... | ... | ... | ... |

Typical formulas:
- Aggressive (young, long horizon): 75-80% equity / 20-25% bond
- Balanced: 60% equity / 40% bond
- Monthly total = daily × ~22 trading days

### Phase 7: Execution Checklist

Always end with an actionable checklist:
1. Confirm subscription status of each fund on user's actual platform
2. If a fund is closed, suggest alternatives (C-class shares, similar strategy from different company)
3. Note that QDII quota is fungible — if one华夏 QDII is closed, others likely are too

## Key Data Points to Collect Per Fund

| Metric | Source | Priority |
|--------|--------|----------|
| 基金全称 + 类型 | search snippet | Critical |
| 基金经理 + 从业年限 | search snippet | High |
| 资产规模 (AUM) | search snippet | High |
| 申购状态 | chinaamc.com / cifm.com | **Critical** |
| 近1年收益 | 同花顺爱基金 / 天天基金 | High |
| 今年以来收益 | danjuanfunds.com | High |
| 标准差 (1Y) | eastmoney 特色数据 | Medium |
| 夏普比率 (1Y) | eastmoney 特色数据 | Medium |
| 前十大持仓 | stockstar.com (via search) | High |
| 跟踪指数 + PE分位 | danjuanfunds.com valuation | Medium (index funds) |

## Pitfalls

1. **extract fails on Chinese fund sites**: stockstar.com, eastmoney.com, 同花顺 all block extract. Search snippets are the primary data source — plan queries to maximize snippet density.

2. **Conflicting subscription status**: Different sites may show different statuses (暂停 vs 限大额). The official fund company site is authoritative. Also check for recent announcements (调整公告) that signal status changes.

3. **QDII quota exhaustion cascade**: When one fund from a company closes, check if the company's other QDII funds are also affected. C-class shares sometimes have separate quotas.

4. **Don't recommend more equity for diversification**: User asking for "分散风险" with an already equity-heavy portfolio needs bonds/commodities, not another equity fund (even if from a different geography).
