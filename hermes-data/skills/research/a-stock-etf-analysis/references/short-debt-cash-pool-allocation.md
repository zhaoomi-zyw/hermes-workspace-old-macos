# Short-Debt Cash Pool Allocation Pattern

Use when Omi asks about putting a large idle cash amount (e.g. 35–40万) into low-risk funds while also running equity/QDII DCA.

## Core pattern from prior session

Portfolio framing: **权益进攻 + 短债防守**.

- Keep equity exposure gradual via daily DCA rather than investing the whole lump sum at once.
- Use short-duration bond funds as a defensive cash pool and future buying power.
- Split the short-debt pool into a stable main sleeve and a flexible sleeve.

Example conclusion previously given for ~40万 context:

| Sleeve | Amount / method | Product example | Role |
|---|---:|---|---|
| Overseas tech DCA | 150元/日 | 华夏全球科技先锋混合 QDII A | AI / US-global tech growth exposure |
| A-share core DCA | 150元/日 | 华夏中证A500ETF联接A | Broad A-share core exposure |
| Stable short-debt main sleeve | 20万 | 001497 大成月添利一个月滚动持有中短债E | Defensive anchor, low volatility |
| Flexible cash sleeve | 15万 | 019112 恒越短债D or a larger-scale substitute | Emergency liquidity / dip-buying reserve |

## Critical: Lock-up type distinctions (Omi's explicit preference)

There are three distinct fund lock-up types in the Chinese market, and Omi has a clear preference ranking:

| Type | Name pattern | How it works | Omi's choice |
|---|---|---|---|
| **开放申赎** | No "持有期" or "滚动" in name | No lock-up; can redeem any business day (T+1 settlement) | ★最偏好 |
| **持有期** | "XX天持有期" (without "滚动") | Must hold X days, then free to redeem ANY business day afterward | ✅ 可接受 |
| **滚动持有** | "XX天滚动持有" or "XX个月滚动" | Each buy locks for ~X days; only redeemable at a specific window; auto-rolls if missed | ❌ 明确排斥 |

**Do NOT conflate these.** "30天滚动持有" does NOT mean "30天后随时可赎" — it means a rolling lockup with a narrow redemption window. Omi explicitly rejected rolling-holding funds in session 2026-06-15. When recommending substitutes, always ask about or respect this constraint first.

## Best-fit fund candidates (under Omi's constraints)

### 开放申赎 (no lockup — best fit for main sleeve)

| Code | Fund | Scale | 近1年 | Daily limit |
|---|---|---|---|---|
| 017314 | 国泰利享安益短债债券A | 23.68亿 | 1.72% | 500万/天 |
| 006932 | 平安0-3年期政策性金融债债券A | 0.62亿 | 3.51% | 开放 |

017314 is the top pick for large amounts: 23亿 scale means no liquidation risk, 500万/day limit means no purchase constraint, and open redemption means truly flexible.

### 7天持有期 (best fit for flexible/dry-powder sleeve)

| Code | Fund | Scale | 近1年 | Daily limit |
|---|---|---|---|---|
| 015875 | 汇添富中证同业存单AAA指数7天持有期 | 7.50亿 | 1.28% | 100万/天 |
| 019754 | 交银中证同业存单AAA指数7天持有期 | 1.10亿 | 1.08% | 100万/天 |

Rule: buy → hold 7 days → day 8 onward, free to redeem any business day. No rolling, no window constraint.

### 30天滚动持有 (rolling — Omi rejected, only use if explicitly accepted)

| Code | Fund | Scale | 近1年 | Daily limit |
|---|---|---|---|---|
| 016871 | 华富吉富30天滚动持有中短债A | 20.76亿 | 2.73% | 100万/天 |
| 001497 | 大成月添利一个月滚动持有中短债E | 0.74亿 | 3.43% | 1万/天 |

NOTE: 001497's E share has a 1万/day purchase limit — cannot fill 20万 in a single day.

## Purchase limit checking workflow

**Never recommend a fund without first checking its current purchase limit and lock-up type.** Use this approach:

