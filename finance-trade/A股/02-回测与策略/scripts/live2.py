import urllib.request
# 赤峰600988, 紫光000938 intraday low check via qt.gtimg
for code in ['sh600988','sz000938','sh600522','sh601138','sz002156','sh600487','sh600460','sh603380']:
    url='http://qt.gtimg.cn/q='+code
    req=urllib.request.Request(url,headers={'Referer':'http://finance.qq.com'})
    d=urllib.request.urlopen(req,timeout=10).read().decode('gbk')
    f=d.split('=')[1].strip('";\n').split('~')
    print(f"{f[2]} {f[1]} 现{f[3]} 低{f[34]} 高{f[33]} 量比{f[49] if len(f)>49 else '?'}")
