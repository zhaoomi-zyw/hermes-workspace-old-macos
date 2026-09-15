import pandas as pd, numpy as np, sys
sys.path.insert(0, '/Users/omi/workspace/quant-backtest')
from strategies import dsa_strategy as D
# try to find load_data
import os
cands = {'易德龙':'603380','赤峰黄金':'600988','士兰微':'600460','中天科技':'600522',
         '通富微电':'002156','工业富联':'601138','紫光股份':'000938','亨通光电':'600487','星网锐捷':'002396'}
for n,c in cands.items():
    p=f'/Users/omi/workspace/quant-backtest/data/{c}_{n}.csv'
    print(p, os.path.exists(p))
