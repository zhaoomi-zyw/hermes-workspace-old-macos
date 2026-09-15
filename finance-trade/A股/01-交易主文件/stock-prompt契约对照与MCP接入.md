# stock-prompt 契约对照与 MarketGraph MCP 接入记录

日期：2026-09-13
相关仓库：https://github.com/Geekwls/stock-prompt （v7.6.0，无 LICENSE 文件）
本地克隆：/Users/omi/workspace/stock-prompt

---

## 一、MarketGraph MCP 接入状态

- 服务端已注册到 main profile 的 config.yaml（`mcp_servers.marketgraph-data`）
- 解释器：`/usr/local/bin/python3.11`（独立于 Hermes venv，避免 hermes update 后失效）
- 入口：`/Users/omi/workspace/stock-prompt/mcp/marketgraph-mcp/server.py`
- connect_timeout: 90，21 个工具全部启用
- 注册命令：`hermes mcp add marketgraph-data --command /usr/local/bin/python3.11 --connect-timeout 90 --args <server.py 绝对路径>`
  - 注意：该命令有交互确认（Enable all 21 tools?），需 `printf 'y\n' |` 管道喂入，否则会 Cancelled
- 注册后必须重启 gateway 才生效：微信发 `/restart`，或 gateway 外部 shell 执行 `hermes gateway restart`
- 验证：`hermes mcp list` / `hermes mcp test marketgraph-data`

### 数据源准确性实测（2026-09-13，核对 9/11 数据）

已验证正确：
- 个股行情（中文名解析、PE/PB/市值/五档）
- 750 日前复权 K 线 + MA20/50/120/250/500 + ATR14 + Bias + 3 年分位 + 周线共振 + 威科夫三层
- 市场情绪家数：涨停 40 / 跌停 21 / 炸板 18 / 炸板率 31.03%（=18/58 自洽）/ 最高 4 连板
  —— 与同花顺 API（limit-up-pool / limit-down-pool / limit-break-pool）逐项一致
- 指数涨跌幅：上证 9/11 -1.18%，与腾讯原始接口一致

已验证错误 / 不可用：
- `total_turnover_billion` 字段：返回 112.14，独立源（腾讯+东财）实测两市成交额 19,718.98 亿 ≈ 1971.9 billion，偏差约 17 倍。**该字段不可用于任何计算或判断**
- 日期标注：周日（非交易日）调用时 `date` 返回当天日期（20260913），而实际数据是 9/11 收盘的。按 `date` 字段判断"这是今天的数"会误读。**使用时必须以内部 `as_of` / `data_date` 为准，不能信外层 date**

### 相对现有工具的增量（值得用）
1. 当日 240 分钟分时 + VWAP + 9:25 集合竞价承接力（hithink-finance 无分钟级数据）
2. 龙虎榜前 5 大买卖席位穿透（自动识别机构专用/北向/游资）
3. 行业板块封板质量 Q、炸板结构、等权篮子容灾序列
4. 大数据量日 K 一次批量返回（750 日 + 全均线矩阵）

### 与现有工具重叠（无增量）
- 实时行情、涨停池/连板天梯：同花顺 API 与腾讯行情更快、更权威
- 结论：只作补充数据源，**不得接入止损 / 低吸判断链路**（该链路继续用腾讯实时价 + 本地 CSV）

---

## 二、契约对照：stock-prompt vs 我们现有 cron 防幻觉写法

### 我们的现有做法（cron 提示词）

| 做法 | 具体写法 |
|---|---|
| 单一权威源 | 第一步强制 `read_file` `/Users/omi/Documents/macos hermes/04-Trading/Omi A股交易主文件.md` |
| 显式禁编造 | "获取真实持仓/现金/交易历史，禁止编造" |
| 硬编码降级 | "主文件是唯一权威，下述硬编码为过期提示，以主文件为准" |
| 强制实时计算 | "DSA 必须当场用实时价+日线算，禁止写'等晨报确认'" |
| 条件不许加码 | "低吸只按四条件，禁止用'距MA60远/60日位高'额外否决" |
| 数据源单一化 | "价格用注入的腾讯实时 context，勿搜索" |
| 非交易日跳过 | 开头判断，非交易日直接输出跳过 |
| 教训来源 | 2026-09-03 cron 复盘编造持仓（立讯日期错误） |

