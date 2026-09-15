"""
方案A 3年回测 → HTML 报告生成器
================================
跑全部自选, 对每只: 方案A(左侧低吸) vs 买入持有基准。
输出: results/planA_3y_report.html  (白底深绿风格, 用户偏好)
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from datetime import datetime

from strategies.ma_strategy import load_data
from run_backtest import buy_hold
from backtest_planA_3y import backtest_planA, STOCKS, dsa_score_series

START = "2023-09-06"
INIT_CASH = 10000.0


def main():
    rows = []
    detail_html = []
    for code, name in STOCKS.items():
        df = load_data(code, name)
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"] >= pd.to_datetime(START)].reset_index(drop=True)
        if len(df) < 200:
            continue
        # 方案A回测
        res = backtest_planA(df, init_cash=INIT_CASH)
        m = res.metrics
        # 买入持有
        bh = buy_hold(df, INIT_CASH)
        def pct(v):
            try: return float(str(v).rstrip('%'))
            except: return 0.0
        strat_ret = pct(m['累计收益'])
        bh_ret = pct(bh['累计收益'])
        bh_dd = pct(bh['最大回撤'])
        strat_dd = pct(m['最大回撤'])
        # 权益归一化(基准100)
        eq = res.equity / INIT_CASH * 100
        bh_eq = df['close'] / df['close'].iloc[0] * 100
        dates = [d.strftime('%Y-%m-%d') for d in df['date']]
        # 交易明细
        sells = [t for t in res.trades if t['type']=='sell']
        wins = [t for t in sells if t['pnl']>0]
        # 颜色: 正绿负红
        col = "#0A7A5E" if strat_ret >= 0 else "#C0392B"
        rows.append({
            "code": code, "name": name,
            "strat_ret": strat_ret, "bh_ret": bh_ret,
            "strat_dd": strat_dd, "bh_dd": bh_dd,
            "sharpe": float(str(m['夏普比率'])), "winrate": float(str(m['胜率']).rstrip('%')) if m['胜率']!='N/A' else 0,
            "trades": len(sells), "equity": res._final_equity,
            "col": col,
        })
        # 交易明细表
        rows_html = ""
        for t in res.trades:
            rc = "#0A7A5E" if t['pnl'] > 0 else "#C0392B"
            pctv = t['pnl_pct']*100
            rows_html += f"<tr><td>{t['type']}</td><td>{t['reason']}</td><td>{str(t['date'])[:10]}</td><td>{t['price']:.2f}</td><td>{t['shares']}</td><td style='color:{rc}'>{t['pnl']:+.0f}</td><td style='color:{rc}'>{pctv:+.1f}%</td><td>{t['hold_days']}天</td></tr>"
        detail_html.append({
            "code": code, "name": name, "strat_ret": strat_ret, "bh_ret": bh_ret,
            "col": col, "eq": eq.tolist(), "bh_eq": bh_eq.tolist(), "dates": dates,
            "trade_rows": rows_html, "wins": len(wins), "losses": len(sells)-len(wins),
            "strat_dd": strat_dd, "bh_dd": bh_dd,
        })

    # ---- 汇总表 ----
    rows_sorted = sorted(rows, key=lambda x: -x["strat_ret"])
    sum_rows = ""
    for i, r in enumerate(rows_sorted, 1):
        outrank = "✅" if r['strat_ret'] > r['bh_ret'] else ("=" if abs(r['strat_ret']-r['bh_ret'])<0.5 else "❌")
        sum_rows += f"""<tr>
            <td>{i}</td><td><b>{r['name']}</b><br><span class='sub'>{r['code']}</span></td>
            <td style='color:{r['col']};font-weight:600'>{r['strat_ret']:+.1f}%</td>
            <td style='color:{"#0A7A5E" if r['bh_ret']>=0 else "#C0392B"}'>{r['bh_ret']:+.1f}%</td>
            <td>{r['strat_dd']:.1f}%</td><td>{r['bh_dd']:.1f}%</td>
            <td>{r['sharpe']:.2f}</td><td>{r['winrate']:.0f}%</td><td>{r['trades']}笔</td><td>{outrank}</td>
        </tr>"""
    # 组合汇总(等权平均)
    avg_strat = np.mean([r['strat_ret'] for r in rows])
    avg_bh = np.mean([r['bh_ret'] for r in rows])
    n_win = sum(1 for r in rows if r['strat_ret']>0)
    n_beat = sum(1 for r in rows if r['strat_ret']>r['bh_ret'])

    gen = datetime.now().strftime('%Y-%m-%d %H:%M')
    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>方案A 3年回测报告 · 自选股</title>
<style>
body{{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#fff;color:#333;margin:0;padding:24px;line-height:1.6}}
.wrap{{max-width:1100px;margin:0 auto}}
h1{{color:#0A7A5E;font-size:24px;border-bottom:3px solid #00E47C;padding-bottom:10px}}
h2{{color:#0A7A5E;font-size:19px;margin-top:32px}}
.meta{{color:#888;font-size:13px;margin:6px 0 20px}}
.cards{{display:flex;gap:16px;flex-wrap:wrap;margin:16px 0}}
.card{{flex:1;min-width:150px;background:#FAF9F8;border:1px solid #eee;border-radius:10px;padding:14px;text-align:center}}
.card .v{{font-size:22px;font-weight:700;color:#0A7A5E}}
.card .l{{font-size:12px;color:#888;margin-top:4px}}
table{{border-collapse:collapse;width:100%;font-size:14px;margin:12px 0}}
th{{background:#0A7A5E;color:#fff;padding:9px 8px;text-align:left;font-weight:600}}
td{{padding:8px;border-bottom:1px solid #eee}}
tr:nth-child(even){{background:#f9fdfb}}
.sub{{color:#aaa;font-size:11px;font-weight:400}}
.note{{background:#eefaf4;border-left:4px solid #0A7A5E;padding:12px 16px;font-size:13px;border-radius:4px;margin:16px 0}}
.warn{{background:#fdf3ef;border-left:4px solid #C0392B;padding:12px 16px;font-size:13px;border-radius:4px;margin:16px 0}}
canvas{{max-width:100%;background:#fff}}
.detail{{background:#FAF9F8;border:1px solid #eee;border-radius:10px;padding:16px;margin:18px 0}}
.detail h3{{color:#0A7A5E;margin:0 0 4px}}
.detail .stat{{font-size:13px;color:#666;margin-bottom:10px}}
.trade-tbl{{font-size:12.5px;max-height:260px;overflow-y:auto;display:block}}
.pos{{color:#0A7A5E}}.neg{{color:#C0392B}}
</style></head><body><div class="wrap">

<h1>📊 方案A 左侧低吸策略 · 3年日线回测</h1>
<div class="meta">数据源：同花顺官方API（前复权日线）｜区间：2023-09-06 → 2026-09-04｜初始资金 ¥{INIT_CASH:,.0f}｜生成：{gen}</div>

<div class="cards">
  <div class="card"><div class="v">{n_win}/{len(rows)}</div><div class="l">策略盈利标的</div></div>
  <div class="card"><div class="v">{n_beat}/{len(rows)}</div><div class="l">跑赢买入持有</div></div>
  <div class="card"><div class="v">{avg_strat:+.1f}%</div><div class="l">9只平均收益</div></div>
  <div class="card"><div class="v">{avg_bh:+.1f}%</div><div class="l">买入持有均值</div></div>
</div>

<div class="note"><b>策略规则</b>：从10日高点回撤≥5% + 站上MA60 + DSA评级A/B(≥65分) + 现价接近MA5/MA10 → 一手试探100股。止损-4.5%｜止盈+8%｜最长持仓20天。T+1/涨跌停/费用(佣金万2.5+印花税千0.5+过户费)已计入。<b>初始资金¥1万</b>贴近一手实际仓位（100股×均价≈¥3500，占比约35%）。</div>

<div class="warn"><b>⚠️ 诚实提示</b>：方案A是<b>防守型左侧低吸</b>，本质是控制风险而非追逐收益。本回测显示：它在上涨趋势股(工业富联+21%/赤峰+14%)能跟随获利，但在<b>趋势走弱/单边下跌股(紫光-21%/士兰微-7%)会反复止损</b>。方案A的价值在于限制单笔亏损和回撤，不等于每只都赚。</div>

<h2>一、汇总对比（方案A vs 买入持有）</h2>
<table>
<tr><th>#</th><th>标的</th><th>方案A收益</th><th>买入持有</th><th>策略回撤</th><th>持有回撤</th><th>夏普</th><th>胜率</th><th>交易</th><th>跑赢?</th></tr>
{sum_rows}
<tr style="background:#eefaf4;font-weight:700"><td colspan="2">平均</td><td>{avg_strat:+.1f}%</td><td>{avg_bh:+.1f}%</td><td colspan="6"></td></tr>
</table>

<h2>二、个股明细（方案A交易记录 + 权益曲线）</h2>
"""
    for d in detail_html:
        rc = d['col']
        arrow = "↑" if d['strat_ret'] > d['bh_ret'] else "↓"
        html += f"""
<div class="detail">
  <h3>{d['name']} <span style="font-size:12px;color:#aaa">({d['code']})</span>
    <span style="float:right;color:{rc};font-size:16px">方案A {d['strat_ret']:+.1f}% · 买入持有 {d['bh_ret']:+.1f}% {arrow}</span></h3>
  <div class="stat">最大回撤：方案A {d['strat_dd']:.1f}% vs 持有 {d['bh_dd']:.1f}%｜{d['wins']}盈 {d['losses']}亏</div>
  <canvas id="c_{d['code']}" height="220"></canvas>
  <h4 style="color:#666;margin:14px 0 6px;font-size:14px">方案A 全部交易</h4>
  <table class="trade-tbl">
  <tr><th>方向</th><th>原因</th><th>日期</th><th>价格</th><th>股数</th><th>盈亏(元)</th><th>盈亏%</th><th>持仓</th></tr>
  {d['trade_rows']}
  </table>
</div>"""

    html += f"""
<script>
const charts = {{
"""
    for d in detail_html:
        html += f"c_{d['code']}: {{ eq: {json_dumps(d['eq'])}, bh: {json_dumps(d['bh_eq'])}, dates: {json_dumps(d['dates'])} }},\n"
    html += """};
function draw(id){
  const d=charts[id]; const cv=document.getElementById(id); if(!cv) return;
  const W=cv.clientWidth||900,H=220,ctx=cv.getContext('2d');
  ctx.clearRect(0,0,W,H);
  const pad={l:40,r:10,t:10,b:22};
  let all=d.eq.concat(d.bh); let mx=Math.max(...all),mn=Math.min(...all);
  const span=(mx-mn)||1; mn-=span*0.05; mx+=span*0.05;
  const X=i=>pad.l+i*(W-pad.l-pad.r)/(d.dates.length-1||1);
  const Y=v=>pad.t+(1-(v-mn)/(mx-mn))*(H-pad.t-pad.b);
  // grid
  ctx.strokeStyle='#eee';ctx.lineWidth=1;
  for(let g=0;g<=4;g++){const gy=pad.t+g*(H-pad.t-pad.b)/4;ctx.beginPath();ctx.moveTo(pad.l,gy);ctx.lineTo(W-pad.r,gy);ctx.stroke();
    ctx.fillStyle='#999';ctx.font='11px sans-serif';ctx.fillText((mx-g*(mx-mn)/4).toFixed(1),2,gy+4);}
  // strategy equity (green)
  ctx.strokeStyle='#0A7A5E';ctx.lineWidth=2;ctx.beginPath();
  d.eq.forEach((v,i)=>{i?ctx.lineTo(X(i),Y(v)):ctx.moveTo(X(i),Y(v));});ctx.stroke();
  // buy-hold (gray dashed)
  ctx.strokeStyle='#bbb';ctx.lineWidth=1.5;ctx.setLineDash([4,4]);ctx.beginPath();
  d.bh.forEach((v,i)=>{i?ctx.lineTo(X(i),Y(v)):ctx.moveTo(X(i),Y(v));});ctx.stroke();ctx.setLineDash([]);
  // legend
  ctx.fillStyle='#0A7A5E';ctx.fillRect(pad.l,W-18,12,3);ctx.fillStyle='#333';ctx.fillText('方案A',pad.l+16,W-22);
  ctx.strokeStyle='#bbb';ctx.setLineDash([4,4]);ctx.beginPath();ctx.moveTo(pad.l+70,W-20);ctx.lineTo(pad.l+82,W-20);ctx.stroke();ctx.setLineDash([]);
  ctx.fillStyle='#333';ctx.fillText('买入持有',pad.l+86,W-22);
  ctx.fillStyle='#aaa';ctx.font='10px sans-serif';ctx.fillText(d.dates[0]+' — '+d.dates[d.dates.length-1],pad.l,H-5);
}
window.addEventListener('resize',()=>Object.keys(charts).forEach(draw));
document.addEventListener('DOMContentLoaded',()=>Object.keys(charts).forEach(draw));
</script>
<p style="color:#aaa;font-size:12px;margin-top:30px">本报告由 Hermes 生成，仅供量化研究参考，非投资建议。历史回测不代表未来表现。</p>
</div></body></html>"""

    out = Path("results/planA_3y_report.html")
    out.parent.mkdir(exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"HTML已生成: {out} ({len(html)/1024:.0f}KB)")
    return str(out)


def json_dumps(x):
    import json
    return json.dumps(x)


if __name__ == "__main__":
    main()
