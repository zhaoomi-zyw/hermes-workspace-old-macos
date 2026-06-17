# Monthly Portfolio Report & DCA Limit Monitoring

Created 2026-06-15 for Omi's fund portfolio. These are reusable scripts for automated recurring fund tracking.

## Scripts inventory

Both scripts live at `~/.hermes/profiles/main/scripts/` and run as `no_agent=True` cron jobs (self-contained Python, no LLM needed).

### 1. Monthly Portfolio Report (`monthly-portfolio-report.py`)

**Purpose**: Generate a comprehensive month-end return report covering both cash pool (lump-sum bond funds) and DCA (daily equity/QDII) holdings.

**Schedule**: `30 20 26-31 * 1-5` — runs on weekdays during the last week of each month at 20:30. The script itself detects whether today is the last trading day; skips silently if not.

**Delivery**: WeChat via `deliver="weixin"`.

**What it tracks**:
| Category | Funds tracked | Method |
|---|---|---|
| Cash pool | 020080 华富恒稳纯债D, 019872 长城短债D | NAV change from purchase-date baseline |
| DCA | 005698 华夏全球科技先锋QDII A, 022979 华夏中证A500ETF联接A | Cumulative invested vs estimated current value |

**State persistence**: Stores baseline NAVs and DCA share estimates in `~/.hermes/profiles/main/cron/state/monthly_portfolio.json`. On first run, establishes baselines from purchase date.

**Key design decisions**:
- Cash pool start date is 2026-06-18 (configurable via `CASH_POOL_START` variable)
- DCA initial invested amounts set from Alipay screenshot (005698: 1150元, 022979: 650元 as of 2026-06-15)
- DCA additional contributions estimated from trading days since last report
- NAV fetched via eastmoney fundgz API (`fundgz.1234567.com.cn/js/{code}.js`)
- QDII NAV has T+2 lag — noted in report footer

**Report sections**:
1. Cash pool: per-fund cost, purchase NAV, current NAV, profit/loss, totals
2. DCA: per-fund daily rate, cumulative invested, current market value, profit/loss
3. Grand total: combined cost, market value, profit/loss, total return %

### 2. DCA Fund Limit Monitor (`monitor-dca-limits.py`)

**Purpose**: Watch for purchase limit changes on Omi's active DCA funds. Silent when unchanged; alerts on any delta.

**Schedule**: `0 9,21 * * *` — twice daily at 09:00 and 21:00.

**Delivery**: WeChat via `deliver="weixin"`.

**Alert levels**:
| Condition | Level | Example output |
|---|---|---|
| Limit changed (up or down) | 🔔 Info | `华夏全球科技QDII A 限额变更：2,500元 → 1,000元` |
| Limit < daily DCA amount | 🔴 Critical | `限额500元，低于日定投150元！` |
| Suspended | 🔴 Emergency | `已暂停申购，定投将中断！` |
| Limit < 2× daily DCA | 🟡 Warning | `限额250元，接近日定投150元` |

**Monitored funds**: 005698 (华夏全球科技QDII A, 150元/日), 022979 (华夏中证A500ETF联接A, 150元/日)

**State persistence**: `~/.hermes/profiles/main/cron/state/dca_fund_limits.json`

### How to modify for another user

```python
# In monthly-portfolio-report.py, change these config sections:
CASH_POOL = {
    "code": {"name": "Fund Name", "amount": 200000},
}
DCA_FUNDS = {
    "code": {"name": "Fund Name", "daily": 150},
}
CASH_POOL_START = "2026-06-18"  # When cash pool starts earning
DCA_START_INVESTED = {"code": 1000}  # Initial DCA total as of report start date

# In monitor-dca-limits.py, change:
FUNDS = {
    "code": {"name": "Fund Name", "dca": 150},
}
```

## Cron job creation commands (for reference)

```bash
# Create monthly report
hermes cron create \
  --name "月末基金收益月报" \
  --schedule "30 20 26-31 * 1-5" \
  --script monthly-portfolio-report.py \
  --no-agent \
  --deliver weixin

# Create DCA limit monitor
hermes cron create \
  --name "定投基金申购限额监控" \
  --schedule "0 9,21 * * *" \
  --script monitor-dca-limits.py \
  --no-agent \
  --deliver weixin
```

## Related cron jobs on Omi's system

| Job | Schedule | Script/Agent | Deliver |
|---|---|---|---|
| DCA weekly report | Fri 22:00 | Agent (LLM, uses anysearch + a-stock-etf-analysis) | weixin |
| Monthly portfolio report | 26-31 weekdays 20:30 | Script (no_agent) | weixin |
| DCA limit monitor | Daily 9:00, 21:00 | Script (no_agent) | weixin |

## Pitfalls

- **QDII T+2 NAV delay**: On month-end, the latest available NAV for QDII funds may be 2 market days old. This is normal, not a data error. Report footer notes this.
- **Bond fund baseline on T+1**: Bond funds bought before 15:00 confirm next business day. If the purchase date falls on a Friday, the baseline won't establish until Monday.
- **DCA contribution estimation**: The script uses `days_since_check * 0.7` as a rough trading-day count. Actual count may vary slightly due to holidays. The error margin is small (<2% of total invested) — acceptable for a monthly overview.
- **Alipay screenshot vision**: Use `mmx vision describe` (via read-image skill) to extract DCA data from Alipay screenshots. The AA-type Alipay DCA page shows: fund name, cumulative amount, number of periods, next deduction plan, but NOT per-fund NAV, share count, or profit/loss. For those, need the 持仓详情 page instead.
- **delivery=weixin**: When creating cron jobs for Omi, use `deliver="weixin"` for fund-related notifications since the WeChat gateway is the primary notification channel.
