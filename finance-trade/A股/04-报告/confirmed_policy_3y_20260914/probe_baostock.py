import baostock as bs, pandas as pd, json
lg = bs.login()
print("login:", lg.error_code, lg.error_msg)
rs = bs.query_history_k_data_plus("sh.601138",
    "date,time,code,open,high,low,close,volume,amount,adjustflag",
    start_date="2023-09-14", end_date="2026-09-14", frequency="5", adjustflag="2")
rows=[]
while rs.error_code=='0' and rs.next():
    rows.append(rs.get_row_data())
df=pd.DataFrame(rows, columns=rs.fields)
print("error:", rs.error_code, rs.error_msg)
print("rows:", len(df))
if len(df):
    print(df.head(3).to_string())
    print(df.tail(3).to_string())
    d=pd.to_datetime(df['time'].str[:10])
    vc=d.dt.date.value_counts()
    print("n_days:", len(vc), "bars/day max:", vc.max(), "min:", vc.min())
    print("first day:", vc.index.min(), "last day:", vc.index.max())
bs.logout()
