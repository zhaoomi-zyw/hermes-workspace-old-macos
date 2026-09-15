"""
积极版 3年回测 + 未来1年蒙特卡洛 → HTML
生成 results/agg_report.html, 供局域网访问
"""
import sys, json
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

def json_dumps(x):
    return json.dumps(x)

def main():
    data = json.load(open("results/agg_3y_data.json"))
    mc = json.load(open("results/mc_1y_chifeng.json"))
    q = mc["q"]; up = mc["up_prob"]

    # 汇总排序
    items = sorted(data.values(), key=lambda x: -x["agg_ret"])
    sum_rows = ""
    for i, it in enumerate(items, 1):
        col = "#0A7A5E" if it["agg_ret"] >= 0 else "#C0392B"
        bhcol = "#0A7A5E" if it["bh_ret"] >= 0 else "#C0392B"
        beat = "✅跑赢" if it["agg_ret"] > it["plana_ret"] else "="
        sum_rows += f"""<tr><td>{i}</td><td><b>{it['name']}</b><br><span class='sub'>{list(data.keys())[list(data.values()).index(it)]}</span></td>
<td style='color:{col};font-weight:600'>{it['agg_ret']:+.1f}%</td><td style='color:#888'>{it['plana_ret']:+.1f}%</td>
<td style='color:{bhcol}'>{it['bh_ret']:+.1f}%</td><td>{it['agg_dd']:.1f}%</td><td>{it['plana_dd']:.1f}%</td>
<td>{it['agg_sharpe']:.2f}</td><td>{it['agg_win']:.0f}%</td><td>{it['agg_trades']}</td><td>{beat}</td></tr>"""
    avg_agg = sum(i["agg_ret"] for i in items)/len(items)
    avg_plana = sum(i["plana_ret"] for i in items)/len(items)
    avg_bh = sum(i["bh_ret"] for i in items)/len(items)
    n_win = sum(1 for i in items if i["agg_ret"]>0)
    n_beat = sum(1 for i in items if i["agg_ret"]>i["bh_ret"])

    # 明细
    detail = ""
    for it in sorted(items, key=lambda x:-x["agg_ret"]):
        rc = "#0A7A5E" if it["agg_ret"]>=0 else "#C0392B"
        arrow = "↑" if it["agg_ret"]>it["bh_ret"] else "↓"
        # 交易明细
        tr = ""
        for t in it["trades"]:
            tcol = "#0A7A5E" if t["pnl"]>0 else "#C0392B"
            tr += f"<tr><td>{t['date']}</td><td>{t['reason']}</td><td>{t['price']:.2f}</td><td>{t['shares']}</td><td style='color:{tcol}'>{t['pnl']:+d}</td><td style='color:{tcol}'>{t['pct']:+.1f}%</td><td>{t['hold']}天</td></tr>"
        detail += f"""
<div class="detail">
<h3>{it['name']} <span style="float:right;color:{rc};font-size:15px">积极版 {it['agg_ret']:+.1f}% {arrow}</span></h3>
<div class="stat">vs 方案A {it['plana_ret']:+.1f}% ｜ 买入持有 {it['bh_ret']:+.1f}% ｜ 回撤积极{it['agg_dd']:.1f}%/方案A{it['plana_dd']:.1f}% ｜ 夏普{it['agg_sharpe']:.2f} ｜ 胜率{it['agg_win']:.0f}% ｜ {it['agg_trades']}笔</div>
<canvas id="c_{list(data.keys())[list(data.values()).index(it)]}" height="190"></canvas>
<details><summary style="cursor:pointer;color:#0A7A5E;font-size:13px;margin-top:8px">展开交易明细({len(it['trades'])}笔)</summary>
<table class="trade-tbl"><tr><th>日期</th><th>原因</th><th>价格</th><th>股数</th><th>盈亏</th><th>%</th><th>持仓</th></tr>{tr}</table></details>
</div>"""

    gen = datetime.now().strftime('%Y-%m-%d %H:%M')
    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>积极版策略 3年回测 + 未来1年模拟</title><style>
