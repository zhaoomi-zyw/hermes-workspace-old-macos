---
name: fund-position-analysis
description: Analyze a held QDII/mutual-fund 定投 position.
---

# Fund / QDII 定投 Position Analysis

Analyze a mutual-fund or QDII position Omi already holds via 定投 (daily auto-invest). The goal is an honest, data-backed answer to "现在亏多少、继续定投多久能摊薄回本、该持有还是止损" — NOT to market a fund.

## When to use
- Omi sends a fund-holding screenshot (蚂蚁/同花顺) or asks "继续定投多久回本"
- Any "摊薄回本测算" / "这个QDII值不值得持" question
- Compare a held QDII against alternatives (纳指100指数 vs 主动全球科技)

## ⭐ 铁律一：QDII 的净值结算与「今日收益」
QDII 净值日期 T 用的是 **T 日美东收盘**（= 北京时间 T+1 凌晨），**T+1 日才公布**。
- 用户 T 日晚上看到的"今日收益" = T 日净值 = **前一晚/今晨**那段美股 → **永远滞后一晚**；今晚正在走的美股，明天才进收益。
- ⚠️ **下单方向相反**：T 日 15:00 前下单，买到的是**今晚**的价（T 日美东收盘）。想吃到今晚的涨，必须 15:00 前动手。
- 验证滞后最省事的办法：看**最新净值日期是否 < 今天**（如 9/17 21:47 最新仍是 9/16 净值 → 滞后成立）。
- 别一律套公式：纯美股 QDII 多为 T+2 确认，港股/A股占比高的可能 T+1。

## ⭐ 铁律二：推荐/加仓/换任何基金前，先查「能不能买」
**只看收益和费率就下结论是错的** —— QDII 额度紧张会随时暂停申购。**必查三项**：
1. 申购状态（开放申购 / 限大额 / **暂停申购**）
2. **日累计申购限额** —— 必须 ≥ 用户的定投金额；**正好等于**＝卡边界，随时可能失败
3. **定投状态**（支持 / 不支持）+ 定投起点
```python
h = get(f"https://fundf10.eastmoney.com/jjfl_{code}.html")
t = re.sub(r"<[^>]+>", " ", re.sub(r"<script.*?</script>", "", h, flags=re.S))   # ⚠️ 必须先剥 script
t = re.sub(r"&nbsp;", " ", t); t = re.sub(r"\s+", " ", t)
m   = re.search(r"交易状态\s*申购状态\s*(\S+)\s*赎回状态\s*(\S+)\s*定投状态\s*(\S+)", t)
lim = re.search(r"日累计申购限额\s*([\d.]+元|无限额)", t)
```
⚠️ **不剥 `<script>` 会命中导航栏里的"申购状态"链接，解析出一堆菜单文本** —— 看着像成功，其实是垃圾。自检：结果里必须出现「限大额/暂停申购/开放申购」之一 **＋** 一个具体数字。
**实例（2026-09-18，收益/费率完全看不出来）**：天弘纳斯达克100A `018043` = **暂停申购 + 定投不支持 + 限额100元**，而用户正挂着 **100元/日** 天弘定投 → 下一扣款日会失败；宝盈 `019736` = 限大额 **200元**，用户定投正好 **200元** → 卡在边界；华夏全球科技 `005698` = 限大额 5000元 → 安全。

## 基金代码搜索（名称 → 代码）
```python
u = "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx?callback=cb&m=1&key=" + quote(name)
# 返回 cb({...}) → Datas[].CODE / NAME / CATEGORYDESC / FundBaseInfo.FTYPE
```
一次能拿到 A/C/美元份额全家族（宝盈 019736/019737/019738/019739），**认准「人民币 A」份额**。

## 同指数多只基金怎么比较（纳指100 这类）
同一指数的两只基金**长期收益必然接近** —— 差 0.3pp/年 是**跟踪误差，不是能力**。**不要用「成立以来收益」比高低**：成立日期差一年就会造出 +99% vs +46% 的假差距。
真正有决策价值的比较顺序：
1. **能不能买**（申购状态 / 限额 / 定投状态）← 决定性的一项
2. 费率（管理费 + 托管费 + 申购费折后）—— 同指数基金通常合计差 <0.1%/年，**可忽略**
3. 规模（大者清盘风险低）
4. 成立时长 / 经理任期（可参考，别当收益依据）
**结论模板**：两只本质是同一只产品，差异在细节；**若一只已暂停申购，「费率更低」没有任何意义。**

