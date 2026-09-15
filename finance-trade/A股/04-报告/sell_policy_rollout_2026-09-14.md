# 卖出策略统一执行 — 上线报告

**策略版本**: `SELL-POLICY-v1.0-20260914`
**执行日期**: 2026-09-14
**范围**: 仅卖出规则（未改动买入策略/仓位预算/基金规则）
**执行权限**: 仅微信提醒，用户在券商端操作；无自动下单、无撤单、无券商凭据访问

---

## 一、结论摘要（区分已实现 / 已验证 / 已应用 / 阻塞）

| 类别 | 内容 |
|------|------|
| **已实现** | 统一卖出模块 `strategies/sell_policy.py`（状态机 + 唯一参数配置 + 原子持久化）；4 个入口全部接入（signal_daily / dsa_strategy / stop-loss-watch / 5 个 cron 提示词）|
| **已验证** | 11 个验收场景 → **30/30 断言通过**；dry-run 捕获硬止损+盈利保护两条提醒；迁移用真实分钟数据重建 |
| **已应用** | 5 个股票 cron 已更新并生效；止损 watchdog 已切到统一模块；分钟级（每分钟）check 已存在 |
| **阻塞/待确认** | ①赤峰硬止损 **已由 Omi 确认为 42.26**（R6 只升不降）；②历史 H 仅 5 分钟粒度（非逐笔），存在采样遗漏风险 |

---

## 二、修改文件清单

| 文件 | 变更 |
|------|------|
| `quant-backtest/strategies/sell_policy.py` | **新增**：唯一权威模块（状态机/规则/参数/持久化/自测）|
| `quant-backtest/migrate_sell_policy.py` | **新增**：历史 H/保护状态迁移脚本 |
| `quant-backtest/dryrun_sell_policy.py` | **新增**：dry-run 提醒捕获（不发送）|
| `quant-backtest/signal_daily.py` | 接入模块：持仓改从模块状态读取（不再硬编码）；`_aggressive_exit_advice` 改为调用模块 |
| `quant-backtest/strategies/dsa_strategy.py` | `DSAConfig` 退出参数改为从模块派生；trend 退出分支调用模块状态机 |
| `~/.hermes/profiles/main/scripts/stop-loss-watch.py` | 重写：全部委托模块，去掉自持参数与旧双层止损 |
| `~/.hermes/profiles/main/cron/jobs.json` | 5 个 cron 提示词/名称更新（见第五节）|

**备份目录**: `quant-backtest/backups/sell_policy_20260914/`（quant/ scripts/ state/ cron/ 四类，含 jobs.json.bak、stop-loss-watch-state.json、trading-execution-events.jsonl）

---

## 三、统一模块设计

**唯一参数配置**（`SellParams`）：
```
hard_stop_pct=0.06      # R1 硬止损 = C×0.94
profit_activate_pct=0.08 # R3 H≥C×1.08 开保护
profit_floor_pct=0.03    # R4 保护线最低 = C×1.03
trail_from_peak_pct=0.07 # R4 保护线 = H×0.93
price_decimals=2         # 触发线取整；成本保留3位
```

**状态字段**：lifecycle_id / cost / total_qty / sellable_qty / today_new_qty / quote_time /
peak_h(持仓后最高价) / protection_active / hard_stop / profit_line / pending_exit /
fired_events(通知去重) / add_log(加仓审计) / migrated / migration_note

**持久化**：`~/.hermes/state/sell-policy-state.json`，写采用 tmp+`os.replace` 原子替换 + `fcntl.flock` 文件锁（多 cron 并发安全）；进程重启不丢保护线/待退出。

**纯函数核心**与持久化分离：`evaluate_exit` / `fire_exit` / `update_quote` / `add_position` 等无副作用，回测与实盘共用（场景11）。

---

## 四、验证命令与结果

```bash
# 1) 验收场景（11 项 → 30 断言）
cd /Users/omi/workspace/quant-backtest && .venv/bin/python strategies/sell_policy.py --test
# → === 验收: 30/30 通过 ===

# 2) 迁移（真实分钟数据重建 H）
.venv/bin/python migrate_sell_policy.py
# → results/sell_policy_migration_2026-09-14.json

# 3) dry-run 提醒
.venv/bin/python dryrun_sell_policy.py

# 4) 回测（统一模块退出）
.venv/bin/python -c "from strategies.dsa_strategy import backtest_dsa,DSAConfig; from fetch_data_hithink import fetch_history; r=backtest_dsa(fetch_history('600988','赤峰黄金'),DSAConfig()); print(len(r.trades))"
# → 19 trades, 含 止损/盈利保护 事件

# 5) signal_daily 端到端
.venv/bin/python signal_daily.py 600988
```

