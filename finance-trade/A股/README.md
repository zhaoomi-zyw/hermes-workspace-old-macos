# A股

股票交易、量化回测、DSA 分析相关内容。

## 01-交易主文件
| 文件 | 说明 |
|------|------|
| `Omi A股交易主文件.md` | **唯一权威**：当前持仓、止损、纪律、交易历史、自选股清单 |
| `投资持仓导出_2026-08-14.md` | 历史持仓快照（含板块分布）|
| `stock-prompt契约对照与MCP接入.md` | MarketGraph MCP 数据源接入记录 |
| `一手试探规则手册.md` | 建仓规则（SIG-010）|
| `quant-backtest-README.md` | 回测仓库说明 |

## 02-回测与策略
- `scripts/`（43个）：数据抓取(fetch_*)、DSA评分(dsa_*)、回测(backtest_*)、HTML报告(gen_*)、
  交易日志(trade_journal*)、日历(generate_cn_calendar)、IC检验(ic_eval/dsa_dim_ic)
- `strategies/`（3个）：`sell_policy.py`(统一卖出规则v1.0)、`dsa_strategy.py`、`ma_strategy.py`

**当前策略：积极版趋势策略**（2026-09-06启用，止损-6%）
- 买入：左侧低吸四条件（10日回撤≥5% + 站上MA60 + DSA≥B级 + 近MA5/MA10≤2%）
- 卖出：硬止损-6% → 浮盈≥+8%后启用移动止损/破MA60

## 03-数据
14 只自选股日K（往前复权），CSV 格式，覆盖约5年。

## 04-报告
回测 HTML 报告（`agg_report.html` 3年积极版对比、`planA_3y_report.html` 方案A）、
蒙特卡洛未来模拟（`mc_1y_*.json`）、止损宽度敏感性（`stop_compare*`）、
策略迁移记录（`sell_policy_rollout_2026-09-14.md`）。

## 05-交易记录
- `trade_journal.json` — **逐笔交易日志**（含 signal_id 归因、MFE/MAE、教训）
- `signal_library.json` — 信号库（SIG-001 低吸 等）
- `stats_trades_run.py` — 统计脚本（胜率/盈亏比/按信号分组）

## ⚠️ 已知陷阱（回测必看）
1. 支撑/压力滚动窗口必须 `.shift(1)`，否则是未来函数
2. 入场周期 ≠ 离场周期（同窗口会平均持仓1天）
3. 回测收益 ≠ 实盘可得（右侧突破纸面更好但追价吃掉优势）
4. 补丁必须用完整策略(含止损/成本)验证 —— 已否决3个"看起来有道理"的过滤条件
