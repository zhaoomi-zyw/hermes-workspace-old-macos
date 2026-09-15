import urllib.request
codes=['sz000938','sh600988','sz002396','sh600522','sz002156','sh601138','sh600487','sh600460','sh603380','sz002475','sh601899','sh688097']
url='http://qt.gtimg.cn/q='+','.join(codes)
req=urllib.request.Request(url,headers={'Referer':'http://finance.qq.com'})
data=urllib.request.urlopen(req,timeout=10).read().decode('gbk')
for line in data.strip().split(';'):
    line=line.strip()
    if not line or '=' not in line: continue
    body=line.split('=')[1].strip('"')
    f=body.split('~')
    if len(f)<35: continue
    print(f"{f[2]} {f[1]} 现{f[3]} 涨跌{f[32]}% 高{f[33]} 低{f[34]} 昨收{f[4]}")
