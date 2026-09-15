"""
积极版 3年回测 + 未来1年蒙特卡洛(全部自选) → HTML
生成 results/agg_report.html, 供局域网访问
"""
import sys, json
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent))

def main():
    data = json.load(open("results/agg_3y_data.json"))
    mc = json.load(open("results/mc_1y_all.json"))

    items = sorted(data.values(), key=lambda x: -x["agg_ret"])
    sum_rows = ""
    for i, it in enumerate(items, 1):
        col = "#0A7A5E" if it["agg_ret"] >= 0 else "#C0392B"
        bhcol = "#0A7A5E" if it["bh_ret"] >= 0 else "#C0392B"
        beat = "YES" if it["agg_ret"] > it["plana_ret"] else "="
        code = [k for k, v in data.items() if v is it][0]
        sum_rows += "<tr><td>%d</td><td><b>%s</b><br><span class='sub'>%s</span></td><td style='color:%s;font-weight:600'>%+.1f%%</td><td style='color:#888'>%+.1f%%</td><td style='color:%s'>%+.1f%%</td><td>%.1f%%</td><td>%.1f%%</td><td>%.2f</td><td>%.0f%%</td><td>%d</td><td>%s</td></tr>" % (
            i, it["name"], code, col, it["agg_ret"], it["plana_ret"], bhcol, it["bh_ret"],
            it["agg_dd"], it["plana_dd"], it["agg_sharpe"], it["agg_win"], it["agg_trades"], beat)
    avg_agg = sum(i["agg_ret"] for i in items)/len(items)
    avg_plana = sum(i["plana_ret"] for i in items)/len(items)
    avg_bh = sum(i["bh_ret"] for i in items)/len(items)
    n_win = sum(1 for i in items if i["agg_ret"] > 0)

    mc_rows = ""
    for code, m in mc.items():
        col = "#0A7A5E" if m["q"][2] > 100 else "#C0392B"
        mc_rows += "<tr><td><b>%s</b><br><span class='sub'>%s</span></td><td style='color:#C0392B'>%+.0f%%</td><td>%+.0f%%</td><td style='color:%s;font-weight:600'>%+.0f%%</td><td>%+.0f%%</td><td style='color:#0A7A5E'>%+.0f%%</td><td>%d%%</td><td>%.1f%%</td></tr>" % (
            m["name"], code, m["q"][0]-100, m["q"][1]-100, col, m["q"][2]-100, m["q"][3]-100, m["q"][4]-100, m["up_prob"], m["daily_vol"])

    detail = ""
    for it in sorted(items, key=lambda x: -x["agg_ret"]):
        rc = "#0A7A5E" if it["agg_ret"] >= 0 else "#C0392B"
        code = [k for k, v in data.items() if v is it][0]
        tr = ""
        for t in it["trades"]:
            tcol = "#0A7A5E" if t["pnl"] > 0 else "#C0392B"
            tr += "<tr><td>%s</td><td>%s</td><td>%.2f</td><td>%d</td><td style='color:%s'>%+d</td><td style='color:%s'>%+.1f%%</td><td>%d天</td></tr>" % (
                t["date"], t["reason"], t["price"], t["shares"], tcol, t["pnl"], tcol, t["pct"], t["hold"])
        detail += """
<div class="detail">
<h3>%s <span style="float:right;color:%s;font-size:15px">积极版 %+.1f%%</span></h3>
<div class="stat">vs 方案A %+.1f%% | 买入持有 %+.1f%% | 回撤积极%.1f%%/方案A%.1f%% | 夏普%.2f | 胜率%.0f%% | %d笔</div>
<canvas id="c_%s" height="190"></canvas>
<details><summary style="cursor:pointer;color:#0A7A5E;font-size:13px;margin-top:8px">展开交易明细(%d笔)</summary>
<table class="trade-tbl"><tr><th>日期</th><th>原因</th><th>价格</th><th>股数</th><th>盈亏</th><th>%%</th><th>持仓</th></tr>%s</table></details>
</div>""" % (it["name"], rc, it["agg_ret"], it["plana_ret"], it["bh_ret"], it["agg_dd"], it["plana_dd"], it["agg_sharpe"], it["agg_win"], it["agg_trades"], code, len(it["trades"]), tr)

    # JS 权益数据
    js_charts = ""
    for code, it in data.items():
        js_charts += "%s:{eq:%s,bh:%s,dates:%s},\n" % (
            code, json.dumps(it["eq"]), json.dumps(it["bh_eq"]), json.dumps(it["dates"]))

    gen = datetime.now().strftime('%Y-%m-%d %H:%M')
    # HTML模板用 @@VAR@@ 占位 + % (CSS花括号不需转义)
    tmpl = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>积极版 3年回测 + 未来1年模拟(全部自选)</title><style>
