import urllib.request
url='http://qt.gtimg.cn/q=sz002396'
req=urllib.request.Request(url,headers={'Referer':'http://finance.qq.com'})
d=urllib.request.urlopen(req,timeout=10).read().decode('gbk')
line=d.strip().split('"')[1]
f=line.split('~')
print("星网锐捷 现价%s 昨收%s 今开%s 最高%s 最低%s 时间%s 涨跌%s(%s%%) 量比%s" % (
    f[3], f[4], f[5], f[33], f[34], f[30], f[31], f[32], f[49] if len(f)>49 else 'NA'))
