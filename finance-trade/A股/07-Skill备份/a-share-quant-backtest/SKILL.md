---
name: a-share-quant-backtest
description: Backtest and validate A-share strategies end-to-end — multi-source data (hithink/腾讯/akshare/baostock), minute-level verification, isolation and invariant checks.
---

# A-share Quantitative Backtest

Turn an A-share trading thesis into a validated, backtestable strategy engine. Bridges Omi's DSA (Daily Stock Analysis) methodology into executable rules, runs them on historical data, and avoids the classic traps (future-function bugs, overfitting, entry/exit period mismatch).

- 🧾 `references/trade-recording-and-state-safety.md`（状态文件禁加字段/部分卖出成本/触发差口）

- 🧩 **策略参数只留一份，但给历史留一把「冻结钥匙」**: `references/policy-module-live-backtest-coupling.md`。生产脚本与回测引擎同读一个策略模块时，**绝不要**把弃用的门槛参数改成 `None`/`inf`/删除来关掉它——引擎 import 时读值，改动＝静默重写历史收益。正确姿势: 数值原样保留 + 模式开关（`SIZING_MODE="manual"|"auto"`）+ `FROZEN_AUTO_CONFIG` 冻结快照并注明「仅供复现，禁改」。同文件另收: ① **一个「限制」住在三层（计算/阻断/通知文案），删一层等于没删**，验收必须是「提醒文本不含被删字段名」的断言；② **行为等价重构的验收＝逐位复现**（逐 scenario 数值差 ≤1e-9 且差异项为 0，并回查冻结值仍在输出里）；③ 残余文案 grep 会因**你自己的禁止句**假阳性，必须打印上下文分类；④ 用未来日期打桩会因缺分钟数据全程不出信号，基准要用有数据的真实交易日；⑤ 回执须区分已实现/已验证/已应用/阻塞，**数量假设一变旧回测收益不得充当新策略业绩**。
- 🧪 **改「门槛」前先用确定性 dry-run 自证**: `templates/strategy_dryrun_harness.py` 可直接抄。要点: 行情**打桩**（实时源限流/不确定会把测试变成噪声）；状态文件强制指向临时目录——⚠️ `def save_state(st, path=STATE_FILE)` 的默认参数在 **def 时**绑定，改 `module.STATE_FILE` 无效，必须包一层 `lambda st, path=None: orig(st, path or TMP)`，否则「dry-run」会写进真实状态文件；测试矩阵必含「现金=0 / 净资产未知（loader 抛错）/ 超风险上限 / 不足一手 **全部仍出信号**」与「条件不满足 / 非时段 / 周末 / 行情无效 **必须静默**」。生产代码也要对 `load_account()` 这类调用做防御，否则账户不可读会直接崩掉监控。

- 🧪 **自建分钟级回测引擎前先读正确性契约**: `references/minute-level-engine-contract.md` —— 11 类已修缺陷，三条最致命的是「T+1 只阻成交不阻触发」、「不得用当前 bar 的最终 low/volume 判定该 bar 开盘是否成交」、「可执行性要用 bar 窗口起点而非结束时刻」；另含真实有效期、O-H-L-C 双路径、估值回退禁用量收。动手前必读。
- 💰 **回测资金账本三道自检，漏一道就静默失真**: `references/backtest-cash-ledger-selfchecks.md`（探针必须纯计算 / 费用守恒精确到分 / 现金对账用实际现金流字段；含「日循环持现金忘了写回 → 每笔买入都免费」的实例）。
- 📊 **「只改一条规则」的 A/B 对照必须守纪律**: `references/rule-isolation-ab-experiments.md`。核心: 新增约束一律写成 `min(原规则, 新规则)` 以保证**永不放宽基准**；**如实报告组间等价**（本次 0.1%/0.2% 追价上限因「原限价已是 ceil 到分」几乎不生效；1%/2% 档下 `C ≡ D_cap0.1 ≡ D_cap0.2` 交易序列完全一致 —— 公式使然，绝不可为了制造差异去动基准）；所有臂共用**同一费用模型**，新费率数据不得悄悄混入基准；**先过基线复现门槛**（旧版期末权益/平仓笔数/费用逐项一致）再跑臂；被取代的版本归档 `*_superseded/` 并写缺陷 README；上限/延迟挡掉的成交机会只能记**反事实计数**，不得当成已实现收益。
- 🛰️ **A 股多年 5 分钟数据首选 baostock**: 东财/新浪的分钟接口只回传最近约 32~42 个交易日（1 分钟仅约 9 天），**baostock 匿名登录即可拿到三年以上、48 根/日**的 5 分钟数据，是分钟级验证的现实可用源。可直接复跑的可用性探针 + 取数配方: `scripts/probe_minute_data_sources.py`。
- 📉 **小账户 100 股整手 × 风险预算是强耦合，别当成「同样的交易更小仓」**: 单笔可承受名义市值 ≈ 净资产 × 单笔风险% ÷ 止损%；13,822 元账户配 -6% 止损时，2% 档上限约 4,607 元（≈46 元/股），**1% 档降到约 2,304 元（≈23 元/股）**，高价股直接买不到一手（本次平仓笔数 121 → 58，回撤同时由 -22% 收窄到 -12%）。另: 万 2.5 但**每笔最低 5 元**的佣金在小账户上会被高频换手放大成决定性拖累（本次手续费占初始资金约 10%）。

