#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 ETF vs 个股 回测对比 HTML 报告（纯 SVG 手绘，无外部依赖）"""
import json, datetime, html
from pathlib import Path

D = Path("/Users/omi/workspace/quant-backtest/results/confirmed_policy_3y_20260914")
d = json.loads((D / "etf_vs_stock_dailyproxy.json").read_text(encoding="utf-8"))
ETF, STK = "ETF池(9只)", "个股池(12只)"
etf, stk = d[ETF], d[STK]

INI = 13822.47
NAMES = {"sh515880":"通信ETF国泰","sh512480":"半导体ETF国联安","sz159995":"芯片ETF华夏",
         "sh515050":"通信ETF华夏","sz159819":"人工智能ETF","sh512010":"医药ETF易方达",
         "sz159992":"创新药ETF银华","sh513120":"港股创新药广发","sh512170":"医疗ETF华宝",
         "601138":"工业富联","002156":"通富微电","600460":"士兰微","603380":"易德龙",
         "002396":"星网锐捷","000938":"紫光股份","600487":"亨通光电","600522":"中天科技",
         "600988":"赤峰黄金","600219":"南山铝业","000878":"云南铜业","600760":"中航沈飞"}

# ---------- SVG 折线图 ----------
def svg_line(series, w=980, h=340, pad=(62, 18, 40, 58), base=100.0, title=""):
    """series: [(label, color, [(date, nav)])]  nav=归一化净值(起点100)"""
    pl, pt, pr, pb = pad
    iw, ih = w - pl - pr, h - pt - pb
    allv = [v for _, _, pts in series for _, v in pts]
    lo, hi = min(allv), max(allv)
    span = max(hi - lo, 1e-9)
    lo, hi = lo - span * 0.06, hi + span * 0.06
    span = hi - lo
    n = max(len(pts) for _, _, pts in series)
    def X(i): return pl + iw * (i / max(n - 1, 1))
    def Y(v): return pt + ih * (1 - (v - lo) / span)
    g = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Roboto,sans-serif">']
    # 网格
    for k in range(6):
        v = lo + span * k / 5
        y = Y(v)
        g.append(f'<line x1="{pl}" y1="{y:.1f}" x2="{pl+iw}" y2="{y:.1f}" stroke="#e6ebe8" stroke-width="1"/>')
        g.append(f'<text x="{pl-8}" y="{y+4:.1f}" font-size="11" fill="#8a9992" text-anchor="end">{v:.0f}</text>')
    # 基准线 100
    y100 = Y(base)
    g.append(f'<line x1="{pl}" y1="{y100:.1f}" x2="{pl+iw}" y2="{y100:.1f}" stroke="#0A7A5E" stroke-width="1" stroke-dasharray="4 3" opacity="0.55"/>')
    # 日期刻度
    for k in range(5):
        i = int((n - 1) * k / 4)
        x = X(i)
        dt = series[0][2][i][0]
        g.append(f'<text x="{x:.1f}" y="{pt+ih+20}" font-size="10.5" fill="#8a9992" text-anchor="middle">{dt}</text>')
    # 数据线
    for label, color, pts in series:
        pth = " ".join(("M" if i == 0 else "L") + f"{X(i):.1f},{Y(v):.1f}" for i, (_, v) in enumerate(pts))
        g.append(f'<path d="{pth}" fill="none" stroke="{color}" stroke-width="2.1" stroke-linejoin="round"/>')
    # 图例
    lx = pl + 6
    for label, color, pts in series:
        g.append(f'<rect x="{lx}" y="{pt+2}" width="16" height="3" fill="{color}" rx="1.5"/>')
        g.append(f'<text x="{lx+21}" y="{pt+8}" font-size="12" fill="#333">{html.escape(label)}</text>')
        lx += 26 + len(label) * 8.2
    g.append('</svg>')
    return "\n".join(g)

def norm(eq):
    b = eq[0]["equity"]
    return [(e["date"], e["equity"] / b * 100) for e in eq]

etf_n, stk_n = norm(etf["equity"]), norm(stk["equity"])
chart = svg_line([(ETF, "#0A7A5E", etf_n), (STK, "#c0392b", stk_n)])

