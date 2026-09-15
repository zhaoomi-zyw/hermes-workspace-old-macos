"""盘中实时 DSA + 低吸四条件 (2026-09-14 10:03)
用本地CSV日线 + 注入的腾讯实时价当场计算
"""
import pandas as pd, numpy as np, os

RT = {  # 代码: (名称, 现价, 涨跌幅, 今开, 最高, 最低, 成交量手, 昨收)
 "600988": ("赤峰黄金", 44.78, 0.39, 43.51, 45.60, 43.30, 170081, 44.39),
 "000878": ("云南铜业", 16.94, -0.24, 16.77, 17.04, 16.57, 189811, 17.18),
 "601138": ("工业富联", 62.31, -1.76, 62.99, 63.01, 61.70, 285131, 64.07),
 "002156": ("通富微电", 57.45, -0.55, 57.30, 57.88, 56.33, 128978, 58.00),
 "600487": ("亨通光电", 64.29, -0.95, 63.01, 64.93, 62.22, 567648, 65.24),
 "600522": ("中天科技", 34.49, 0.00, 33.84, 34.78, 32.82, 993924, 34.49),
 "603380": ("易德龙", 34.08, 1.82, 32.05, 34.25, 31.65, 23051, 32.26),
 "600460": ("士兰微", 29.97, -0.10, 29.65, 30.09, 29.31, 145029, 30.07),
 "002396": ("星网锐捷", 35.62, 1.03, 33.95, 35.93, 33.01, 328306, 34.59),
 "000938": ("紫光股份", 32.89, 0.05, 32.36, 33.21, 31.91, 368109, 32.84),
 "600219": ("南山铝业", 4.80, -0.02, 4.78, 4.82, 4.75, 323505, 4.82),
 "600760": ("中航沈飞", 46.26, -1.76, 47.90, 48.25, 46.05, 89536, 48.02),
}
HOLD = {"600988": (200, 44.685, 42.00), "002396": (100, 35.83, 33.68)}
D = "/Users/omi/workspace/quant-backtest/data"

rows = []
for code, (name, p, pct, op, hi, lo, vlot, prev) in RT.items():
    f = f"{D}/{code}_{name}.csv"
    df = pd.read_csv(f)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    # 去掉可能当日行, 用实时价代表今日
    if df["date"].iloc[-1].date() >= pd.Timestamp("2026-09-14").date():
        df = df.iloc[:-1]
    c = df["close"].astype(float).tolist()
    h = df["high"].astype(float).tolist()
    l = df["low"].astype(float).tolist()
    v = df["volume"].astype(float).tolist()
    last_date = df["date"].iloc[-1].date()
    C = c + [p]; H = h + [hi]; L = l + [lo]
    n = len(C)
    ma5 = sum(C[-5:])/5; ma10 = sum(C[-10:])/10; ma20 = sum(C[-20:])/20; ma60 = sum(C[-60:])/60
    hi10 = max(H[-10:]); lo60 = min(L[-60:]); hi60 = max(H[-60:])
    dd = (p-hi10)/hi10*100
    d60 = (p-ma60)/ma60*100
    d5 = (p-ma5)/ma5*100; d10 = (p-ma10)/ma10*100
    # DSA v1
    sc = 0
    sc += 15*(p>ma5); sc += 10*(ma5>ma10); sc += 10*(ma10>ma20); sc += 10*(p>ma20); sc += 15*(p>ma60)
    sc += 15*(p>ma5 and ma5>ma10 and ma10>ma20 and ma20>ma60)
    sc += (p-lo60)/(hi60-lo60)*15 if hi60>lo60 else 7.5
    vma20 = sum(v[-20:])/20
    vratio_raw = (vlot*100)/vma20 if vma20 else 1  # 手->股? CSV volume单位需确认
    sc += 10 if vratio_raw<1 else (5 if vratio_raw<1.5 else 2)
    sc += 15 if p>C[-21] else (7 if p>C[-11] else 3)
    grade = "S" if sc>=80 else "A" if sc>=65 else "B" if sc>=50 else "C" if sc>=35 else "D"
    near_ma = (abs(d5)<=3 or abs(d10)<=3)
    cond = dict(dd5=dd<=-5, ma60=d60>0, dsa=sc>=65, near=near_ma)
    ok = all(cond.values())
    tag = ""
    if code in HOLD:
        sh, cost, stop = HOLD[code]
        pl = (p-cost)/cost*100
        tag = f" 持仓{sh}股 浮盈{pl:+.2f}% 距止损{(p-stop)/stop*100:+.2f}%(stop {stop})"
    rows.append(dict(code=code, name=name, p=p, pct=pct, ma5=ma5, ma10=ma10, ma20=ma20, ma60=ma60,
                     d5=d5, d10=d10, d60=d60, hi10=hi10, dd=dd, vr=vratio_raw, sc=sc, grade=grade,
                     ok=ok, near=near_ma, cond=cond, tag=tag, last_date=last_date, hi=hi, lo=lo, op=op, prev=prev))

print(f"数据末行日期: {rows[0]['last_date']}  量比=当日量/20日均量(未做时间折算)")
print(f"{'名称':<6}{'现价':>7}{'涨跌':>7} {'MA5':>7}{'MA10':>7}{'MA60':>7}  {'距MA5':>7}{'距MA10':>7}{'距MA60':>8}  {'10高':>7}{'回撤':>7}  {'量比':>5} {'DSA':>5} {'级':>3}  四条件")
for r in rows:
    print(f"{r['name']:<6}{r['p']:>7.2f}{r['pct']:>+7.2f} {r['ma5']:>7.2f}{r['ma10']:>7.2f}{r['ma60']:>7.2f}  "
          f"{r['d5']:>+7.1f}{r['d10']:>+7.1f}{r['d60']:>+8.1f}  {r['hi10']:>7.2f}{r['dd']:>+7.1f}  "
          f"{r['vr']:>5.2f} {r['sc']:>5.0f} {r['grade']:>3}  "
          f"{'✅全满足' if r['ok'] else '|'.join(k+('✓' if x else '✗') for k,x in r['cond'].items())}{r['tag']}")