### stock-prompt 契约的做法

| 机制 | 具体规则 |
|---|---|
| 证据编号 | 关键事实编号 F01/F02…，记录来源层级+日期+获取时间+口径；结论必须回指 Fxx，无证据内容标"推断" |
| 时点标注 | 报告必须给 `as_of`，区分盘中快照/收盘/公告日/财报期；过期数据可作背景但不得伪装成当前 |
| 来源分级 | P1–P4；同一网关/同一转载只算一个独立证据族（`source_family` + `independence_group`），禁止用多个转载抬高置信度 |
| 覆盖率公式 | `Data Coverage = 已验证证据权重 / 计划证据总权重`；≥85% 完整评分，70–84% 条件化且置信最高"中"，50–69% 只输出条件判断不给精确分，<50% 只输出审计与待补清单 |
| N/A 语义 | N/A 不等于 0 分或中性分；核心模块缺失也要保留并说明影响 |
| 状态门 | `data_status != ok` 不得参与精确计算或支撑方向结论 |
| 确定性计算 | 指标必须调用脚本，不得模型自创公式；保留 `formula_version` / `input_snapshot_id` / `missing` / `status`，回退手算要标 `manual_fallback` |
| 隐私边界 | 状态持久化默认不保存账户/仓位/成本，除非用户明确授权 |
| 连续复盘 | 必须先核验旧结论，`review_delta` 六组字段（previous_snapshot_id / changed_facts / conclusion_delta / confirmed_hypotheses / invalidated_hypotheses / unchanged_but_important）；无前序要标"首次基准"，**不得虚构变化** |
| 表述边界 | 评分/概率/历史命中率不代表收益承诺；不得输出确定性买卖指令；缺用户风险参数时不给固定百分比止损 |

---

## 三、差距分析：可以吸收的 5 条

1. **显式 `as_of` 标注（优先级最高）**
   现在 cron 依赖 `{{#date}}` 和注入的腾讯行情，但没有要求逐条标注数据时点/口径。周末或盘后运行时，数据源返回的是上一交易日数据，不标 as_of 就会被当成今日——这正是我实测 marketgraph 踩到的坑。建议在输出里加一行"数据时点：YYYY-MM-DD 收盘 / 盘中 HH:MM"，并明确"周末调用时数据为最近完整交易日"。

2. **覆盖率 + 数据状态显式化**
   现在缺字段是"写不出来就跳过"，没有量化层。加一句"本次可用字段覆盖率 X%，数据状态：完整/部分/不足"，并要求覆盖率不足时只给条件化结论、不给精确评分，可以防"字段缺了静默按 0 或中性处理"。

3. **结论回指证据（轻量版）**
   不必上 F01/F02 全套，但可以让关键数字带上来源标签（如"DSA 来自 signal_daily.py 实时计算"/"价格来自腾讯注入 context"），让"这个数字谁算的"可追溯。成本低，收益是排查错误时能定位。

4. **`review_delta` 的最小字段**
   现有主文件 + trade_journal 已承担了连续性，但没有强制的"较上次变化 / 假设确认或失效"。可在日报里加两行：较上次结论的变化、上次判断被证实还是失效。也可以直接在主文件里加"上期假设状态"小节。

5. **独立证据族概念**
   搜新闻时容易把多个转载当多个源。采纳 `source_family` 思路：同一事件的多个转载只算一条证据，禁止用"3 家媒体都报道"抬高确定性。

---

## 四、明确不采纳的部分