- ⛔ **选股/剔除/调参决策的证据一致性检查（2026-09-15 同日两次犯同类错误）**: 做任何「剔除某标的 / 优选某子集 / 改某参数」的决定前，先问一句 **「我正要用的这类证据，是不是我刚宣布过不可靠的那一类？」** —— 本次先论证「样本外 Top6/Bottom6 区分度弱 ⇒ 事前选池无增益」，转头就用**全窗样本内单股回测**（星网 −6.66% / 易德龙 −4.16%）把两只剔了，**自相矛盾，已撤回**。**剔除只允许基于 ① 实盘已发生的事实（反复止损）② 基本面/结构性问题（业务恶化、长期破位、流动性差）**；**禁止**用样本内回测数字（单股收益/盈亏比/胜率）当依据。另：`per_stock.csv` 是**单股独立满仓**结果，与组合回测**不可互换**（忽略资金争用与轮动）；**持仓中的标的不要标「暂停交易」**（会被读成「要不要卖」，本次用户即因此发问）。完整清单 + 证据分级（E1实盘事实 > E2基本面 > E3样本外 > E4样本内-仅研究）见 `references/selection-decision-discipline.md`。
- 🚨 **动任何策略分析前先核验口径（2026-09-15 踩坑，代价=整轮分析作废）**: 见 `references/spec-version-and-backtest-integrity.md` —— **必须读权威模块的 `POLICY_VERSION`，不得从脚本里扒遗留函数当规则**（本次误把 `lowbuy-watch.py` 里的 `dsa_score` 当作线上买入条件，而线上早已换成 BUY-LOW-v1 三条件且**DSA 门槛被移除**）；买入只认 `strategies/buy_policy.py`、卖出只认 `strategies/sell_policy.py`。含回测完整性陷阱（未来函数 `hi[-11:-1]`、日内顺序「先判止损再更新H」、印花税 2023-08-28 起 0.05%、**别重写引擎**——`results/confirmed_policy_3y_20260914/` 已忠实实现 BUY-LOW-v1 且支持传自定义池子）与统计铁律（n<15 不作依据、样本敏感性检验、切点区分度、事后 vs 事前、换 K 值翻转=噪声）。
- ⭐ **把已确认的买卖规则落地成生产模块 + cron**: 见 `references/policy-module-rollout-playbook.md` —— 唯一权威模块模式(纯函数+状态机+`--test`)、**净资产口径=现金+持仓市值**(不是现金)、`sizing()` 资金分档(资金不足**不得拦截提醒**、warnings 而非 BLOCKED、`strict=True` 可选)、cron 提示词必须写**禁止项**否则 LLM 会混用旧口径、残留检查要逐条看上下文(禁止性表述会命中关键词)、要主动找**与已确认策略矛盾**的旧逻辑(如「跌破MA60→卖出」违反 SELL-POLICY 规则⑤)、本仓库 **非 git** 改动前必须手动备份、回执须分 已实现/已验证/已应用/阻塞、**遗留门槛要么删要么在回执里当场解释清楚**(只降级为 warning 不算解决)、**同刻缩量必须同源对齐且单位实测**(新浪5min=股/腾讯日K=手)。
- ⭐ **成本/费率/执行延迟的证据检索**: 见 `references/cost-calibration-evidence-hunt.md` —— 证据分布(状态文件/笔记/trade_journal._meta/附件截图/cron输出/gateway.log)、**成交明细页≠交割单**(同花顺历史成交无任何费用字段)、**成本−成交价≠佣金**(分红污染)、样本全落最低费档**不可反推比例费率**、执行延迟=提醒发送(文件时间戳)→成交时间、账号标识须遮盖。
- ⭐ **回测引擎参数单一来源 + 行为等价回归**: 见 `references/engine-param-single-sourcing.md` —— 先侦察再动手（任务书里的"引擎需要支持 X"常是作者推断，本次 v4 本已忠实实现全部条款）、参数/费率从策略模块取值且派生列表**生成**而非另抄、⚠️**patch 会静默吃掉 old_string 之外的结构**（本会话踏三次：吞掉小节标题、删掉 STOCKS/BACKTEST_START/ALLOWED_TIMES，lint 不报错）、行为等价必须用**逐位回归**证明（14 场景差异=0 才能说"未变"）、未校准项写进 `summary.json.assumptions` 而不只写在报告里、同行不同买入口径的两份回测**不可比**。

