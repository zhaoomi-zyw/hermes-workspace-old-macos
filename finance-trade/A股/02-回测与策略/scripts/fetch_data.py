"""
数据下载脚本 · 用 akshare 拉取 A股历史日线
==========================================
拉取前复权日线并保存为 CSV，供回测使用。

用法:
    python fetch_data.py                # 拉取配置中的全部标的
    python fetch_data.py 601138         # 只拉指定代码

说明: akshare 免费数据源，需联网。若拉取失败可能是网络/数据源接口变动。
"""
import sys
import time
from pathlib import Path
from typing import Optional

import akshare as ak
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

# 标的池: {代码: 名称}
STOCKS = {
    "601138": "工业富联",
    "600487": "亨通光电",
    "000938": "紫光股份",
    "600570": "恒生电子",
}

YEARS = 5  # 拉取近5年


def _to_eastmoney_df(df: pd.DataFrame) -> pd.DataFrame:
    """东财源数据列名标准化"""
    rename = {
        "日期": "date", "开盘": "open", "收盘": "close", "最高": "high",
        "最低": "low", "成交量": "volume", "成交额": "amount",
        "振幅": "amplitude", "涨跌幅": "pct_change", "涨跌额": "change",
        "换手率": "turnover",
    }
    df = df.rename(columns=rename)
    return df


def _to_sina_df(df: pd.DataFrame, code: str, name: str) -> pd.DataFrame:
    """新浪源数据列名标准化（字段与东财不同）"""
    df = df.rename(columns={"date": "date", "open": "open", "high": "high",
                            "low": "low", "close": "close", "volume": "volume"})
    df["date"] = pd.to_datetime(df["date"])
    return df


def fetch_history(code: str, name: str, retries: int = 3) -> pd.DataFrame:
    """拉取单只股票前复权日线。优先东财源，失败回退新浪源。按年分片。"""
    end = pd.Timestamp.now().strftime("%Y-%m-%d")
    years = list(range(pd.Timestamp.now().year - YEARS, pd.Timestamp.now().year + 1))

    # 新浪代码前缀: 6开头=sh, 其他=sz
    sina_symbol = ("sh" if code.startswith("6") else "sz") + code

    frames = []
    for yr in years:
        start = f"{yr}-01-01"
        end_of_yr = f"{yr}-12-31" if yr < pd.Timestamp.now().year else end
        got = False
        # 优先东财
        for attempt in range(1, retries + 1):
            try:
                df = ak.stock_zh_a_hist(
                    symbol=code, period="daily",
                    start_date=start.replace("-", ""), end_date=end_of_yr.replace("-", ""),
                    adjust="qfq",
                )
                if df is not None and not df.empty:
                    frames.append(_to_eastmoney_df(df))
                    got = True
                    break
            except Exception:
                time.sleep(1.0 * attempt)
        if got:
            continue
        # 回退新浪
        for attempt in range(1, retries + 1):
            try:
                df = ak.stock_zh_a_daily(
                    symbol=sina_symbol, start_date=start.replace("-", ""),
                    end_date=end_of_yr.replace("-", ""), adjust="qfq",
                )
                if df is not None and not df.empty:
                    frames.append(_to_sina_df(df, code, name))
                    got = True
                    break
            except Exception:
                time.sleep(1.0 * attempt)
        if not got:
            print(f"    ⚠️ {yr}年东财+新浪均失败，跳过该年")

    if not frames:
        raise ConnectionError(f"{code} 全部年份拉取失败")

    df = pd.concat(frames, ignore_index=True)
    # 统一 date 列为 Timestamp，避免东财(date对象)+新浪(Timestamp)混拼导致的类型比较错误
    # 必须放在 sort/drop_duplicates 之前，否则 sort_values("date") 会因混合类型崩溃
    df["date"] = pd.to_datetime(df["date"])
    df = df.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    df["code"] = code
    df["name"] = name
    return df


def main(codes: Optional[list] = None):
    DATA_DIR.mkdir(exist_ok=True)
    targets = {c: STOCKS[c] for c in (codes or STOCKS.keys()) if c in STOCKS}

    for code, name in targets.items():
        print(f"[{code}] {name} 拉取中...")
        try:
            df = fetch_history(code, name)
            out = DATA_DIR / f"{code}_{name}.csv"
            df.to_csv(out, index=False)
            print(f"  ✅ 保存 {len(df)} 条, {out}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
        time.sleep(1.2)  # 避免请求过快被封


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args if args else None)
