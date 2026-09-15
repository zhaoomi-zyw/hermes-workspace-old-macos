"""收盘前(14:57)实时DSA + 低吸四条件 + 持仓损益 (2026-09-14)
日线: data/*.csv (hithink, 已刷新到09-14) + 注入的腾讯实时价代表今日
DSA 用 dsa_scores.score_v1_series (v1, 与主文件/回测一致)
"""
import pandas as pd, numpy as np
from dsa_scores import score_v1_series

RT = {  # 代码: (名称, 现价, 涨跌幅, 今开, 最高, 最低, 成交量(股), 昨收)
 "600988": ("赤峰黄金", 44.45, 0.14, 43.51, 45.60, 43.30, 37121300, 44.39),
 "000878": ("云南铜业", 16.83, -2.04, 16.77, 17.09, 16.57, 42707400, 17.18),
 "601138": ("工业富联", 61.61, -3.84, 62.99, 63.01, 61.37, 78783600, 64.07),
 "002156": ("通富微电", 56.75, -2.16, 57.30, 57.88, 56.33, 36926100, 58.00),
 "600487": ("亨通光电", 63.20, -3.13, 63.01, 64.93, 62.22, 110324000, 65.24),
 "600522": ("中天科技", 33.90, -1.71, 33.84, 34.78, 32.82, 181550400, 34.49),
 "603380": ("易德龙", 33.92, 5.15, 32.05, 34.33, 31.65, 4678400, 32.26),
 "600460": ("士兰微", 29.83, -0.80, 29.65, 30.20, 29.31, 36900900, 30.07),
 "002396": ("星网锐捷", 34.80, 0.61, 33.95, 35.93, 33.01, 65300900, 34.59),
 "000938": ("紫光股份", 32.72, -0.37, 32.36, 33.21, 31.91, 75025800, 32.84),
 "600219": ("南山铝业", 4.80, -0.41, 4.78, 4.82, 4.75, 77950000, 4.82),
 "600760": ("中航沈飞", 45.51, -5.23, 47.90, 48.25, 45.43, 27198400, 48.02),
}
HOLD = {"600988": ("赤峰黄金", 200, 44.735, 42.05, 48.31),
        "002396": ("星网锐捷", 100, 35.880, 33.73, 38.75)}
D = "/Users/omi/workspace/quant-backtest/data"
TODAY = pd.Timestamp("2026-09-14")

print(f"{'名称':<6}{'现价':>7}{'涨跌%':>7}{'MA5':>7}{'MA10':>7}{'MA20':>7}{'MA60':>7}"
      f"{'距MA5':>7}{'距MA10':>7}{'距MA60':>8}{'10日高':>7}{'回撤':>7}{'量比':>6}{'DSA':>5}{'级':>3}  四条件")
for code, (name, p, pct, op, hi, lo, v, prev) in RT.items():
    df = pd.read_csv(f"{D}/{code}_{name}.csv")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    df = df[df["date"] < TODAY]                      # 去掉今日行, 用实时价代替
    row = pd.DataFrame([{"date": TODAY, "open": op, "high": hi, "low": lo,
                         "close": p, "volume": v, "code": code, "name": name}])
    df = pd.concat([df, row], ignore_index=True)
    sc = float(score_v1_series(df).iloc[-1])
    c = df["close"]; h = df["high"]; l = df["low"]; vol = df["volume"]
    ma5 = c.rolling(5).mean().iloc[-1]; ma10 = c.rolling(10).mean().iloc[-1]
    ma20 = c.rolling(20).mean().iloc[-1]; ma60 = c.rolling(60).mean().iloc[-1]
    hi10 = h.iloc[-10:].max(); lo60 = l.iloc[-60:].min(); hi60 = h.iloc[-60:].max()
    d5 = (p/ma5-1)*100; d10 = (p/ma10-1)*100; d60 = (p/ma60-1)*100
    dd = (p-hi10)/hi10*100
    vma = vol.rolling(20).mean().shift(1).iloc[-1]
    vr = v/vma
    grade = ("S" if sc>=90 else "A" if sc>=80 else "B" if sc>=65 else "C" if sc>=50 else "D")
    cond = {"回撤≥5%": dd<=-5, "站上MA60": d60>0, "DSA≥65": sc>=65,
            "近MA5/10": (abs(d5)<=2 or abs(d10)<=2)}
    n_ok = sum(cond.values())
    s = "   ".join(f"{k}{'✓' if x else '✗'}" for k, x in cond.items())
    marks = []
    if code in HOLD:
        hn, sh, cost, stop, prof = HOLD[code]
        pl = (p-cost)/cost*100
        marks.append(f"持仓{sh}股 成本{cost:.3f} 浮盈{pl:+.2f}% 距止损{(p/stop-1)*100:+.2f}%(止损{stop}) 距浮盈线{(p/prof-1)*100:+.2f}%(线{prof})")
    if n_ok == 4:
        marks.append("★四条件全满足")
    print(f"{name:<6}{p:>7.2f}{pct:>+7.2f}{ma5:>7.2f}{ma10:>7.2f}{ma20:>7.2f}{ma60:>7.2f}"
          f"{d5:>+7.1f}{d10:>+7.1f}{d60:>+8.1f}{hi10:>7.2f}{dd:>+7.1f}{vr:>6.2f}{sc:>5.0f}{grade:>3}  {s}  {'  '.join(marks)}")
