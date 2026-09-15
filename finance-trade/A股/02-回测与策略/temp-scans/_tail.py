import pandas as pd
for code, name in [("600988", "赤峰黄金"), ("002396", "星网锐捷"), ("600760", "中航沈飞"), ("600522", "中天科技")]:
    df = pd.read_csv(f"/Users/omi/workspace/quant-backtest/data/{code}_{name}.csv")
    print(name)
    print(df.tail(6)[["date", "open", "high", "low", "close"]].to_string(index=False))
    print()