```python
# Python check via pingzhongdata for name + returns
import requests, re, json
code = '001497'
txt = requests.get(f'https://fund.eastmoney.com/pingzhongdata/{code}.js', timeout=10).text
# Get lock-up type from name
name = re.search(r'var fS_name = "(.*?)";', txt).group(1)
has_rolling = '滚动' in name
has_lock = '持有' in name

# Get purchase limit from jjgg page
limtxt = requests.get(f'https://fundf10.eastmoney.com/jjgg_{code}.html', timeout=10).text
limit_match = re.search(r'单日累计购买上限[\d.]+万', limtxt)
```

Key regex patterns:
- Purchase limit: `单日累计购买上限([\d.]+)万`
- Fund name (from pingzhongdata): `var fS_name = "(.*?)";`
- Return data (from pingzhongdata): `var syl_1n="(.*?)";` (1-year), `var syl_3y="(.*?)";` (3-month)
- Scale data: `var Data_fluctuationScale = (.*?);` → parse JSON → get latest value
- Some funds show "开放申购" or "暂停申购" instead of a numerical limit → these are also valid states to check

## 019112 恒越短债债券D — specific caveats

- Only use as a flexible sleeve if liquidity is the top priority and amount is small (<5万).
- No lock-up; useful when Omi wants T+1-ish buying power for QDII/A-share dips.
- Important pitfall: the D share class was very small (~0.28亿 as of 2026Q1), which increases fund-size / liquidation / operational disruption risk.
- Do not present it as a pure safety pick without mentioning size risk.
- Near 1-year 5.98% is attractive but misleading — the 3-month return dropped to 0.33% (1-month 0.05%), suggesting the high yield period has passed.

## Yield / Risk ladder (within no-rolling-lockup constraint)

When Omi asks "更激进" or "更高收益" within the no-rolling-lockup preference, present this ladder. Higher yield = longer duration / more credit risk = more NAV fluctuation.

| Tier | Type | Representative fund | 近1年 | 近3月 | Scale | Key risk |
|---|---:|---|---:|---|---|
| ① 同业存单 | 7天持有期 | 015875 汇添富同业存单AAA | 1.28% | 0.34% | 7.5亿 | 收益最低，几乎无波动 |
| ② 基础短债 | 开放申赎 | 017314 国泰利享安益短债A | 1.72% | 0.40% | 23.68亿 | 偶尔单日微跌 |
| ③ 中短债增强 | 开放申赎 | **019872 长城短债D** | **2.49%** | **0.81%** | **256亿** | 信用下沉+短久期，最平衡 |
| ④ 纯债升级 | 开放申赎 | **020080 华富恒稳纯债D** | **2.88%** | **1.38%** | 17.53亿 | 长债，利率波动敏感 |
| ⑤ 长债高收益 | 开放申赎 | **675100 西部利得得尊纯债A** | **4.54%** | 0.43% | 19.64亿 | 近1月-0.24%, 真会跌 |
| ⑥ 信用债高收益 | 开放申赎 | 550018 中信保诚优质纯债A | 6.78% | 1.48% | 1.33亿 | 规模小，近1月-0.57% |

### Key insight for "more aggressive" requests

When Omi asks for higher yield under no-lockup constraint, the path is:
- 短债(②③) → 纯债/长债(④⑤): same open-redemption liquidity, higher coupon, but longer duration means NAV drops when rates rise
- The practical cap for comfortable holding is tier ④ (~2.88%): still positive nearly every month, occasional small dips
- Tier ⑤+: 1-month negative returns are normal; only use if Omi explicitly accepts this and for smaller allocation (<15万)

### 长城短债D (019872) — top balanced pick

| Metric | Value |
|---|---|
| 近1年 | 2.49% |
| 近3月 | 0.81% |
| Scale | **256亿** (very safe) |
| Daily limit | 100万/天 ✅ |
| Type | 中短债, 开放申赎 ✅ |
| Lockup | None ✅ |
| Fee | 0.03% (1折) |