body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#fff;color:#333;margin:0;padding:24px;line-height:1.6}
.wrap{max-width:1080px;margin:0 auto}
h1{color:#0A7A5E;font-size:24px;border-bottom:3px solid #00E47C;padding-bottom:10px}
h2{color:#0A7A5E;font-size:19px;margin-top:30px}
.meta{color:#888;font-size:13px}
.cards{display:flex;gap:14px;flex-wrap:wrap;margin:14px 0}
.card{flex:1;min-width:140px;background:#FAF9F8;border:1px solid #eee;border-radius:10px;padding:13px;text-align:center}
.card .v{font-size:20px;font-weight:700;color:#0A7A5E}.card .l{font-size:11px;color:#888}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0}
th{background:#0A7A5E;color:#fff;padding:8px;text-align:left}
td{padding:7px;border-bottom:1px solid #eee}tr:nth-child(even){background:#f9fdfb}
.sub{color:#aaa;font-size:11px;font-weight:400}
.note{background:#eefaf4;border-left:4px solid #0A7A5E;padding:12px 16px;font-size:13px;border-radius:4px}
.warn{background:#fdf3ef;border-left:4px solid #C0392B;padding:12px 16px;font-size:13px;border-radius:4px}
.detail{background:#FAF9F8;border:1px solid #eee;border-radius:10px;padding:14px;margin:14px 0}
.detail h3{color:#0A7A5E;margin:0 0 4px;font-size:16px}.detail .stat{font-size:12px;color:#666;margin-bottom:8px}
.trade-tbl{font-size:11.5px;width:100%}.trade-tbl td,.trade-tbl th{padding:4px 6px}
.mc{background:#fff;border:1px solid #0A7A5E33;border-radius:10px;padding:16px;margin:14px 0}
</style></head><body><div class="wrap">
<h1>积极版趋势策略 - 3年回测 + 未来1年模拟(全部自选)</h1>
<div class="meta">数据源: 同花顺官方API(前复权) | 回测: 2023-09-06 -> 2026-09-04 | 初始1万 | 生成 @@GEN@@ | 局域网 HTTP 可访问</div>
<div class="cards">
<div class="card"><div class="v">@@NWIN@@/9</div><div class="l">积极版盈利标的</div></div>
<div class="card"><div class="v">@@AVG_AGG@@</div><div class="l">积极版平均收益</div></div>
<div class="card"><div class="v">@@AVG_PLANA@@</div><div class="l">方案A平均</div></div>
<div class="card"><div class="v">@@AVG_BH@@</div><div class="l">买入持有均值</div></div>
</div>
<div class="note"><b>积极版规则</b>: 买入=左侧低吸(回撤>=5%+站上MA60+DSA A/B+接近MA5/MA10) 或 右侧放量突破(破20日压力+量比>=1.5)。持仓=硬止损-7%; 浮盈>=+8%前不因回调离场; 浮盈>=+8%后破MA60或回撤10%离场; 最长60天。</div>
<div class="warn"><b>诚实声明</b>: 积极版把9只平均从+3.3%(方案A)提升到 @@AVG_AGG@@, 代价是回撤扩大(-11%到-33%)。非每只都赚, 趋势弱股仍可能亏。</div>
<h2>一、汇总对比(积极版 vs 方案A vs 买入持有)</h2>
<table><tr><th>#</th><th>标的</th><th>积极版</th><th>方案A</th><th>买入持有</th><th>积极回撤</th><th>方案A回撤</th><th>夏普</th><th>胜率</th><th>交易</th><th>跑赢</th></tr>
@@SUM_ROWS@@
<tr style="background:#eefaf4;font-weight:700"><td colspan="2">平均</td><td>@@AVG_AGG@@</td><td>@@AVG_PLANA@@</td><td>@@AVG_BH@@</td><td colspan="6"></td></tr></table>
<h2>二、未来1年蒙特卡洛模拟(全部9只, 非预测)</h2>
<div class="mc">
<div class="note" style="margin:0"><b>方法</b>: 每只用近5年真实日收益率分布随机抽样2000条未来1年(250交易日)路径。表内为一年后涨跌幅概率分位, 非预测。P5=悲观, P50=中位, P95=乐观。</div>
<table style="margin-top:10px"><tr><th>标的</th><th>P5悲观</th><th>P25</th><th>P50中位</th><th>P75</th><th>P95乐观</th><th>上涨概率</th><th>日波动</th></tr>
@@MC_ROWS@@
<tr style="background:#eefaf4"><td colspan="8"><b>解读</b>: 中位数>0且上涨概率高(工业富联83%/亨通82%/中天79%)的标的上涨倾向更强; 但每只P5都为负(-28%~-51%), 尾部回撤风险真实存在——这是保留-7%止损的原因。</td></tr></table>
<div class="warn"><b>蒙特卡洛非承诺</b>: 假设未来波动规律与过去5年相似。若发生系统性行情(大牛或崩盘)可能落在区间外。基于日收益独立抽样, 未计入宏观/政策/黑天鹅。</div>
</div>
<h2>三、个股明细(权益曲线 + 交易)</h2>
@@DETAIL@@
<p style="color:#aaa;font-size:12px;margin-top:26px">本报告由 Hermes 生成, 仅供量化研究参考, 非投资建议。历史回测与模拟不代表未来表现。</p>
</div>
<script>
var CH={@@JS_CHARTS@@};
function draw(id){var d=CH[id],cv=document.getElementById(id);if(!cv)return;var W=cv.clientWidth||880,H=190,ctx=cv.getContext('2d');ctx.clearRect(0,0,W,H);
var pad={l:38,r:8,t:8,b:20},all=d.eq.concat(d.bh),mx=Math.max.apply(null,all),mn=Math.min.apply(null,all),sp=(mx-mn)||1;mn-=sp*0.05;mx+=sp*0.05;
var X=function(i){return pad.l+i*(W-pad.l-pad.r)/(d.dates.length-1||1)},Y=function(v){return pad.t+(1-(v-mn)/(mx-mn))*(H-pad.t-pad.b)};
ctx.strokeStyle='#eee';for(var g=0;g<=3;g++){var gy=pad.t+g*(H-pad.t-pad.b)/3;ctx.beginPath();ctx.moveTo(pad.l,gy);ctx.lineTo(W-pad.r,gy);ctx.stroke();ctx.fillStyle='#999';ctx.font='10px sans-serif';ctx.fillText((mx-g*(mx-mn)/3).toFixed(0),2,gy+4);}
ctx.strokeStyle='#0A7A5E';ctx.lineWidth=2;ctx.beginPath();d.eq.forEach(function(v,i){i?ctx.lineTo(X(i),Y(v)):ctx.moveTo(X(i),Y(v));});ctx.stroke();
ctx.strokeStyle='#bbb';ctx.lineWidth=1.5;ctx.setLineDash([4,4]);ctx.beginPath();d.bh.forEach(function(v,i){i?ctx.lineTo(X(i),Y(v)):ctx.moveTo(X(i),Y(v));});ctx.stroke();ctx.setLineDash([]);
ctx.fillStyle='#0A7A5E';ctx.fillRect(pad.l,H-18,12,3);ctx.fillStyle='#333';ctx.fillText('积极版',pad.l+15,H-22);
ctx.strokeStyle='#bbb';ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(pad.l+60,H-20);ctx.lineTo(pad.l+72,H-20);ctx.stroke();ctx.setLineDash([]);
ctx.fillStyle='#333';ctx.fillText('买入持有',pad.l+76,H-22);}
function drawAll(){for(var k in CH)draw(k);}
window.addEventListener('resize',drawAll);document.addEventListener('DOMContentLoaded',drawAll);
</script></body></html>"""
    html = tmpl
    html = html.replace("@@GEN@@", gen)
    html = html.replace("@@NWIN@@", str(n_win))
    html = html.replace("@@AVG_AGG@@", "%+.1f%%" % avg_agg)
    html = html.replace("@@AVG_PLANA@@", "%+.1f%%" % avg_plana)
    html = html.replace("@@AVG_BH@@", "%+.1f%%" % avg_bh)
    html = html.replace("@@SUM_ROWS@@", sum_rows)
    html = html.replace("@@MC_ROWS@@", mc_rows)
    html = html.replace("@@DETAIL@@", detail)
    html = html.replace("@@JS_CHARTS@@", js_charts)
    out = Path("results/agg_report.html")
    out.write_text(html, encoding="utf-8")
    print("生成: %s (%.0fKB)" % (out, len(html)/1024))
    return str(out)

if __name__ == "__main__":
    main()