# 回撤图
def dd(eq):
    peak, out = -1e18, []
    for e in eq:
        peak = max(peak, e["equity"])
        out.append((e["date"], (e["equity"] / peak - 1) * 100))
    return out
dd_etf, dd_stk = dd(etf["equity"]), dd(stk["equity"])
def svg_dd(series, w=980, h=250, pad=(62, 18, 40, 58)):
    pl, pt, pr, pb = pad
    iw, ih = w - pl - pr, h - pt - pb
    allv = [v for _, _, pts in series for _, v in pts]
    lo, hi = min(allv) * 1.08, 0.0
    span = hi - lo
    n = max(len(pts) for _, _, pts in series)
    def X(i): return pl + iw * (i / max(n - 1, 1))
    def Y(v): return pt + ih * (1 - (v - lo) / span)
    g = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" font-family="-apple-system,sans-serif">']
    for k in range(5):
        v = lo + span * k / 4
        y = Y(v)
        g.append(f'<line x1="{pl}" y1="{y:.1f}" x2="{pl+iw}" y2="{y:.1f}" stroke="#e6ebe8"/>')
        g.append(f'<text x="{pl-8}" y="{y+4:.1f}" font-size="11" fill="#8a9992" text-anchor="end">{v:.0f}%</text>')
    for k in range(5):
        i = int((n - 1) * k / 4); x = X(i)
        g.append(f'<text x="{x:.1f}" y="{pt+ih+20}" font-size="10.5" fill="#8a9992" text-anchor="middle">{series[0][2][i][0]}</text>')
    for label, color, pts in series:
        pth = " ".join(("M" if i == 0 else "L") + f"{X(i):.1f},{Y(v):.1f}" for i, (_, v) in enumerate(pts))
        g.append(f'<path d="{pth}" fill="none" stroke="{color}" stroke-width="1.8"/>')
    lx = pl + 6
    for label, color, pts in series:
        g.append(f'<rect x="{lx}" y="{pt+2}" width="16" height="3" fill="{color}" rx="1.5"/>')
        g.append(f'<text x="{lx+21}" y="{pt+8}" font-size="12" fill="#333">{html.escape(label)}</text>')
        lx += 26 + len(label) * 8.2
    g.append('</svg>')
    return "\n".join(g)
ddchart = svg_dd([(ETF, "#0A7A5E", dd_etf), (STK, "#c0392b", dd_stk)])

# ---------- 表格 ----------
def kpi(label):
    s = d[label]["summary"]
    return s

def rows_per(label, is_etf):
    ps = d[label]["per_symbol"]
    out = []
    for c, v in sorted(ps.items(), key=lambda x: -x[1]["pnl"]):
        out.append((c, NAMES.get(c, c), v["n"], v["pnl"], v["win"] / v["n"] * 100))
    return out

def per_table(label, is_etf):
    r = ['<table><thead><tr><th>标的</th><th class="n">笔数</th><th class="n">累计盈亏</th><th class="n">胜率</th></tr></thead><tbody>']
    for c, n, k, pnl, wr in rows_per(label, is_etf):
        cls = "pos" if pnl > 0 else "neg"
        r.append(f'<tr><td><span class="code">{c}</span> {html.escape(n)}</td><td class="n">{k}</td>'
                 f'<td class="n {cls}">{pnl:+,.2f}</td><td class="n">{wr:.0f}%</td></tr>')
    r.append("</tbody></table>")
    return "\n".join(r)

# 高亮重合项
HL = {"600988", "002396", "000938"}

s_e, s_s = kpi(ETF), kpi(STK)
gen = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

HTML = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ETF 池 vs 个股池 · 三年对照回测</title>
<style>
:root{{--g:#0A7A5E;--gn:#00E47C;--gl:#b8f5d4;--w:#FFFFFF;--wa:#FAF9F8;--t:#333;--tm:#6b7d75;--ln:#e6ebe8}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--wa);color:var(--t);
 font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",Roboto,sans-serif;
 line-height:1.62;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1060px;margin:0 auto;padding:0 22px 70px}}