body{{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#fff;color:#333;margin:0;padding:24px;line-height:1.6}}
.wrap{{max-width:1080px;margin:0 auto}}
h1{{color:#0A7A5E;font-size:24px;border-bottom:3px solid #00E47C;padding-bottom:10px}}
h2{{color:#0A7A5E;font-size:19px;margin-top:30px}}
.meta{{color:#888;font-size:13px}}
.cards{{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0}}
.card{{flex:1;min-width:140px;background:#FAF9F8;border:1px solid #eee;border-radius:10px;padding:13px;text-align:center}}
.card .v{{font-size:20px;font-weight:700;color:#0A7A5E}}.card .l{{font-size:11px;color:#888}}
table{{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0}}
th{{background:#0A7A5E;color:#fff;padding:8px;text-align:left}}
td{{padding:7px;border-bottom:1px solid #eee}}tr:nth-child(even){{background:#f9fdfb}}
.sub{{color:#aaa;font-size:11px;font-weight:400}}
.note{{background:#eefaf4;border-left:4px solid #0A7A5E;padding:12px 16px;font-size:13px;border-radius:4px}}
.warn{{background:#fdf3ef;border-left:4px solid #C0392B;padding:12px 16px;font-size:13px;border-radius:4px}}
.detail{{background:#FAF9F8;border:1px solid #eee;border-radius:10px;padding:14px;margin:14px 0}}
.detail h3{{color:#0A7A5E;margin:0 0 4px;font-size:16px}}.detail .stat{{font-size:12px;color:#666;margin-bottom:8px}}
.trade-tbl{{font-size:11.5px;width:100%}}.trade-tbl td,.trade-tbl th{{padding:4px 6px}}
.mc{{background:#fff;border:1px solid #0A7A5E33;border-radius:10px;padding:16px;margin:14px 0}}
</style></head><body><div class="wrap">
<h1>📈 积极版趋势策略 · 3年回测 + 未来1年模拟</h1>
<div class="meta">数据源: 同花顺官方API(前复权)｜回测: 2023-09-06→2026-09-04｜初始¥1万｜生成 {gen}｜本报告可在局域网内由 HTTP 服务访问</div>

<div class="cards">
<div class="card"><div class="v">{n_win}/{len(items)}</div><div class="l">积极版盈利标的</div></div>
<div class="card"><div class="v">{avg_agg:+.1f}%</div><div class="l">积极版平均收益</div></div>
<div class="card"><div class="v">{avg_plana:+.1f}%</div><div class="l">方案A平均</div></div>
<div class="card"><div class="v">{avg_bh:+.1f}%</div><div class="l">买入持有均值</div></div>
</div>

<div class="note"><b>积极版规则</b>：买入=左侧低吸(回撤≥5%+站上MA60+DSA A/B+接近MA5/MA10) 或 右侧放量突破(破20日压力+量比≥1.5)。持仓=硬止损-7%；浮盈≥+8%前不因回调离场；浮盈≥+8%后破MA60或回撤10%离场；最长60天。</div>
<div class="warn"><b>⚠️ 诚实声明</b>：积极版把9只平均从+3.3%(方案A)提升到<b>{avg_agg:+.1f}%</b>，代价是回撤扩大(约-11%→-33%)。它不是"每只都赚"，紫光等趋势弱股仍可能亏。本页权益曲线会直观显示每只的积极版(绿线)vs买入持有(灰虚线)。</div>

<h2>一、汇总对比（积极版 vs 方案A vs 买入持有）</h2>
<table><tr><th>#</th><th>标的</th><th>积极版</th><th>方案A</th><th>买入持有</th><th>积极回撤</th><th>方案A回撤</th><th>夏普</th><th>胜率</th><th>交易</th><th>跑赢方案A</th></tr>
{sum_rows}
<tr style="background:#eefaf4;font-weight:700"><td colspan="2">平均</td><td>{avg_agg:+.1f}%</td><td>{avg_plana:+.1f}%</td><td>{avg_bh:+.1f}%</td><td colspan="6"></td></tr></table>

<h2>二、未来1年蒙特卡洛模拟（赤峰黄金，非预测）</h2>
<div class="mc">
<div class="note" style="margin:0"><b>方法说明</b>：基于赤峰黄金近5年真实日收益率分布(日均+0.14%, 日波动3.01%)，随机抽样模拟 <b>2000条</b>未来1年(250交易日)股价路径。这是<b>概率情景模拟</b>，不是预测——反映"若历史波动规律延续，一年后大致落在哪个区间"。起点=现价45.69。</div>
<div class="cards" style="margin-top:12px">
<div class="card"><div class="v">{q[0]:.0f}</div><div class="l">5%悲观位(一年后指数)</div></div>
<div class="card"><div class="v">{q[2]:.0f}</div><div class="l">中位数(50%)</div></div>
<div class="card"><div class="v">{q[4]:.0f}</div><div class="l">95%乐观位</div></div>
<div class="card"><div class="v">{up}%</div><div class="l">上涨概率</div></div>
</div>
<table><tr><th>情景</th><th>悲观(P5)</th><th>中位数</th><th>乐观(P95)</th></tr>
<tr><td>一年后赤峰股价(起点45.69)</td><td style="color:#C0392B">{45.69*q[0]/100:.1f}元</td><td>{45.69*q[2]/100:.1f}元</td><td style="color:#0A7A5E">{45.69*q[4]/100:.1f}元</td></tr>
<tr><td>对应涨跌</td><td style="color:#C0392B">{q[0]-100:+.0f}%</td><td>{q[2]-100:+.0f}%</td><td style="color:#0A7A5E">{q[4]-100:+.0f}%</td></tr></table>
<div class="warn"><b>⚠️ 蒙特卡洛≠承诺</b>：它假设未来波动规律与过去5年相似。若发生系统性行情(如黄金大牛或崩盘)，实际可能落在区间外。P5=-37%提醒你尾部风险真实存在——所以积极版保留-7%止损是对的。</div>
</div>

<h2>三、个股明细（权益曲线 + 交易）</h2>
{detail}
<p style="color:#aaa;font-size:12px;margin-top:26px">本报告由 Hermes 生成，仅供量化研究参考，非投资建议。历史回测与模拟不代表未来表现。</p>
</div>
<script>
const CH = {{"""
    for code, it in data.items():
        html += f"{code}: {{ eq: {json_dumps(it['eq'])}, bh: {json_dumps(it['bh_eq'])}, dates: {json_dumps(it['dates'])} }},\n"
    html += """};
function draw(id){
  const d=CH[id]; const cv=document.getElementById(id); if(!cv) return;
  const W=cv.clientWidth||880,H=190,ctx=cv.getContext('2d'); ctx.clearRect(0,0,W,H);
  const pad={l:38,r:8,t:8,b:20};
  let all=d.eq.concat(d.bh),mx=Math.max(...all),mn=Math.min(...all);const sp=(mx-mn)||1;mn-=sp*0.05;mx+=sp*0.05;
  const X=i=>pad.l+i*(W-pad.l-pad.r)/(d.dates.length-1||1);
  const Y=v=>pad.t+(1-(v-mn)/(mx-mn))*(H-pad.t-pad.b);
  ctx.strokeStyle='#eee';for(let g=0;g<=3;g++){const gy=pad.t+g*(H-pad.t-pad.b)/3;ctx.beginPath();ctx.moveTo(pad.l,gy);ctx.lineTo(W-pad.r,gy);ctx.stroke();ctx.fillStyle='#999';ctx.font='10px sans-serif';ctx.fillText((mx-g*(mx-mn)/3).toFixed(0),2,gy+4);}
  ctx.strokeStyle='#0A7A5E';ctx.lineWidth=2;ctx.beginPath();d.eq.forEach((v,i)=>i?ctx.lineTo(X(i),Y(v)):ctx.moveTo(X(i),Y(v)));ctx.stroke();
  ctx.strokeStyle='#bbb';ctx.lineWidth=1.5;ctx.setLineDash([4,4]);ctx.beginPath();d.bh.forEach((v,i)=>i?ctx.lineTo(X(i),Y(v)):ctx.moveTo(X(i),Y(v)));ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#0A7A5E';ctx.fillRect(pad.l,H-18,12,3);ctx.fillStyle='#333';ctx.fillText('积极版',pad.l+15,H-22);
  ctx.strokeStyle='#bbb';ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(pad.l+60,H-20);ctx.lineTo(pad.l+72,H-20);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#333';ctx.fillText('买入持有',pad.l+76,H-22);
}
window.addEventListener('resize',()=>Object.keys(CH).forEach(draw));
document.addEventListener('DOMContentLoaded',()=>Object.keys(CH).forEach(draw));
</script></body></html>"""
    out = Path("results/agg_report.html")
    out.write_text(html, encoding="utf-8")
    print(f"生成: {out} ({len(html)/1024:.0f}KB)")
    return str(out)

if __name__ == "__main__":
    main()
