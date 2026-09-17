#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""美股隔夜行情注入脚本（免搜索，用于 cron 美股晨报）

背景（2026-09-17）：
  美股晨报 cron 依赖 anysearch 搜美股新闻 → 搜到的新闻原文在后续轮次被
  DeepSeek 内容风控拦截（HTTP 400: Content Exists Risk），且 400 为确定性
  错误，重试无效（api_max_retries=3 已存在仍未救回）。当日为该 cron 45 次
  运行中唯一一次失败。
  解决：美股指数与关键个股改为直连腾讯行情接口（qt.gtimg.cn，实测可用），
  彻底移除"搜索新闻"这一风控触发源。

用法：作为 cron 的 script 配置，stdout 会被注入 prompt。
"""
import urllib.request

# 指数
INDICES = ["usDJI", "usIXIC", "usINX", "usNDX"]
# 关键个股：芯片 / AI 巨头 / 中概 / 能源
STOCKS = [
    "usNVDA", "usAMD", "usAVGO", "usTSM", "usMU",      # 芯片
    "usMSFT", "usGOOG", "usMETA", "usAAPL", "usTSLA",  # AI 巨头
    "usBABA", "usPDD", "usJD", "usNIO",                # 中概
    "usXOM", "usCVX",                                   # 能源
]
ALL = INDICES + STOCKS


def fetch(codes):
    url = "http://qt.gtimg.cn/q=" + ",".join(codes)
    req = urllib.request.Request(url, headers={"Referer": "http://finance.qq.com"})
    return urllib.request.urlopen(req, timeout=20).read().decode("gbk", errors="ignore")


def parse(raw):
    out = []
    for line in raw.strip().split(";"):
        line = line.strip()
        if not line or "=" not in line:
            continue
        body = line.split("=", 1)[1].strip().strip('"')
        f = body.split("~")
        if len(f) < 33:
            continue
        try:
            out.append({
                "name": f[1],
                "price": float(f[3]),
                "prev": float(f[4]),
                "pct": float(f[32]),
                "high": float(f[33]) if len(f) > 33 else None,
                "low": float(f[34]) if len(f) > 34 else None,
                "time": f[30],
            })
        except (ValueError, IndexError):
            continue
    return out


def main():
    try:
        rows = parse(fetch(ALL))
    except Exception as e:
        print(f"[美股行情获取失败] {type(e).__name__}: {e}")
        print("（请基于此明确说明数据不可用，不要编造点位）")
        return

    if not rows:
        print("[美股行情为空] 接口未返回有效数据，请明确说明，不要编造。")
        return

    idx = [r for r in rows if r["name"] in ("道琼斯", "纳斯达克", "标普500", "纳斯达克100")]
    stk = [r for r in rows if r not in idx]

    print("### 美股隔夜收盘（直连腾讯行情，免搜索）")
    ts = rows[0]["time"] if rows else ""
    print(f"数据时间：{ts}\n")

    print("【三大指数】")
    for r in idx:
        print(f"  {r['name']}: {r['price']:.2f}  {r['pct']:+.2f}%  (高{r['high']:.2f}/低{r['low']:.2f})")

    print("\n【关键个股】")
    for r in stk:
        print(f"  {r['name']}: {r['price']:.2f}  {r['pct']:+.2f}%")

    up = sum(1 for r in rows if r["pct"] > 0)
    print(f"\n【统计】{len(rows)}个标的：上涨 {up} / 下跌 {len(rows)-up}")

    print("""
### 使用要求
- 上面的点位/涨跌为【直连行情的真实数据】，直接引用，不要另行搜索覆盖。
- 如需补充新闻面（如美联储决议、财报），可用 anysearch 搜索；但【若搜索返回
  异常或被拦截，必须跳过新闻部分继续输出行情结论，不得因此中断整篇报告】。
- 对 A 股的传导分析基于本地自选股逻辑，不需要搜索。""")


if __name__ == "__main__":
    main()