## 定投组合体检（收到「我的定投」截图必做）
把每只映射到**底层暴露**，而不是看基金名字：
- 纳指100 联接 / 纳指100 指数 / 主动全球科技 = **同一风险因子（美股科技）**
- **同指数买两只 ＝ 常见且合理的做法**（QDII 限额紧张时用多只突破单只限额），但要明确告知：**任一只扣款失败，实际投入立刻下降**
**必查四项**：① 是否 100% 单因子（无 A股/债/黄金）② 有没有「已暂停」的定投被忽略 ③ 每只限额 vs 定投额 ④ 有没有基金**没被限额监控脚本覆盖**（脚本清单见 `references/qdii-and-dca-fund-mechanics.md`）
⚠️ 若用户 A股 仓位很低（如 32%）+ 大量现金，而定投端却是 100% 美股科技 → **两头都是极端，必须同时讲**。

## Get fund NAV (the working endpoint — eastmoney pingzhongdata)
`akshare` has no clean single-call NAV history; the reliable free source is eastmoney's JS bundle:
```python
import urllib.request, json, re, datetime
def fetch_nav(code):
    url = f"https://fund.eastmoney.com/pingzhongdata/{code}.js?v={int(datetime.datetime.now().timestamp())}"
    req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0","Referer":"https://fund.eastmoney.com/"})
    js = urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
    m = re.search(r"Data_netWorthTrend = (\[.*?\]);", js, re.DOTALL)
    return json.loads(m.group(1)) if m else None
# each item: {"x": ms_timestamp, "y": 单位净值, "equityReturn": 日涨跌%}
```
- Filter out None `y` (suspension days). 1年前 = `navs[-250]`, 90天前 = `navs[-90]`.
- This also reveals recent drawdown shape (e.g. 005698 8/18 -3.6%, 8/19 -5.9%, 8/24 -4.0% = global-tech selloff driver).

## Compute the user's real numbers from a holding screenshot
A holding screenshot gives: 持仓市值, 累计盈亏, 持有天数, 收益率.
```python
holding_value = 7329.13; loss = 1320.87; nav_now = 2.6190
total_invested = holding_value + loss        # 累计投入 ≈ 市值+已亏
shares = holding_value / nav_now             # 份额
avg_cost = total_invested / shares           # 平均成本（需净值回升到这才回本）
```
**Key honesty check**: 平均成本 vs 最新净值 tells you how deep underwater the *average* dollar is. For 005698 (2026-08): avg_cost 3.09 vs nav 2.62 → the average buy was at a 2.8-3.0 price zone, now -18%. A high avg_cost is the real problem, not "the fund is bad".

## 摊薄回本 projection — be HONEST about small DCA
Daily 定投 of ¥150 against a large existing share count barely moves the average cost. Project it rather than hand-waving:
```python
def project(nav_flat, daily, shares, avg_cost, days=500):
    sh, cost = shares, avg_cost
    for d in range(1, days+1):
        sh += daily / nav_flat
        cost = (cost*(sh - daily/nav_flat) + daily) / sh
        if cost <= nav_flat: return d
    return None  # not reached in `days`
```
Scenarios to run: NAV flat / NAV back to 90d-ago level / NAV +15%. **Expect the honest result**: with a large existing position and ¥150/day, breakeven-by-DCA alone usually takes 300-500+ days or never converges — the average cost barely moves. The durable conclusion to give Omi: **回本主要靠净值反弹到平均成本，不靠小额定投摊薄；决定持有与否看净值能否回到平均成本（看重仓方向/美股AI能否企稳），不看每天摊多少。**

## Decision framing for Omi (data-backed, both sides)
- Give the honest "X天无法摊薄回本" numbers — don't sell false hope.
- Then frame the real decision: 看好多重仓方向(如美股AI)长期 → 持有+小额定投等净值反弹，别期待快速回本；悲观或需资金 → 择反弹止损，别坑底割。
- Respect Omi's already-decided constraints (e.g. 005698 previously confirmed "不建议坑底割肉转走"); reconfirm, don't relitigate every time.
- Omi is price/value sensitive → always give a number, never just qualitative.

