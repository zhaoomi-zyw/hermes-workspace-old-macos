import pandas as pd, numpy as np

quotes = {
 '600522':('中天科技',33.23),'601138':('工业富联',63.59),'000938':('紫光股份',38.15),
 '002156':('通富微电',60.09),'600487':('亨通光电',66.19),'600460':('士兰微',31.40),
 '603380':('易德龙',35.40),'600988':('赤峰黄金',46.80),'002396':('星网锐捷',39.37)}

def fetch_sina(code):
    prefix='sh' if code.startswith('6') else 'sz'
    import urllib.request, json, re
    url=f'https://quotes.sina.cn/cn/api/jsonp_v2.php/=/CN_MarketDataService.getKLineData?symbol={prefix}{code}&scale=240&ma=no&datalen=300'
    req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0','Referer':'https://finance.sina.com.cn'})
    txt=urllib.request.urlopen(req,timeout=15).read().decode('utf-8')
    m=re.search(r'\((\[.*\])\)', txt)
    arr=json.loads(m.group(1))
    df=pd.DataFrame(arr)
    df['date']=pd.to_datetime(df['day'])
    for col in ['open','high','low','close','volume']:
        df[col]=pd.to_numeric(df[col])
    return df

def calc(df, price, name):
    df=df.sort_values('date').reset_index(drop=True)
    c=df['close'].astype(float); v=df['volume'].astype(float)
    ma5=c.rolling(5).mean(); ma10=c.rolling(10).mean(); ma20=c.rolling(20).mean(); ma60=c.rolling(60).mean()
    sup20=df['low'].astype(float).rolling(20).min().shift(1)
    res20=df['high'].astype(float).rolling(20).max().shift(1)
    vol_ma=v.rolling(20).mean().shift(1)
    print(f"\n== {name} 现{price} ==")
    print(f" MA5={ma5.iloc[-1]:.2f} MA10={ma10.iloc[-1]:.2f} MA20={ma20.iloc[-1]:.2f} MA60={ma60.iloc[-1]:.2f}")
    print(f" 20日支撑={sup20.iloc[-1]:.2f} 20日压力={res20.iloc[-1]:.2f}")
    print(f" 昨收={c.iloc[-1]:.2f} 距MA10 {(price/ma10.iloc[-1]-1)*100:+.1f}% 距MA60 {(price/ma60.iloc[-1]-1)*100:+.1f}% 距支撑 {(price/sup20.iloc[-1]-1)*100:+.1f}%")
    # DSA score
    score=0
    if price>ma5.iloc[-1]: score+=15
    if ma5.iloc[-1]>ma10.iloc[-1]: score+=10
    if ma10.iloc[-1]>ma20.iloc[-1]: score+=10
    if price>ma20.iloc[-1]: score+=10
    if price>ma60.iloc[-1]: score+=15
    if price>ma5.iloc[-1]>ma10.iloc[-1]>ma20.iloc[-1]>ma60.iloc[-1]: score+=15
    lo60=df['low'].astype(float).iloc[-60:].min(); hi60=df['high'].astype(float).iloc[-60:].max()
    score+= (price-lo60)/(hi60-lo60)*15 if hi60>lo60 else 7
    vm=vol_ma.iloc[-1]; lastv=v.iloc[-1]
    score+= 10 if lastv<vm else (5 if lastv<vm*1.5 else 2)
    score+= 15 if c.iloc[-1]>c.iloc[-21] else (7 if c.iloc[-1]>c.iloc[-11] else 3)
    grade='S' if score>=90 else 'A' if score>=80 else 'B' if score>=65 else 'C' if score>=50 else 'D'
    print(f" DSA≈{score:.0f} {grade}")

for code,(name,price) in quotes.items():
    try:
        df=fetch_sina(code)
        calc(df,price,name)
    except Exception as e:
        print(f"\n== {name} FAIL {type(e).__name__}: {e}")
