# Omi's Monitored Funds

## 摩根纳斯达克100指数 QDII 人民币A

- **Code**: 019172
- **Manager**: 摩根基金管理（中国）有限公司
- **Type**: 指数型-海外股票 (NASDAQ-100 tracking)
- **Cron Job**: `5315b4da1199` (daily 9:00 + 21:00)
- **Script**: `~/.hermes/profiles/main/scripts/monitor-nasdaq-limit.py`
- **State File**: `~/.hermes/profiles/main/cron/state/nasdaq_limit.json`
- **Current Limit**: 10 RMB/day (as of 2026-06-12) 🔴
- **Omi's Daily Investment**: 100 RMB/day (BLOCKED — 10x the limit)

### Limit Change History

| Date | Limit | Direction |
|------|-------|-----------|
| 2026-04-27 | 100元 | 下调 (from higher amount) |
| 2026-06-05 | 100元 | baseline established |
| 2026-06-12 | 10元 | 🔴 骤降至10元，定投100元完全无法执行 |

### Page Scraped

`https://fundf10.eastmoney.com/jjgg_019172.html`

Key field: `单日累计购买上限XXX元`
