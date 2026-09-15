# -*- coding: utf-8 -*-
"""复权口径对账: 前复权(qfq) vs 不复权(raw) 的分红/除权痕迹"""
import json
from pathlib import Path
import pandas as pd, numpy as np
HERE = Path(__file__).resolve().parent
CODES = ["601138","002156","600487","603380","600988","600460","600522","002396","600219","000878","000938","600760"]
NAMES = {"601138":"工业富联","002156":"通富微电","600487":"亨通光电","603380":"易德龙","600988":"赤峰黄金",
         "600460":"士兰微","600522":"中天科技","002396":"星网锐捷","600219":"南山铝业","000878":"云南铜业",
         "000938":"紫光股份","600760":"中航沈飞"}
rows=[]
for c in CODES:
    q=pd.read_csv(HERE/f"data_cache/daily_qfq_{c}.csv",dtype=str)
    r=pd.read_csv(HERE/f"data_cache/daily_raw_{c}.csv",dtype=str)
    for col in ("close","preclose"):
        q[col]=pd.to_numeric(q[col],errors="coerce"); r[col]=pd.to_numeric(r[col],errors="coerce")
    m=q[["date","close"]].merge(r[["date","close"]],on="date",suffixes=("_qfq","_raw"))
    m=m.dropna()
    ratio=m["close_qfq"]/m["close_raw"]
    # 检测 ratio 变化点 = 除权/分红事件
    ch=ratio.round(8).diff().abs()>1e-8
    events=m.loc[ch,"date"].tolist()
    rows.append({"code":c,"name":NAMES[c],"pairs":len(m),
                 "ratio_first":round(float(ratio.iloc[0]),6),"ratio_last":round(float(ratio.iloc[-1]),6),
                 "n_adjust_events":len(events),
                 "events_sample":",".join(events[:6]),
                 "close_end_qfq":round(float(m['close_qfq'].iloc[-1]),4),
                 "close_end_raw":round(float(m['close_raw'].iloc[-1]),4)})
df=pd.DataFrame(rows)
df.to_csv(HERE/"price_reconciliation.csv",index=False)
print(df.to_string(index=False))
