"""日终 DSA + 低吸四条件扫描 (2026-09-10 收盘)"""
import pandas as pd, numpy as np, json
from pathlib import Path
from dsa_scores import score_v1_series

DATA = Path("data")

# 腾讯实时(收盘价) — 由 cron context 注入, 这里再校准一次用 CSV 收盘
LIVE = {
    "600988": 44.30, "000878": 18.71, "601138": 63.91, "002156": 58.34,
    "600487": 63.91, "600522": 33.30, "603380": 32.72, "600460": 30.24,
    "002396": 35.99, "000938": 33.10, "600219": 5.00, "600760": 48.60,
}

FILES = {
    "600988": "600988_赤峰黄金.csv", "601138": "601138_工业富联.csv",
    "600487": "600487_亨通光电.csv", "600522": "600522_中天科技.csv",
    "002156": "002156_通富微电.csv", "002396": "002396_星网锐捷.csv",
    "603380": "603380_易德龙.csv", "600460": "600460_士兰微.csv",
    "600219": "600219_南山铝业.csv", "000878": "000878_云南铜业.csv",
    "000938": "000938_紫光股份.csv", "600760": "600760_中航沈飞.csv",
}

def grade(s):
    if s >= 90: return "S"
    if s >= 80: return "A"
    if s >= 65: return "B"
    if s >= 50: return "C"
    return "D"

rows = []
for code, fn in FILES.items():
    df = pd.read_csv(DATA / fn).sort_values("date").reset_index(drop=True)
    # 用腾讯实时价覆盖/追加当日收盘
    last_date = str(df.iloc[-1]["date"])[:10]
    live = LIVE[code]
    if last_date == "2026-09-10":
        df.loc[df.index[-1], "close"] = live
    else:
        df = pd.concat([df, pd.DataFrame([{"date": "2026-09-10", "open": np.nan,
                       "high": np.nan, "low": np.nan, "close": live,
                       "volume": np.nan, "code": code, "name": ""}])], ignore_index=True)
    c = df["close"]
    ma5, ma10, ma20, ma60 = [c.rolling(n).mean().iloc[-1] for n in (5, 10, 20, 60)]
    hi10 = df["high"].rolling(10).max().iloc[-1]
    hi60 = df["high"].rolling(60).max().iloc[-1]
    lo60 = df["low"].rolling(60).min().iloc[-1]
    dd = (live - hi10) / hi10 * 100
    pos60 = (live - lo60) / (hi60 - lo60) * 100
    score = score_v1_series(df).iloc[-1]
    last = df.iloc[-1]
    rows.append(dict(code=code, name=fn.split("_")[1].replace(".csv", ""),
                     close=live, dsa=round(score, 1), grade=grade(score),
                     ma5=round(ma5, 2), ma10=round(ma10, 2), ma20=round(ma20, 2),
                     ma60=round(ma60, 2), dd10=round(dd, 1), pos60=round(pos60, 1),
                     vol=last.get("volume"), date=last_date))

out = pd.DataFrame(rows)
pd.set_option("display.width", 250)
print(out.to_string(index=False))

print("\n--- 低吸四条件判定 (回撤>=5% + 站上MA60 + DSA>=65 + 近MA5/MA10) ---")
for r in rows:
    c1 = r["dd10"] <= -5
    c2 = r["close"] > r["ma60"]
    c3 = r["dsa"] >= 65
    dist5 = (r["close"] - r["ma5"]) / r["ma5"] * 100
    dist10 = (r["close"] - r["ma10"]) / r["ma10"] * 100
    c4 = min(abs(dist5), abs(dist10)) <= 2.5
    verdict = "✅四条件全满足=低吸" if all([c1, c2, c3, c4]) else "—"
    print(f"{r['name']}({r['code']}) 回撤{r['dd10']}% 站MA60={c2} DSA{r['dsa']}({r['grade']}) 距MA5{dist5:+.1f}% 距MA10{dist10:+.1f}% 60位{r['pos60']}% → {verdict}")