## QDII fund-alternative lookup (when asked "有没有别的美股AI基金")
Use anysearch (news) — key facts that recur (2026):
- QDII quota is tight: >60% of QDII tranches suspended or severely limited subscriptions; popular 纳指100 funds cap at ¥10-100/day (摩根/华安 10, 南方 50, 易方达 100).
- Held-005698-alternatives: 易方达全球成长精选(QDII)A (近3年+314%, AI purest), 国富全球科技互联006373 (美股72%/信息技术79%, 偏半导体硬件 — differs from 005698's holdings), 建信纳指100 012752.
- **Rule**: don't push a new QDII if Omi already holds one with the same AI exposure — it's duplication, plus quota-limits make new buys impractical.

## ⭐ 铁律三：watchdog 对「持续异常」是静默的 → 必须配快照脚本
限额监控是**变化才推**的 watchdog。**首次登记会推一次**，此后若问题**一直存在**（如某基金长期暂停申购）→ **再也不会提醒**，而 cron status 仍显示 ok。

**正解：两个脚本分工**
- `monitor-dca-limits.py` — watchdog：**状态变化**才推（cron `0 7,21 * * *`，`no_agent=True` 脚本直推、不经 LLM）
- `dca-status-snapshot.py` — 快照：**每次运行都输出全部状态**，用于「某个特定日期到底能不能投」的确认

→ **凡是有「用户要在某天做决定」的场景，都不要指望 watchdog，要挂一个一次性快照 cron。**
（实例 2026-09-18：用户说「天弘下周一不让投我就关掉定投」→ 挂 9/21 08:00 一次性快照，明确输出「🔴 今天投不了，建议关闭定投」或「✅ 可以正常投」。）

**判定规则**（限额 vs 用户日定投额）：
- 限额 **< 你的定投额** → 🔴 会被拒
- 限额 **== 你的定投额** → 🟠 卡边界，一旦下调即失败
- 暂停申购 / 定投不支持 → 🔴 立即失败

**数据源**：`https://fundf10.eastmoney.com/jjfl_{code}.html`
正则：`申购状态\s*(\S+?)\s*赎回状态\s*(\S+?)\s*定投状态\s*(\S+)` + `日累计申购限额\s*([\d.]+)\s*元`

**QDII 特别提示**：额度紧张时基金公司会随时「暂停申购/下调限额」，**纳指/标普类基金尤其频繁**。
→ 用户历史行为：**同时定投多只同指数基金（天弘+宝盈），用不同限额叠加突破单只上限**。

**监控脚本实况（2026-09-18 重写后，备份 `.bak_20260918`）**：`monitor-dca-limits.py` 现同时判定 **申购状态 + 定投状态 + 日限额** 三项，盯 `018043` + `005698` + `019736` 三只。
- 旧版盯 `005698` + `022979` + `016453`（**已过时** —— 那三只都不是当前在投的）
- 另存两个陈旧脚本：`monitor-tianhong-nasdaq-limit.py`(018043)、`monitor-nasdaq-limit.py`(**摩根 019172 —— 不是用户的宝盈**)
- 用户历史上为绕 QDII 限额**换过多只纳指100基金**（天弘/宝盈/南方016453/摩根019172），所以**脚本盯的代码 ≠ 用户实际在投的代码**，必须定期核对。

### 🐛 漏报根因（2026-09-18 实战踩到，务必牢记）

**症状**：天弘 018043 于 **2026-09-18** 发布「暂停申购及定投」公告，但用户**没收到任何监控提醒**。

**根因（两层）**：
1. **旧脚本只比对「日限额数字」**（正则 `单日累计购买上限(\d+)元`）
   → 暂停申购时该字段**仍是 100** → 判定"无变化" → **永远静默**
   → **申购状态/定投状态这两个决定性字段根本没读**
2. **只按"数字变化"去重** → 状态类变化（开放→限大额→暂停）**全部漏报**

**✅ 正确设计 = 按「问题指纹」去重**：
```python
fingerprint = "|".join(sorted(problems)) if problems else "OK"
if problems and fingerprint != prev_fp:   # 同一问题只推一次
    alert(...)
elif not problems and prev_fp not in (None, "OK"):
    alert("✅ 问题已解除")                 # 问题消失后再出现则重推
```
- 覆盖 **申购状态 + 定投状态 + 日限额** 三项（缺一不可）
- **不要**用"限额数字相等"当无事发生的依据

**天弘 018043 申购状态时间线（实证）**：
| 日期 | 事件 |
|---|---|
| 2026-05-29 | 暂停申购及定投 |
| 2026-09-01 | **恢复**申购及定投 + 限大额（单个账户单日≤100元）|
| **2026-09-18** | **再次暂停申购及定投**（公告 09-18 09:09）|

**⚠️ QDII 额度紧张时状态可能十几天一变** → 监控必须能捕捉"状态"而非仅"数字"。
**公告查询**：`https://api.fund.eastmoney.com/f10/JJGG?callback=cb&fundcode=<code>&pageIndex=1&pageSize=20&type=0`