header{{background:var(--w);border-bottom:3px solid var(--g);padding:34px 0 26px;margin-bottom:0}}
h1{{margin:0 0 8px;font-size:25px;letter-spacing:-.3px;font-weight:700}}
h1 .tag{{font-size:12px;font-weight:600;color:var(--g);background:var(--gl);
 padding:3px 9px;border-radius:11px;vertical-align:middle;margin-left:9px;letter-spacing:0}}
.sub{{color:var(--tm);font-size:13px;margin:0}}
h2{{font-size:17px;margin:38px 0 13px;padding-left:11px;border-left:4px solid var(--g);font-weight:700}}
h3{{font-size:14.5px;margin:24px 0 9px;color:var(--g);font-weight:700}}
.card{{background:var(--w);border:1px solid var(--ln);border-radius:11px;padding:20px 22px;margin:15px 0}}
.warn{{background:#fff9e8;border:1px solid #f0d99a;border-left:4px solid #d99b1f}}
.warn h3{{color:#9a6b0c;margin-top:0}}
.ok{{background:#eefbf4;border:1px solid #b8f5d4;border-left:4px solid var(--g)}}
.ok h3{{margin-top:0}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin:9px 0}}
th{{text-align:left;padding:9px 10px;background:#f3f7f5;border-bottom:2px solid var(--g);
 font-weight:700;font-size:12px;color:var(--g);letter-spacing:.2px}}
td{{padding:8px 10px;border-bottom:1px solid var(--ln)}}
tr:last-child td{{border-bottom:none}}
.n{{text-align:right;font-variant-numeric:tabular-nums}}
.pos{{color:#0A7A5E;font-weight:600}}
.neg{{color:#c0392b;font-weight:600}}
.code{{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:11.5px;color:var(--tm)}}
.kpi{{display:grid;grid-template-columns:repeat(auto-fit,minmax(168px,1fr));gap:12px;margin:15px 0}}
.k{{background:var(--w);border:1px solid var(--ln);border-radius:10px;padding:14px 16px}}
.k .lb{{font-size:11.5px;color:var(--tm);margin-bottom:5px;letter-spacing:.2px}}
.k .v{{font-size:22px;font-weight:700;font-variant-numeric:tabular-nums;line-height:1.2}}
.k .d{{font-size:11.5px;color:var(--tm);margin-top:3px}}
.hl{{background:#fff2f0!important}}
.hl td:first-child::after{{content:" ⚠ 实盘同款";font-size:10.5px;color:#c0392b;font-weight:600}}
.chartbox{{background:var(--w);border:1px solid var(--ln);border-radius:11px;padding:16px 12px 8px;margin:14px 0}}
.note{{font-size:12.5px;color:var(--tm)}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
@media(max-width:760px){{.two{{grid-template-columns:1fr}}}}
footer{{margin-top:44px;padding-top:18px;border-top:1px solid var(--ln);font-size:12px;color:var(--tm)}}
ul{{padding-left:20px;margin:8px 0}} li{{margin:5px 0}}
.pill{{display:inline-block;font-size:11px;padding:2px 8px;border-radius:9px;background:var(--gl);color:var(--g);font-weight:600}}
</style></head><body>
<header><div class="wrap">
<h1>ETF 池 vs 个股池 · 三年对照回测<span class="tag">日线代理口径</span></h1>
<p class="sub">窗口 2023-09-14 ~ 2026-09-14（726 交易日）｜初始资金 13,822.47 元｜引擎 v4 · 同一规则同一口径</p>
</div></header>
<div class="wrap">

<div class="card warn">
<h3>⚠️ 先读这一段：口径声明</h3>
<p>本测试采用 <b>日线代理</b>口径（D-1 收盘信号 + D 日开盘执行）。原因：ETF 无 5 分钟历史数据（baostock 的 ETF 数据仅覆盖 2026-01-05 起）。</p>
<p><b>该口径对个股不友好 —— 个股池在 5 分钟口径下为 +11.73%，本口径下为 −5.84%，相差 17.6 个百分点。</b></p>
<p style="margin-bottom:0"><b>因此：绝对收益数字不可作为预期外推；本文只支撑「同口径下的结构性差异」结论</b>（回撤、交易频次、摩擦成本）。</p>
</div>

<h2>核心结果</h2>
<div class="kpi">
<div class="k"><div class="lb">ETF 池 · 累计收益</div><div class="v pos">{s_e['ret_pct']:+.2f}%</div><div class="d">期末 {s_e['final']:,.2f}</div></div>
<div class="k"><div class="lb">个股池 · 累计收益</div><div class="v neg">{s_s['ret_pct']:+.2f}%</div><div class="d">期末 {s_s['final']:,.2f}</div></div>
<div class="k"><div class="lb">最大回撤（ETF / 个股）</div><div class="v">{s_e['mdd_pct']:.1f}% <span style="font-size:15px;color:#8a9992">/</span> <span class="neg">{s_s['mdd_pct']:.1f}%</span></div><div class="d">ETF 少回撤 {abs(s_s['mdd_pct'])-abs(s_e['mdd_pct']):.1f} pp</div></div>
<div class="k"><div class="lb">交易笔数（ETF / 个股）</div><div class="v">{s_e['trades']} <span style="font-size:15px;color:#8a9992">/</span> {s_s['trades']}</div><div class="d">个股多 {s_s['trades']-s_e['trades']} 笔</div></div>
<div class="k"><div class="lb">胜率（ETF / 个股）</div><div class="v">{s_e['win_rate']:.1f}% <span style="font-size:15px;color:#8a9992">/</span> {s_s['win_rate']:.1f}%</div><div class="d">+{s_e['win_rate']-s_s['win_rate']:.1f} pp</div></div>
<div class="k"><div class="lb">利润因子（ETF / 个股）</div><div class="v">{s_e['profit_factor']:.3f} <span style="font-size:15px;color:#8a9992">/</span> <span class="neg">{s_s['profit_factor']:.4f}</span></div><div class="d">&gt;1 才盈利</div></div>
</div>

<div class="card">
<table><thead><tr><th>指标</th><th class="n">ETF 池（9只）</th><th class="n">个股池（12只）</th><th class="n">差异</th></tr></thead><tbody>
<tr><td>累计收益</td><td class="n pos">{s_e['ret_pct']:+.2f}%</td><td class="n neg">{s_s['ret_pct']:+.2f}%</td><td class="n"><b>{s_e['ret_pct']-s_s['ret_pct']:+.2f} pp</b></td></tr>
<tr><td>最大回撤</td><td class="n pos">{s_e['mdd_pct']:.2f}%</td><td class="n neg">{s_s['mdd_pct']:.2f}%</td><td class="n"><b>小 {abs(s_s['mdd_pct'])-abs(s_e['mdd_pct']):.2f} pp</b></td></tr>
<tr><td>已平仓笔数</td><td class="n">{s_e['trades']}</td><td class="n">{s_s['trades']}</td><td class="n">少 {s_s['trades']-s_e['trades']} 笔</td></tr>
<tr><td>胜率</td><td class="n pos">{s_e['win_rate']:.2f}%</td><td class="n">{s_s['win_rate']:.2f}%</td><td class="n">+{s_e['win_rate']-s_s['win_rate']:.2f} pp</td></tr>
<tr><td>利润因子</td><td class="n pos">{s_e['profit_factor']:.3f}</td><td class="n neg">{s_s['profit_factor']:.4f}</td><td class="n">—</td></tr>
<tr><td>手续费合计</td><td class="n">{s_e['fee_total']:,.2f}</td><td class="n">{s_s['fee_total']:,.2f}</td><td class="n">省 {s_s['fee_total']-s_e['fee_total']:,.2f} 元</td></tr>
<tr><td>滑点成本合计</td><td class="n">{s_e['slip_total']:,.2f}</td><td class="n">{s_s['slip_total']:,.2f}</td><td class="n">—</td></tr>
</tbody></table>
</div>

<h2>权益曲线（起点归一 = 100）</h2>
<div class="chartbox">{chart}</div>

<h2>回撤曲线</h2>
<div class="chartbox">{ddchart}</div>

<h2>逐标的表现</h2>
<div class="two">
<div><h3>ETF 池（9 只）</h3>{per_table(ETF, True)}</div>
<div><h3>个股池（12 只）</h3>{per_table(STK, False)}</div>
</div>

<div class="card warn" style="margin-top:20px">
<h3>⚠️ 一个无法忽视的重合</h3>
<p>个股池回测中<b>亏损最大的三只</b>是：</p>
<ul>
<li><b>600988 赤峰黄金</b> −1,415.08（8 笔，胜率 12%）← 最大亏损源</li>
<li><b>002396 星网锐捷</b> −892.40（10 笔，胜率 30%）</li>
<li><b>000938 紫光股份</b> −788.45（13 笔，胜率 38%）</li>
</ul>
<p style="margin-bottom:0">这三只<b>恰好也是实盘中已实现亏损的标的</b>（赤峰于 2026-09-24 触发硬止损、星网与紫光此前均已止损）。
回测在三年数据上重复了同样的结果 —— <b>这不是巧合，而是同一类买点在同类标的上反复失效。</b></p>
</div>

<h2>结论</h2>
<div class="card ok">
<h3>✅ 可靠（结构性差异，不依赖入场时点精确性）</h3>
<ul>
<li><b>回撤显著更小</b>：−22.44% vs −32.91%（小 10.5 pp）</li>
<li><b>交易更少、摩擦更低</b>：50 笔 vs 82 笔；手续费省 326 元</li>
<li><b>胜率与利润因子占优</b>：52.0% vs 41.5%；1.082 vs 0.902</li>
<li><b>规避个股特有风险</b>：不会出现母子公司重复下注（星网↔锐捷）、单只停牌（紫光）等</li>
</ul>
</div>
<div class="card warn">
<h3>❌ 不可靠 / 必须承认的边界</h3>
<ul>
<li><b>「ETF 能多赚 11 个点」不成立</b> —— 个股在 5 分钟口径下为 +11.73%，两种口径差异说明绝对数字受口径主导</li>
<li><b>ETF 拿的是行业平均</b>，不会有单只爆发（如南山铝业 +2,087 那类）</li>
<li><b>换 ETF 完全不能解决「追高」</b> —— 防线是规则（条件②防追高闸门），不是标的类型</li>
<li>ETF 无 5 分钟数据，无法做盘中同刻量比验证；窗口未含分红再投资的精确处理</li>
</ul>
</div>

<h2>方法与可复现</h2>
<div class="card">
<table><tbody>
<tr><td style="width:180px">引擎</td><td><span class="code">results/confirmed_policy_3y_20260914/confirmed_policy_engine.py</span>（v4，参数单一来源 <span class="code">strategies/buy_policy.py</span>）</td></tr>
<tr><td>执行脚本</td><td><span class="code">run_etf_vs_stock_proxy.py</span>；代理引擎 <span class="code">run_daily_proxy.py</span></td></tr>
<tr><td>规则</td><td>BUY-LOW-v1（MA60 上行 + (H20−价)/ATR14 ∈ [2.5,4.5] + 缩量&lt;0.80）+ SELL-POLICY-v1.0</td></tr>
<tr><td>费率</td><td>佣金 max(额×0.00025, 5) + 印花税 0.05%（仅卖出）+ 过户费 0.00001%；滑点 0.1%</td></tr>
<tr><td>数据</td><td>日线（ETF：新浪 800 根；个股：baostock 前复权）</td></tr>
<tr><td>数据文件</td><td><span class="code">etf_vs_stock_dailyproxy.json</span>（含 726 点权益曲线 + 全部成交明细）</td></tr>
</tbody></table>
</div>

<footer>
生成时间 {gen}　｜　本报告为历史回放模拟，<b>不构成投资建议，不能预测未来收益</b>。<br>
所有数字来自确定性脚本执行，无人工调整；口径声明见文首。⚠️ 日线代理非原规则完整回测。
</footer>
</div></body></html>
"""

out = D / "etf_vs_stock_report.html"
out.write_text(HTML, encoding="utf-8")
print("已生成: %s  (%d 字节)" % (out, len(HTML)))
