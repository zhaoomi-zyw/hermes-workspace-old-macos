# AI/Token Supply Chain Fund Mapping Methodology

How to map an industry chain (e.g., AI算力/token economy) to investable ETFs, identify what's already hot vs. under-the-radar, surface overlooked segments, and produce portfolio-level recommendations.

## Step 1: Deconstruct the Industry Chain

Break into upstream/midstream/downstream with concrete company examples:

```
上游（算力基础设施）→ AI芯片, 光模块(800G/1.6T/CPO), 服务器, 存储/HBM, PCB/基板, 液冷散热, 数据中心, 光纤光缆, 网络设备
中游（大模型/平台）→ 百度文心, 阿里通义, DeepSeek, 字节豆包, 云计算
下游（AI应用）→ 办公, 自动驾驶, 金融, 医疗, 机器人/具身智能
AI安全 → 横跨三层, 大模型安全+数据安全+网络安全
```

Key insight: "token" in the AI context = 算力的计量单位. The user asking about "token related industries" means the entire AI compute supply chain.

## Step 2: Parallel Search for ETF Coverage

Use anysearch batch_search with 5 queries targeting different chain segments:

```bash
python3 scripts/anysearch_cli.py batch_search --queries '[
  {"query":"液冷散热 数据中心 温控 ETF 基金 概念股 2026","max_results":5},
  {"query":"HBM 高带宽存储 AI存储 ETF 基金 2026","max_results":5},
  {"query":"AI PCB 封装基板 算力 概念股 ETF 2026","max_results":5},
  {"query":"AI电源 算力中心 配电 ETF 2026","max_results":5},
  {"query":"边缘计算 端侧AI AI推理 ETF 2026","max_results":5}
]'
```

Follow up with deeper dives into promising segments:
```bash
python3 scripts/anysearch_cli.py batch_search --queries '[
  {"query":"CPO 硅光 共封装光学 概念股 ETF 基金 2026 低估","max_results":5},
  {"query":"AI应用 软件 SaaS 大模型落地 ETF 2026","max_results":5},
  {"query":"机器人 具身智能 概念股 ETF 基金 2026","max_results":5},
  {"query":"先进封装 Chiplet ETF 2026","max_results":5},
  {"query":"量子计算 概念股 ETFA股 2026","max_results":5}
]'
```

## Step 3: Classify by "Hotness" Tier

From search results, classify each segment:

- 🔥 **Already hyped** (year-to-date gains >50%, extreme valuations, media saturation): 
  光模块/CPO (159363), AI芯片 (589130), 存储/HBM (513310 年内+138%), PCB/通信 (515050 年内+58%)
- ⚡ **Heating up** (gaining attention but not saturated): 
  液冷散热 (无纯ETF), 先进封装 (588170, 125亿规模), AI电源/电网 (159326)
- 💎 **Under-the-radar** (new ETFs, low media coverage, pre-revenue stage): 
  AI软件 (159590/159068), 机器人/具身智能 (562500/159530), 量子计算 (无纯ETF), 信息安全 (159613/562920), 大数据 (516700)

## Step 4: Fund Deep Analysis

For shortlisted funds, use fund-analysis-agents for multi-agent AI analysis:

```bash
# Start the platform
cd ~/fund-analysis-agents && docker start fund-redis fund-mysql && source .env && java -jar fund-application/target/fund-application-0.0.1-SNAPSHOT.jar &

# Trigger via browser at http://localhost:8080 (admin/admin2026)
# Each analysis takes 3-4 minutes (6 analysts + 3 rounds debate)
```

Key findings from analysis (2026-06-04):

| Code | Name | Advice | Position | Risk | Volatility | Note |
|------|------|--------|----------|------|-----------|------|
| 159326 | 电网设备ETF | 持有 | 10-40% | 中 | 33.92% | Stable, grid investment 6200亿 |
| 515880 | 通信ETF | 持有 | 15-30% | 中高 | 47.51% | Extreme greed, reduce |
| 159530 | 机器人ETF易方达 | 持有 | 5-10% | 中高 | 36.44% | 人形76% but mini-fund 5亿 |
| 562500 | 机器人ETF华夏 | 持有 | 10-20% | 中高 | 29.87% | 209亿 scale, preferred over 159530 |

## Step 5: Portfolio Overlap Detection

Before recommending ETFs, map existing holdings to the chain:

- Check for same-underlying ETFs tracking the SAME index (e.g., 159530 vs 562500 both robot)
- Check ETF-vs-stock overlap (e.g., 亨通光电/中天科技 vs 515880通信ETF vs 159326电网ETF)
- Check cross-ETF overlap (e.g., 科大讯飞 appears in 562500, 159590, 516700 simultaneously)
- Flag mini-funds (<2亿 scale) for liquidity risk (e.g., 562920 at 0.78亿, 516700 at 1.08亿)

