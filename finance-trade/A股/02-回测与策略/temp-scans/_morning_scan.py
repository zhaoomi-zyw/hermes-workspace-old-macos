import sys
sys.path.insert(0, "/Users/omi/workspace/quant-backtest")
import pandas as pd
from fetch_data import fetch_history

STOCKS = {"601138":"工业富联","002156":"通富微电","600487":"亨通光电","000938":"紫光股份",
"603380":"易德龙","600988":"赤峰黄金","600460":"士兰微","600522":"中天科技","002396":"星网锐捷"}
TODAY = pd.Timestamp("2026-09-03").normalize()
for c,name in STOCKS.items():
    try:
        df = fetch_history(c, name)
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date").drop_duplicates(subset=["date"])
        dfc = df[df["date"] < TODAY]
        last = dfc.iloc[-1]
        def roll(n):
            sup = dfc["low"].rolling(n).min().shift(1).iloc[-1]
            res = dfc["high"].rolling(n).max().shift(1).iloc[-1]
            return sup, res
        s20,r20 = roll(20)
        ma5  = dfc["close"].rolling(5).mean().iloc[-1]
        ma10 = dfc["close"].rolling(10).mean().iloc[-1]
        ma60 = dfc["close"].rolling(60).mean().iloc[-1]
        hi10 = dfc["high"].iloc[-10:].max()
        hi20 = dfc["high"].iloc[-20:].max()
        volma = dfc["volume"].rolling(20).mean().iloc[-1]
        pos60 = (last["close"]-dfc["low"].iloc[-60:].min())/(dfc["high"].iloc[-60:].max()-dfc["low"].iloc[-60:].min())*100
        print(f"{name}({c}) 昨收={last['close']:.2f} 支撑20={s20:.2f} 压力20={r20:.2f} MA5={ma5:.2f} MA10={ma10:.2f} MA60={ma60:.2f} 10日高={hi10:.2f} 20日高={hi20:.2f} 60日位置={pos60:.0f}%")
    except Exception as e:
        print(f"{name}({c}) ERR {e}")