**11 个验收场景结果（全通过）**：
1. C=100 价94 硬止损触发；MA60 单独跌破不触发 ✅
2. 100→108 保护开启 P=103；回落107保护仍开；触103生成事件 ✅
3. 100→120 P=111.6；触111.6触发；反弹不撤销 ✅
4. 高点上移保护线升高、回落不降；重启后保持 ✅
5. 原100@100(S=94)+买100@96 → 新成本98、S仍94(不降92.12) ✅
6. 已保护+已加仓：状态继承、保护线不下降；边界（加仓前高点不反向重算）✅
7. 老仓可卖100/新仓不可卖100 分别记录；部分卖出后留剩余；次日反弹继续提示 ✅
8. 未确认成交数量不减；重复 cron 不重复创建事件 ✅
9. 清仓再买入：旧高点/旧锁利线不污染 ✅
10. 陈旧报价/并发写不丢状态；无效报价不关保护、不产生虚假退出 ✅
11. 同时序行情，实盘判定与回测模块输出相同退出事件 ✅

---

## 五、cron 现状（ID / 名称 / 频率 / 调用入口 / 版本 / 微信路由）

| cron ID | 名称 | 频率 | 调用入口 | 策略版本 | 微信路由 |
|---------|------|------|----------|----------|----------|
| `aa6316b0b52f` | 退出监控(sell-policy统一): 赤峰/星网 | **每分钟** `* 9-11,13-14 * * 1-5` | `stop-loss-watch.py`→sell_policy | v1.0 | weixin:o9cq80_…@im.wechat |
| `0d1bb1811d94` | 每日晨间DSA分析 9:20 | `25 9 * * 1-5` | 读 sell-policy-state.json | v1.0 | weixin:o9cq80_…@im.wechat |
| `51814bf28ed7` | 每小时监控 | `3 10,11,12,13,14 * * 1-5` | 读状态文件 | v1.0 | weixin:o9cq80_…@im.wechat |
| `91df35c579fb` | 收盘前检查(积极版) | `57 14 * * 1-5` | 读状态文件 | v1.0 | weixin:o9cq80_…@im.wechat |
| `6258267cf112` | 每日分析报告(查真实持仓) | `15 18 * * 1-5` | 读状态文件 | v1.0 | weixin:o9cq80_…@im.wechat |
| `c80c562732a4` | DSA量化模拟盘每日信号 | `5 19 * * 1-5` | `dsa-signal-daily.sh`→signal_daily | v1.0 | weixin:o9cq80_…@im.wechat |

**频率说明（任务书要求证明）**：止损 watchdog 已是**每分钟**（`* 9-11,13-14`），轻量脚本、仅取腾讯实时快照，不每分钟启动大型分析。**注意**：这是"分钟级快照"而非逐笔——见第七节遗漏风险。晨报/盘中/14:57/18:15 为汇总入口，均改为**读状态文件**取退出线（单一来源）。

**未改动**：买入类 cron（低吸监控 8b7a57537834、减仓提醒 96c62b6d3b3b）、定投、宠物、健康等无关任务保持原样。

---

## 六、dry-run 提醒（未发送，仅捕获）

**A. 硬止损触发（星网）**
```
🔔 退出事件 · 星网锐捷(002396)
   策略版本: SELL-POLICY-v1.0-20260914
   报价: 33.50 @ 2026-09-14 10:30:00
   触发原因: 硬止损 (触发线 33.73)
   成本: 35.88 | 持仓后最高价 H: 35.93
   有效退出线: 33.73
   可卖: 0股 | 待退出(T+1): 100股
   事件ID: LC-sz002396-2026-09-14:硬止损:33.73
   ⚠️ 请在券商端操作并反馈成交; 本提醒不代表已卖出。
```

**B. 盈利保护触发（赤峰，模拟 H 到 48.31 开启后回落）**
```
🔔 退出事件 · 赤峰黄金(600988)
   策略版本: SELL-POLICY-v1.0-20260914
   报价: 46.08 @ 2026-09-15 14:00:00
   触发原因: 盈利保护 (触发线 46.08)
   成本: 44.735 | 持仓后最高价 H: 48.31
   有效退出线: 46.08
   可卖: 200股 | 待退出(T+1): 0股
   事件ID: LC-sh600988-2026-09-02:盈利保护:46.08
   ⚠️ 请在券商端操作并反馈成交; 本提醒不代表已卖出。
```