Best combination of yield, scale, liquidity, and purchase limit for a 20-30万 cash pool allocation. Use as the default "first pick" when Omi wants better than 1.5% but doesn't want rolling lockup.

### Purchase limit landmines — always check before recommending

Several funds that LOOK good (large scale, good yield) have tiny daily purchase limits making them impractical for 20+万 allocation:

| Fund | Scale | 近1年 | Daily limit | Verdict |
|---|---|---|---|---|
| 485119 工银信用纯债A | 112亿 | 2.75% | **100元/天** | ❌ 3500天才能建完仓 |
| 206015 鹏华纯债D | 1.35亿 | 4.35% | **1万/天** | ⚠️ 仅适合小额 |
| 001497 大成月添利E | 0.74亿 | 3.43% | **1万/天** | ⚠️ 需20天建20万 |

Always check purchase limit on `https://fundf10.eastmoney.com/jjgg_{code}.html` using regex `单日累计购买上限([\d.]+)万` before recommending any fund for large allocations.

## Sample allocations (2026-06-15 session, 35万, Omi prefers no rolling lockup)

### Conservative: tier ②+①

| Amount | Fund | Code | Type | Rationale |
|---|---:|---|---|---|
| 20万 | 国泰利享安益短债债券A | 017314 | 开放申赎 | 主力现金池，23亿规模，无锁定 |
| 10万 | 汇添富中证同业存单AAA指数7天持有期 | 015875 | 7天持有期 | 真正备用弹药，7天后随时可用 |
| 5万 | 货币基金/余额宝 | — | 开放 | 日常流动性 |
| **综合年化~1.5-1.8%, 年收益 ~5,250-6,300元** |

All positions fillable in one day (no daily limit bottleneck), no rolling lockup.

### Balanced: tiers ③+① (recommended)

| Amount | Fund | Code | 近1年 |
|---|---:|---|---|
| 25万 | 长城短债D | 019872 | 2.49% |
| 10万 | 汇添富同业存单AAA 7天 | 015875 | 1.28% |
| **综合年化~2.1%, 年收益~7,500元, 月均~625元** |

### Aggressive: tiers ④+③+①

| Amount | Fund | Code | 近1年 |
|---|---:|---|---|
| 20万 | 华富恒稳纯债D | 020080 | 2.88% |
| 10万 | 长城短债D | 019872 | 2.49% |
| 5万 | 汇添富同业存单AAA 7天 | 015875 | 1.28% |
| **综合年化~2.5%, 年收益~8,750元, 月均~730元** |

### Very aggressive: tiers ⑤+③+①

| Amount | Fund | Code | 近1年 |
|---|---:|---|---|
| 15万 | 西部利得得尊纯债A | 675100 | **4.54%** |
| 15万 | 长城短债D | 019872 | 2.49% |
| 5万 | 汇添富同业存单AAA 7天 | 015875 | 1.28% |
| **综合年化~3.1%, 年收益~10,850元, 月均~904元** |

⚠️ Tier ⑤ funds really do have negative months — 675100 showed 近1月 -0.24%. Only recommend if Omi explicitly asks for "更激进" and accepts short-term NAV dips.

## Response style for resurfacing old conclusions

When Omi asks "之前你推荐的配比再发我下":

1. Use `session_search` first; do not reconstruct from memory alone.
2. If the exact prior session is found, resend the conclusion in a clean, concise table plus one-line rationale.
3. Preserve the original recommendation, but add any risk caveat that was raised later in the same session (e.g. 019112 size risk, purchase limit changes).
4. Avoid re-running a fresh market analysis unless Omi asks for an update; label the answer as "之前结论复述/整理".

## Caveats

- Short-debt fund returns are not deposits; NAV can fluctuate.
- Always check current fund scale, purchase status, fees, holding period, and latest quarterly report before making a new recommendation.
- Purchase limits change frequently — a fund that was "open" last month may now be "限大额" or "暂停申购".
- If the plan includes QDII DCA, check QDII subscription limit/status before assuming the DCA can execute.
- Fund names alone are not sufficient to determine lock-up type — read the holding-period section on the fund page for each specific share class.
