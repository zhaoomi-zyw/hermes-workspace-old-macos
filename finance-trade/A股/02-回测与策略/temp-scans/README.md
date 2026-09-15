# temp-scans（临时盘中扫描脚本）

这些是 2026-09-03 ~ 2026-09-15 期间按日/按时点生成的一次性扫描脚本，
命名规律 `_intraday_MMDD[_HHMM].py` / `_preclose_*.py` / `_live_*.py`。

**用途**：记录了当时的盘中判断逻辑与取数方式，对**复盘特定交易日**有参考价值。
**注意**：不是可复用的工具（每次运行都是为新一时点即兴生成的），
真正的常驻逻辑在 `../scripts/` 和 `../strategies/`。

| 前缀 | 含义 |
|------|------|
| `_intraday_*` | 盘中快照（含 DSA 实时计算）|
| `_preclose_*` | 收盘前检查 |
| `_live_*` | 实时 DSA |
| `_eod_*` | 日终扫描 |
| `_morning_scan` | 早间扫描 |
| `_scan_*` / `_q_star` / `_tail` | 临时查询 |
| `gen_agg_html.bak.py` | HTML报告生成器备份 |