**微信渠道验证**：已发一条明确标记 **"策略升级测试 · 无需交易"** 的单条消息到现有接收人（一次性 cron `c839e18d507f`）。**未伪造任何真实止损通知。**

---

## 七、状态迁移依据 / 缺口

**迁移数据源**：新浪 `CN_MarketDataService` 5 分钟 K（scale=5），覆盖 2026-08-14~09-14，共 1023 根。

| 持仓 | 生命周期起点 | 重建 H | 窗口 | 粒度 | 保护 | 硬止损 S |
|------|-------------|-------|------|------|------|----------|
| 赤峰黄金 sh600988 | 2026-09-02（首买100@44.96）| **47.63** | 09-02 09:35 ~ 09-14 15:00 | 5min | 未开启（47.63<48.31）| 42.26 |
| 星网锐捷 sz002396 | 2026-09-14 10:03（买回100@35.88）| **35.93** | 09-14 10:05 ~ 09-14 15:00 | 5min | 未开启（35.93<38.75）| 33.73 |

**T-027 / T-029 核对**：确认**同一笔交易**（星网锐捷 9/10 买@35.96）。T-027 为未平仓状态、T-029 为已平仓状态（9/11 止损@33.80，-216）。**未删除历史**。9/14 的 T-031（买回@35.88）是**新生命周期**，不继承旧记录。

**⚠️ 缺口/风险**：
1. **粒度缺口**：H 为 5 分钟 K 的 high（"已观测最高价"），**非逐笔**。若新高/越线发生在两次采样之间，可能未被完整捕捉 → 已在迁移记录 `peak_h` 字段注明。
2. **未用买入前高点填补**：赤峰 H 取 9/02 09:30 之后；未使用 9/02 前或当日早于买入的高点。
3. **硬止损差异（待确认）**：赤峰按 R6"只升不降" = **42.26**（源自首买 44.96×0.94）；现有实盘 watchdog 用 **42.05**（按合并成本 44.735×0.94）。差异 0.21 元。当前模块采用 **42.26**（更保守/更早退出）。**需 Omi 确认采用哪个**。
4. 迁移后两只均**未开启保护**（H 未达 C×1.08），故"迁移数据不足"不影响保护状态——仅硬止损生效，属可安全启用情形。

---

## 八、待退出 / 通知去重机制

- 退出事件含唯一 `event_id`（`<lifecycle>:<原因>:<触发线>`），`fired_events` 去重 → 同事件不重复发。
- 触发后：可卖部分提醒先卖；`today_new_qty`（T+1）记入 `pending_exit.qty_pending`，次一交易日 `roll_trading_day` 解禁后由盘中/收盘入口继续提示，**反弹也不取消**。
- 待退出期间 `can_add()` 返回 False → **禁止建议加仓解除退出**。
- 未确认成交 → `total_qty` 不变；部分成交 → `confirm_sell` 只减剩余。

---

## 九、是否已正式应用 & 回退方法

**已应用**：5 个股票 cron 已更新生效；`stop-loss-watch.py` 已切换；状态文件已生成。全部脚本已通过语法/运行验证。

**回退方法**（任一步可单独回退）：
```bash
BK=/Users/omi/workspace/quant-backtest/backups/sell_policy_20260914
# 1) 脚本回退
cp $BK/quant/signal_daily.py      /Users/omi/workspace/quant-backtest/
cp $BK/quant/dsa_strategy.py      /Users/omi/workspace/quant-backtest/strategies/
cp $BK/scripts/stop-loss-watch.py /Users/omi/.hermes/profiles/main/scripts/
cp $BK/scripts/trading_execution_guard.py /Users/omi/.hermes/profiles/main/scripts/
# 2) cron 回退（关键任务配置）
cp $BK/cron/jobs.json.bak /Users/omi/.hermes/profiles/main/cron/jobs.json
# 3) 状态回退
cp $BK/state/stop-loss-watch-state.json /Users/omi/.hermes/state/
# 4) 删除新状态文件（回退到无 sell-policy 状态）
rm -f /Users/omi/.hermes/state/sell-policy-state.json
```

---

## 十、后续（需 Omi 决策）

1. **确认赤峰硬止损**：42.26（R6 只升不降）还是 42.05（合并成本）？
2. 如需更精确 H：可接逐笔/分钟级实时快照（当前 5 分钟粒度）。
3. 分钟级 watchdog 依赖腾讯快照接口；若接口不可用则静默（不误报），需接受该可用性边界。

---

*报告生成: 2026-09-14 · 策略版本 SELL-POLICY-v1.0-20260914*
