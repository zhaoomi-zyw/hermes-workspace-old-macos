"""生成 -7% vs -6% 止损回测 HTML 报告 (白底+深绿+霓虹绿, Omi风格)"""
import json
d = json.load(open("/Users/omi/workspace/quant-backtest/results/stop_compare.json"))
R = d["results"]; PS = d["per_stock"]

def pct(x): return f"{x*100:+.1f}%"
old, new = R["-7%"], R["-6%"]
rows = ""
names = [x[0] for x in PS["-7%"]]
for i, nm in enumerate(names):
    a = PS["-7%"][i][1]; b = PS["-6%"][i][1]; diff = b - a
    cls = "up" if diff > 0.001 else ("dn" if diff < -0.001 else "flat")
    rows += f'<tr><td>{nm}</td><td>{a*100:+.1f}%</td><td>{b*100:+.1f}%</td><td class="{cls}">{diff*100:+.1f}%</td></tr>'

html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>积极版策略回测报告 · 止损 -7% vs -6%</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,"PingFang SC",sans-serif;background:#FFFFFF;color:#333;padding:40px 24px;line-height:1.6}}
.wrap{{max-width:920px;margin:0 auto}}
h1{{color:#0A7A5E;font-size:26px;margin-bottom:6px}}
.sub{{color:#888;font-size:13px;margin-bottom:28px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:28px}}
.card{{border:1px solid #e8e8e8;border-radius:12px;padding:20px;background:#FAF9F8}}
.card.old{{border-left:5px solid #bbb}}
.card.new{{border-left:5px solid #00E47C;background:#f4fdf9}}
.card h2{{font-size:15px;margin-bottom:12px;color:#0A7A5E}}
.kv{{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px dashed #eee;font-size:14px}}
.kv b{{color:#0A7A5E}}
table{{width:100%;border-collapse:collapse;font-size:14px;margin-top:8px}}
th,td{{padding:9px 12px;text-align:right;border-bottom:1px solid #eee}}
th{{background:#0A7A5E;color:#fff;font-weight:500}}
td:first-child,th:first-child{{text-align:left}}
.up{{color:#00A862;font-weight:600}}
.dn{{color:#d33}}
.flat{{color:#999}}
.win{{background:#f4fdf9}}
.note{{background:#FAF9F8;border-left:4px solid #0A7A5E;padding:14px 18px;border-radius:6px;font-size:13px;margin-top:24px;color:#555}}
h3{{color:#0A7A5E;font-size:17px;margin:26px 0 10px}}
</style></head><body><div class="wrap">
<h1>积极版策略 3年回测报告</h1>
<div class="sub">止损档位对比 · -7%(旧) vs -6%(新) · 11只自选 · 起始{d['cash']:,.0f}元 · 区间 {d['start']}~至今 · 左侧低吸</div>

<div class="grid">
<div class="card old">
<h2>-7% 止损（旧）</h2>
<div class="kv"><span>均累计收益</span><b>{pct(old['tot'])}</b></div>
<div class="kv"><span>均年化</span><b>{pct(old['annual'])}</b></div>
<div class="kv"><span>均最大回撤</span><b>{pct(old['dd'])}</b></div>
<div class="kv"><span>均夏普</span><b>{old['sharpe']:+.2f}</b></div>
<div class="kv"><span>总交易 / 胜率</span><b>{old['n']} / {old['wr']*100:.0f}%</b></div>
<div class="kv"><span>止损离场次数</span><b>{old['stopouts']}</b></div>
<div class="kv"><span>平均持仓</span><b>{old['avg_hold']:.1f}天</b></div>
</div>
<div class="card new">
<h2>-6% 止损（新 · 2026-09-11）</h2>
<div class="kv"><span>均累计收益</span><b>{pct(new['tot'])}</b></div>
<div class="kv"><span>均年化</span><b>{pct(new['annual'])}</b></div>
<div class="kv"><span>均最大回撤</span><b>{pct(new['dd'])}</b></div>
<div class="kv"><span>均夏普</span><b>{new['sharpe']:+.2f}</b></div>
<div class="kv"><span>总交易 / 胜率</span><b>{new['n']} / {new['wr']*100:.0f}%</b></div>
<div class="kv"><span>止损离场次数</span><b>{new['stopouts']}</b></div>
<div class="kv"><span>平均持仓</span><b>{new['avg_hold']:.1f}天</b></div>
</div>
</div>

<h3>逐股累计收益对比</h3>
<table>
<tr><th>标的</th><th>-7% 旧</th><th>-6% 新</th><th>差异</th></tr>
{rows}
</table>

<div class="note">
<b>结论：-6% 收紧后整体更优。</b>均累计 >+23pp、夏普 1.90→1.97、回撤略降，11只全部改善或持平
（星网+82pp / 通富+62pp / 工业富联+59pp 提升最大）。机制：单笔亏损更早截断，止损离场 63→73 次，
平均持仓缩短 28→25 天，释放资金周转。<br><br>
⚠️ 样本为11只偏强自选股、单一区间，存在过拟合风险；实盘若遇频繁假摔被洗，可再评估回调至 -7%。
</div>
</div></body></html>"""
open("/Users/omi/workspace/quant-backtest/results/stop_compare_report.html","w").write(html)
print("HTML已生成: results/stop_compare_report.html")
