import urllib.request, json
code='600522'; prefix='sh'
url=f'http://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={prefix}{code},day,0,500,qfq'
req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
data=urllib.request.urlopen(req,timeout=15).read().decode('utf-8')
j=json.loads(data)
node=j['data'][prefix+code]
print("KEYS:", list(node.keys()))
for k,v in node.items():
    if isinstance(v,list):
        print(k, "sample:", v[-1] if v else None)