## Step 6: Portfolio Optimization & Allocation

Consolidation rules:
- Keep at most 1 ETF per direction (delete duplicates)
- Replace mini-funds with larger equivalents
- Merge overlapping stock+ETF positions (keep the better one)
- Reserve 15-20% cash for dip-buying

Target allocation framework (5 directions covering the full AI chain):

| Direction | Fund | % | Logic |
|-----------|------|---|-------|
| Power | 159326 电网设备 | 20% | AI data center power demand |
| Transport | 515880 通信ETF | 15% | Fiber/optical modules |
| Application | 159590 软件ETF | 20% | AI software monetization |
| Terminal | 562500 机器人ETF | 20% | Embodied AI/robotics |
| Security | 159613 信息安全ETF | 10% | AI security tailwind |
| Cash | — | 15% | Wait for dips |

## Step 7: Periodic Reporting

Generate weekly reports covering:
1. Market overview (index, sector performance)
2. Fund analysis results (from fund-analysis-agents or anysearch)
3. Supply chain hotness update
4. Portfolio adjustments
5. Next week catalysts

Use cron to automate: `cronjob action=create schedule="0 22 * * 5"` for Friday close delivery.

## Robot ETF Specifics

Two main indices:
- **H30590 (中证机器人)**: 66 constituents, covers industrial + humanoid. ETFs: 562500 (209亿), 159770 (48亿), 159559 (22亿), 159526 (10亿), 562360 (小)
- **国证机器人产业**: Higher humanoid purity (~76%). ETF: 159530 (5亿, mini-fund risk)

562500 is preferred for scale and liquidity despite lower humanoid purity.

## Robot Upstream (Stocks, Higher Elasticity)

Key components by BOM%:
- 谐波减速器 (~15%): 绿的谐波 688017 (市占率>60%)
- RV减速器 (~10%): 双环传动 002472
- 行星滚柱丝杠 (~20%): 贝斯特 300580, 五洲新春 603667
- 空心杯电机 (~8%): 鸣志电器 603728, 信捷电气 603416
- 六维力传感器 (~10%): 柯力传感 603662
- 无框力矩电机 (~8%): 步科股份 688160

Note: Some already ran up (长盛轴承 +433% in 2 months). 贝斯特 and 柯力传感 are relatively less hyped.

## Key Fund Codes for AI/Token Chain (2026-06 Updated)

| Segment | Code | Name | Scale | Hotness | AI Analysis |
|---------|------|------|-------|---------|-------------|
| 光模块 | 159363 | 创业板人工智能ETF华宝 | 74亿 | 🔥 | — |
| AI芯片 | 589130 | 科创芯片ETF易方达 | 19亿 | 🔥 | — |
| 存储 | 513310 | 中韩半导体ETF | — | 🔥 年内+138% | — |
| 通信/PCB | 515050 | 通信ETF华夏 | — | 🔥 年内+58% | — |
| 先进封装 | 588170 | 科创半导体ETF华夏 | 125亿 | ⚡ | — |
| 电网设备 | 159326 | 电网设备ETF华夏 | — | ⚡ | ✅ 持有75%置信度 |
| 通信设备 | 515880 | 通信ETF国泰 | — | ⚡ | ✅ 持有70%置信度 |
| AI软件 | 159068 | 软件ETF华夏 | 新发 | 💎 6月新发 | 无数据(刚发行) |
| AI软件 | 159590 | 软件ETF汇添富 | 4.96亿 | 💎 | — |
| 机器人 | 562500 | 机器人ETF华夏 | 209亿 | 💎 | ✅ 持有75%置信度 |
| 机器人(高纯度) | 159530 | 机器人ETF易方达 | 5亿 | 💎 迷你 | ✅ 持有65%置信度 |
| AI安全 | 159613 | 信息安全ETF嘉实 | — | 💎 | — |
| AI安全 | 562920 | 信息安全ETF易方达 | 0.78亿 | 💎 迷你 | — |
| 大数据 | 516700 | 大数据ETF华宝 | 1.08亿 | 💎 迷你 | — |

## Search Query Patterns for Under-the-Radar Discovery

When looking for overlooked segments, search for:
- "概念股 ETF 2026 低估" (concept stocks, ETFs, undervalued)
- "产业链 上游 供应商 龙头" (supply chain, upstream, leaders)
- "[specific component] 上市公司 A股" (listed companies for specific parts)
- "还没火" or "低位" or "补涨" (not yet hot, low position, catch-up rally)

For individual stock earnings, search pattern: "[company] 2026 Q1 营收 净利润 增长"
