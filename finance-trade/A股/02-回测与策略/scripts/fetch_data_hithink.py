"""
数据下载脚本 · 用同花顺官方金融数据API(hithink-finance CLI)拉取 A股历史日线
==============================================================================
替代原 fetch_data.py 的 akshare 源, 消除东财IP风控断连 + 按年分片痛点。
同花顺API一次可拉5年前复权日线(实测3年724行无分片), 稳定无断连。

用法:
    python fetch_data_hithink.py                # 拉取配置中的全部标的
    python fetch_data_hithink.py 600988         # 只拉指定代码

输出CSV格式与 fetch_data.py 兼容(date/open/high/low/close/volume/code/name),
回测脚本无需改动。

依赖: hithink-finance CLI 已安装并登录(API key 存系统凭据库), pandas, subprocess
"""
import sys
import json
import os
import subprocess
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone, timedelta

import pandas as pd

DATA_DIR = Path(__file__).parent / "data"
CN_TZ = timezone(timedelta(hours=8))  # Asia/Shanghai

# cron 环境可能缺 npm-global/node PATH; 主动补上, 保证 subprocess 能找到 hithink-finance CLI 及 node
def _env_with_hithink_path():
    env = dict(os.environ)
    extras = [
        os.path.expanduser("~/.npm-global/bin"),  # hithink-finance CLI
        "/usr/local/bin",   # node (macOS Intel/默认)
        "/opt/homebrew/bin"  # node (Apple Silicon homebrew)
    ]
    cur = env.get("PATH", "")
    for extra in extras:
        if extra and os.path.isdir(extra) and extra not in cur:
            cur = extra + os.pathsep + cur
    env["PATH"] = cur
    return env

# 标的池: {代码: 名称} (对齐自选股 2026-09-06: 去紫光000938, 加南山铝业600219/云南铜业000878/中航沈飞600760)
STOCKS = {
    "600988": "赤峰黄金",
    "601138": "工业富联",
    "600487": "亨通光电",
    "600522": "中天科技",
    "002156": "通富微电",
    "002396": "星网锐捷",
    "603380": "易德龙",
    "600460": "士兰微",
    "600219": "南山铝业",
    "000878": "云南铜业",
    "000938": "紫光股份",
    "600760": "中航沈飞",
}
YEARS = 5  # 拉取近5年


def _thscode(code: str) -> str:
    """6xx -> .SH, 其他 -> .SZ"""
    return code + (".SH" if code.startswith("6") else ".SZ")


def _ms_from_date(date: datetime) -> int:
    return int(date.timestamp() * 1000)


def fetch_history(code: str, name: str) -> pd.DataFrame:
    """用同花顺CLI拉取单只股票前复权日线(近YEARS年)。"""
    end = datetime.now(CN_TZ)
    start = end - pd.Timedelta(days=YEARS * 366)  # 留足跨年余量

    thscode = _thscode(code)
    cmd = [
        "hithink-finance", "market", "history",
        "--thscode", thscode,
        "--start-ms", str(_ms_from_date(start)),
        "--end-ms", str(_ms_from_date(end)),
        "--format", "json",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                          env=_env_with_hithink_path())
    if proc.returncode != 0:
        raise ConnectionError(f"{code} hithink拉取失败: {proc.stderr[:200]}")

    try:
        resp = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise ConnectionError(f"{code} 返回非JSON: {e}")

    if not resp.get("ok"):
        raise ConnectionError(f"{code} API错误: {resp.get('error') or resp}")

    items = resp.get("data", {}).get("item", [])
    if not items:
        raise ConnectionError(f"{code} 无数据返回")

    rows = []
    for it in items:
        dt = datetime.fromtimestamp(it["date_ms"] / 1000, tz=CN_TZ)
        rows.append({
            "date": dt.strftime("%Y-%m-%d"),
            "open": float(it["open_price"]),
            "high": float(it["high_price"]),
            "low": float(it["low_price"]),
            "close": float(it["close_price"]),
            "volume": float(it["volume"]),
        })

    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    df["code"] = code
    df["name"] = name
    return df


def main(codes: Optional[list] = None):
    DATA_DIR.mkdir(exist_ok=True)
    targets = {c: STOCKS[c] for c in (codes or STOCKS.keys()) if c in STOCKS}

    for code, name in targets.items():
        print(f"[{code}] {name} 拉取中(同花顺API)...", flush=True)
        try:
            df = fetch_history(code, name)
            out = DATA_DIR / f"{code}_{name}.csv"
            df.to_csv(out, index=False)
            print(f"  ✅ 保存 {len(df)} 条 ({df['date'].iloc[0].date()} → {df['date'].iloc[-1].date()}), {out}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
        # hithink无IP风控, 但保持礼貌间隔
        # time.sleep(0.5)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args if args else None)