- ⭐ **选股与股票池管理（2026-09-15：A1-A5 + B1/B2 + ATR 裁决，全部已批准落地）**: 见 `references/stock-pool-management.md` —— 交易权限(仅主板+创业板)/**入池资格只剩 3 条**(业务与驱动可述 + 主板或创业板 + 不与现有池同风险簇)/**建仓条件**(一手≤单股上限40%净值)/三层池/紫光暂停/分组修正(黄金 vs 工业金属)/赤峰止损42.26。**阈值只管池子准入，不接入信号链路、不得压制四条件信号**。
- ⭐⭐ **设计任何「入池门槛 / 过滤条件 / 仓位约束」之前必读** `references/threshold-design-and-validation.md` —— ①三类东西必须分清(**入池资格** vs **建仓条件** vs **风险标注字段**；把账户约束写成入池门槛是本会话最大的错) ②四道检验:**样本敏感性**(同一相关性换 n 重算: ATR↔赔率 -0.237@n≥15 → -0.089@n≥8 = 小样本假象)/**切点区分度**/**组合逻辑**(逐只判相关性会让整簇互踢)/**排序并列 n** ③「高波动≠差，止损/ATR 不匹配才差」。文末有**被否假设登记表(六个)** —— 勿重复提。
- ⛔ **入池五标准实测有 2 个设计缺陷（2026-09-15 A6 评估暴露，现有池 0/12 合格）**: ①「一手≤净资产25%」是**建仓**约束而非**入池**约束（小账户等价股价≤34.67，把亨通赔率3.01/趋势最干净这种最优标的砍掉）；②「相关性<0.6」令**整个风险簇互相踢出**（亨通↔中天0.84→光通信组全灭），应改「同簇择一保留最优」。**修正案 B1/B2 获批前不得用该五标准删股。** 详见 `references/stock-pool-management.md` §9。
- ⛔ **样本量诚实审查（与赔率排序强绑定）**: 任何「赔率/胜率」排序**必须并列样本数 n**；**n<8 不计算不展示赔率、绝不排序**（2026-09-15 实测：`中航西飞(2信号,赔率84.24)`、`中直股份(1信号,赔率21.55)` 按赔率排会排第一 —— 那是 1-2 个样本的产物，不是规律）。n<15 只作参考并标「偏少」。**只给比率不给 n = 误导。** 另：候选(腾讯800根≈3.2年) vs 现有池(1212根≈5年) **口径不同，不得直接横比**。

- ⛔⛔ **任何「选池 / 择优 / 增删标的」方案上线前必须过样本外检验 —— 2026-09-15 实测：事前选池零增益，我的候选池方案被数据推翻**。完整证据链（含三轮阈值迭代、ATR 切点检验、逐股归因、回测 bug）: `references/pool-selection-out-of-sample-verdict-2026-09.md`。
  - **决定性实测（前段 2021-09~2024-02 选池 → 后段 2024-03~2026-09 验证）**: 「不挑=全池12只」后段 **+50.3%**；「前期收益 Top6」**−8.9%**（甚至输给 Bottom6 的 +4.4%）；「前期穿越最少 Top6」+10.9% 但 **Top9 −15.8%**；「前期低波动 Top6」+69.3% 但 **Top9 −8.4%** → **换个 K 值结论就翻转 = 噪声**。我的「候选池7只」3年净 **−796元**（全方案最差），样本外 −4.2%。
  - **根因**: 单股 3 年只有 11-39 笔交易 → 样本太小；赔率↔单股净盈亏 r=+0.583 但 **R² 仅 0.34** → 选择噪声淹没信号。逐股反例：**南山铝业赔率 1.27（倒数第3）却是回测第1（+12,903）**；中航沈飞赔率 1.97（中上）却亏 −1,589。
  - **铁律**: ①**不得用与回测同一段数据挑池**（选择偏差）②**结构性指标（MA60穿越 / ATR）也不行**，已实测 ③只允许「**排除式**」（排除基本面恶化/长期破位/流动性差），**禁止「优选式」排序删股** ④赔率只能作**辅助标注**，不得作删股依据 ⑤**样本外不占优 = 不上线**，哪怕样本内很漂亮 ⑥**换参数结论就翻转 = 噪声**，上线门槛是「对参数不敏感」。

---

## ⭐ 因子/信号有效性验证（做之前必读）

**先读 `references/factor-validation-methodology.md`** —— 截面IC vs 时序IC、必须中性化、跨样本复现、事件研究、2026-09-19 实测结论。

---

## 📚 详细章节索引（已迁移到 references/，需要时按名查阅）

> 🧹 **2026-09-19 精简记录**：SKILL.md 原 105,949 字符 / 169,602 字节，超出 100,000 字符上限导致**无法再修改**。
> 已将 52 个非高频章节整体迁出 → `references/skill-migrated-sections-2026-09.md`（**内容一字未删**）。
> 同时去重：3 个同主题因子文件移入 `references/_superseded_20260919/`（**可恢复**）。
> 备份：`SKILL.md.bak_20260919_pre_slim`（原文件完整保留）。

**回测引擎与验证**
- ⭐ 四条件低吸 + SELL-POLICY-v1.0 三年回测（2026-09-15 已跑完，含 21 项不变式校验）  `(#2)`
- ⛔ 两个只在四条件回测里暴露的引擎缺陷（基础引擎 v4 也有，改前先读）  `(#3)`
- ⛔ DSA 实现唯一来源（2026-09-15 写错权重的教训）  `(#4)`
- ⛔ 改参数前先确认「运行时读什么」（2026-09-15，差点误报线上错误）  `(#5)`
- ★ 策略复盘方法论 + 回测≠实盘 (2026-09-11 首次完整复盘) ★  `(#8)`
- ★ 三年分钟级隔离验证 (2026-09-14) — 数据源 / 引擎坑 / 不变式校验 ★  `(#10)`
- ★★ 回测引擎正确性审查清单 (2026-09-15 独立审阅暴露 12 类缺陷 — 新引擎先过这张表) ★★  `(#11)`
- 第二轮复核 (v3 → v4) — 三条建模语义错, 比代码 bug 更隐蔽  `(#12)`
- ⚠️ 归因纪律: 没有消融就不许说「是 X 导致亏损」(本次两次自我打脸)  `(#13)`
- 交付口径(用户明确要求)  `(#14)`
- IC 评估层 (ic_eval.py) — 验证 DSA 信号是否有真实预测力 (2026-08-30)  `(#26)`
- 遗传规划参数进化 (evolve_params.py) — 样本外验证防过拟合 (2026-08-30)  `(#28)`

**数据源与接口**
- akshare data source — CRITICAL quirks (learned the hard way)  `(#16)`
- Tencent realtime quote endpoint (for intraday prices)  `(#21)`
- per line: v_sh601899="1~紫金矿业~601899~33.18~32.53~33.33~..."  `(#22)`
- fields: f[1]=name f[3]=现价 f[4]=昨收 f[5]=今开 f[30]=时间 f[31]=涨跌额  `(#23)`
- f[32]=涨跌幅% f[33]=最高 f[34]=最低 f[36]=成交量 f[37]=成交额(万)  `(#24)`
- Tencent fqkline response-shape gotcha (2026-09-04 — burned 3 fetches)  `(#25)`
- Stock-monitor cron MUST use Tencent quotes, NOT anysearch (2026-08-27)  `(#52)`
- 模型名规范化 + "配置改了但没生效" 的验证法 (2026-09-11)  `(#59)`
- Official 同花顺 data API (hithink-finance CLI) — additional data source (2026-09-06)  `(#66)`

**DSA 与信号研究**
- DSA 评分逐维度 IC 检验 (dsa_dim_ic.py) — 发现加权分本身预测力弱 (2026-09-08)  `(#27)`
- DSA 评分重构研究 (2026-09-08) — 结论: v1 保持不变  `(#29)`
- buy-signal-watch 曾缺 DSA 门槛 (2026-09-08 修复)  `(#30)`
- 基本面因子该不该加进 DSA? — 验证方法论 (2026-09-08, `references/fundamental-factor-validation-2026-09.md`)  `(#31)`
- 不加基本面因子 (2026-09-08 决策确认)  `(#32)`
- buy-signal-watch 实为右侧突破, 已停用 (2026-09-09)  `(#33)`
- 交易反馈循环 (trade_journal.py) — 制度化的"信号→结果→调整" (2026-08-30)  `(#34)`
- 个人信号库 (signal_library.json + search_signals.py) — 简化版RAG (2026-08-30)  `(#35)`

**买入规则与监控**
- ★ 真实费用 / 执行延迟的证据校准 (2026-09-15, 只读第一阶段) ★  `(#39)`
- ★ 同一标的止损后买回 + 现金估算漂移 (2026-09-14 实盘) ★  `(#41)`
- 「你的系统推荐了 X」被质疑时的查证流程 (2026-09-14)  `(#43)`
- 「你让我卖出的节点是多少钱」= 同一天多个推送价位并存, 必须查 cron 输出并逐个标明性质 (2026-09-15)  `(#44)`
- 持仓集中度减仓提醒 watchdog (reduce-position-watch.py, 2026-09-14 新建)  `(#45)`
- Intraday ENTRY-signal watchdog (放量站稳 breakout monitor)  `(#53)`
- Whole-watchlist DSA buy-signal monitor (全自选股买入信号监控, 2026-08-31)  `(#54)`
- Minute-frequency buy-point watchdog — persisted state machine (2026-09-02)  `(#55)`

**执行纪律与守卫**
- ⚠️ 并发修改冲突：patch 覆盖了 cron 的持仓/止损修改 (2026-09-11 — 实际发生)  `(#46)`
- 2026-09-02 执行纪律 (统一硬规则 — 所有监控/回测/模拟盘遵守)  `(#47)`
- 2026-09-02 交易日历门控 (cn_trading_calendar.py)  `(#48)`
- 时段门 6 例: 09:35 BLOCKED / 09:50 ALLOWED / 11:35 BLOCKED / 13:30 ALLOWED / 14:50 BLOCKED / 周六 BLOCKED  `(#50)`
- 资金不足应出现在 warnings 且 allowed 不受影响; hard_stop_check 读 sell-policy 真值  `(#51)`

**watchdog / cron 运维**
- Watchdog JSON persistence pitfalls (2026-09-03 — both crons crashed, shared root cause)  `(#56)`
- Manual-run pollutes day-dedup state → cron goes silent (2026-09-08, breakout-watch)  `(#57)`
- Controlling the no_agent watchdog crons via cronjob tool (2026-09-08)  `(#58)`
- Cron delivery error `unknown platform 'webui'` → reports generated but never arrive (2026-09-08)  `(#60)`
- `weixin,origin` = DOUBLE delivery when origin is also weixin (2026-09-09 — real root cause of the recurring rate-limit)  `(#61)`

**策略与池子管理**
- 板块轮动分析 + 板块内选股(同花顺板块数据) (2026-09-06)  `(#65)`

**其他**
- Backtest engine must encode A-share rules  `(#17)`
- Strategy pitfalls (all hit and fixed in this session)  `(#18)`
- DSA → quant rule mapping (works well)  `(#19)`
- Key strategic insight (backtest truth, report honestly to Omi)  `(#20)`


**→ 以上全部章节的原文在**：`references/skill-migrated-sections-2026-09.md`（按编号顺序）