- P1–P4 完整分级 + 8 类 Artifact Schema + handoff_store / thesis_store 全套：对单人单账户流程过重，且引入 ~/.stock-prompt 状态目录增加故障面。
- "缺少风险参数时不给固定百分比止损"：Omi 已参数化（-6% 硬止损 / +8% 浮盈线），属"用户已提供参数"，保留现有做法。
- "不得输出确定性买卖指令"：与现有 cron 给出明确操作建议的用途冲突，保留现有做法。
- 确定性计算脚本机制：我们已有 `signal_daily.py` / `dsa_scores.py` / `stats_trades_run.py` 承担同样角色，思路一致，不重复引入。

---

## 五、待办与执行记录

- [x] 2026-09-13：第 1、2 条（数据时点标注 + 覆盖率与数据状态）已写入三个 job 的提示词——
  「每日分析报告(查真实持仓)」6258267cf112、「每日晨间DSA分析 9:20」0d1bb1811d94、「收盘前检查(积极版)」91df35c579fb。
  改法是加在提示词末尾新增两段【⚠️…(强制)】条款，原有内容、参数、排期、投递通道均未改动（已 diff 核对）。
  未改：「每小时监控」51814bf28ed7（同类分析 job，待确认是否一并加）。
- [ ] 重启 gateway 使 MCP 生效（微信发 `/restart` 或外部 shell `hermes gateway restart`）——注意：cron 提示词的改动不需要重启，host 每次 fire 时读 jobs.json
- [ ] 重启后实测 `mcp__marketgraph-data__get_stock_timeline` 与 `get_longhubang_detail` 是否可用
- [ ] 若要用成交额类字段，必须先自行用腾讯/东财核对（已知该字段有 bug）
- [ ] 观察 2026-09-14（周一）三份 cron 输出，确认新条款是否被遵守

---

## 六、遗留问题：脚本写死持仓的漂移（2026-09-13 记录，Omi 决定暂缓处理）

**问题**：`intraday_live_dsa.py` 第 11 行写死 `HOLD = {"600988": (100, 44.96, 41.81), "000878": (200, 18.31, 17.02)}`（9/10 快照，且止损还是 -7% 时代的值）。实际主文件为：赤峰黄金 200股@44.685 止损42.00；云南铜业已于 9/11 止损离场。运行该脚本会输出错误持仓（赤峰浮亏只算一半、云南铜业被当成仍在持仓且贴近止损）。

**范围**：`dsa_morning_scan.py`、`_live_dsa_0911.py` 同样各自写死 WATCH/HOLD。这些脚本**未被任何 cron 或 skill 引用**（已 grep 确认：profiles/main/scripts、quant-backtest、a-share-quant-backtest 技能均零引用），所以不会自动推送错信息；风险只在手工运行时误导，以及每次交易后它们不会更新。

**根因**：技能里「每笔交易后同步三处」的纪律只覆盖 Obsidian 主文件、signal_daily.py、stop-loss-watch.py，这些散落脚本不在名单里。

**已完成的可行性验证**：主文件第一节现有格式**不能稳定解析**——当前持仓与已清仓用同一行格式，仅靠「已于…卖出」等散文措辞区分；正则实测把 4 条都识别成持仓（只有 1 条是真的）。另外主文件内部有一处不一致：第一节写赤峰 200股@44.685/止损42.00，第四节仍写「成本44.96→止损42.26」（旧的单笔基数）。

**待办方案（未执行）**：
1. 在主文件第一节末尾加机器可读块：
   ```portfolio
   cash: 3014
   position: 600988 200 44.685 42.00
   ```
   （格式：`position: 代码 股数 成本 止损`，多只多行，空仓只留 cash 行）
2. 写共享 `portfolio.py` 的 `load_portfolio()`，让 intraday_live_dsa.py / dsa_morning_scan.py / _live_dsa_0911.py 都从主文件取持仓，消灭写死副本
3. 进一步让 signal_daily.py 的 HOLDINGS 也读它，把「同步三处」收缩为「改主文件一处 + 挂/撤止损监控」
4. 顺带更正主文件第四节的 44.96/42.26 旧基数

**Omi 2026-09-13 决定：暂不动**（不改主文件、不改脚本）。
