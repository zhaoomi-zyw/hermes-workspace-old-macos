"""
DSA 信号 IC 评估层
=================
衡量 DSA 各个信号(缩量回踩/放量突破/支撑压力/趋势)对未来收益的预测能力。

IC (Information Coefficient) = 信号值与未来 N 日收益的相关系数
  - RankIC: 用 Spearman 秩相关(更稳健, 不依赖线性关系)
  - 它回答一个关键问题: "这个信号到底有没有预测力, 还是只是盘感?"

用法:
    python ic_eval.py                     # 全部自选股
    python ic_eval.py 601138 002475       # 指定股票
    python ic_eval.py --horizon 3 5       # 自定义未来收益窗口(默认1,3,5日)
    python ic_eval.py --lookback 250      # 用最近N个交易日评估

输出(纯文本):
- 每只股票的 IC / IR / 胜率 / 信号覆盖率
- 买入类信号与卖出类信号分开评估
"""
from __future__ import annotations

import sys
import numpy as np
import pandas as pd

from strategies.dsa_strategy import DSAConfig


def _rankdata(a: np.ndarray) -> np.ndarray:
    """手写秩转换(平均秩), 等价 scipy.stats.rankdata, 避免依赖 scipy."""
    a = np.asarray(a, dtype=float)
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    i = 0
    while i < len(a):
        j = i
        while j + 1 < len(a) and a[order[j + 1]] == a[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1  # 1-based 平均秩
        ranks[order[i:j + 1]] = avg
        i = j + 1
    return ranks


def spearmanr(a: np.ndarray, b: np.ndarray):
    """手写 Spearman 秩相关, 返回 (rho, p_value近似). 用 Pearson(rank,rank)."""
    a = np.asarray(a, dtype=float).flatten()
    b = np.asarray(b, dtype=float).flatten()
    n = len(a)
    ra = _rankdata(a)
    rb = _rankdata(b)
    ma, mb = ra.mean(), rb.mean()
    cov = np.sum((ra - ma) * (rb - mb))
    va = np.sqrt(np.sum((ra - ma) ** 2) * np.sum((rb - mb) ** 2))
    rho = cov / va if va > 0 else 0.0
    return rho, None
from fetch_data import fetch_history

STOCKS = {
    "601899": "紫金矿业", "601138": "工业富联", "002475": "立讯精密",
    "000807": "云铝股份", "002156": "通富微电", "600487": "亨通光电",
    "000938": "紫光股份", "688097": "博众精工", "603380": "易德龙",
    "600988": "赤峰黄金", "600460": "士兰微", "600522": "中天科技",
}

PER_STOCK_CFG = {
    "601899": dict(exit_mode="target", tp1=0.10, tp2=0.20, stop_loss=0.07),
    "601138": dict(exit_mode="trend", stop_loss=0.10, trend_exit_ma=30,
                   profit_lock=0.02, trailing_stop=0.03),
}


def get_cfg(code: str) -> DSAConfig:
    return DSAConfig(**PER_STOCK_CFG.get(code, {}))


def build_signal_frame(df: pd.DataFrame, cfg: DSAConfig) -> pd.DataFrame:
    """构建带 DSA 信号标签的评估帧(纯信号构造, 不涉及未来收益)."""
    d = df.copy().sort_values("date").reset_index(drop=True)
    lb = cfg.lookback
    d["support"] = d["low"].rolling(lb, min_periods=lb).min().shift(1)
    d["resistance"] = d["high"].rolling(lb, min_periods=lb).max().shift(1)
    d["vol_ma"] = d["volume"].rolling(cfg.vol_window, min_periods=1).mean()
    d["trend_ma"] = d["close"].rolling(cfg.trend_exit_ma, min_periods=cfg.trend_exit_ma).mean()
    d["prev_close"] = d["close"].shift(1)

    close = d["close"]
    low = d["low"]
    vol = d["volume"]
    sup = d["support"]
    res = d["resistance"]
    vma = d["vol_ma"]
    tma = d["trend_ma"]

    shrink = vol < vma * cfg.shrink_coef
    expand = vol > vma * cfg.expand_coef
    near_sup = low <= sup * 1.02
    broke_res = close > res

    # 信号标签(每日一行, 用昨日支撑压力避免未来函数)
    # 买入类: 1=缩量回踩支撑(低吸), 2=放量突破压力
    # 卖出类: -1=跌破支撑, -2=跌破趋势(仅盈利保护后, 对齐dsa_strategy的locked逻辑)
    sig = np.zeros(len(d), dtype=int)
    valid = sup.notna() & res.notna()

    # ---- 盈利保护代理(对齐 dsa_strategy 的 locked = pnl_pct >= profit_lock) ----
    # 模拟最近一次"潜在买入": 用近 lookback 日低点作为假设成本价(近似缩量回踩入场)
    # 现价相对该成本盈利超 profit_lock 才认为"已有盈利保护", 此时跌破趋势才算卖出信号
    assumed_cost = d["low"].rolling(lb, min_periods=lb).min().shift(1)
    locked = (close / assumed_cost - 1) >= cfg.profit_lock
    # 只在有盈利保护且确实跌破趋势时标记卖出(消除"跌破MA即卖"的噪音)
    sig[((close < tma) & tma.notna() & locked) & valid] = -2

    # 跌破支撑(硬止损, 任何时候都算卖出信号, 对齐 hard_stop)
    sig[(close < sup) & valid] = -1
    # 买入信号
    sig[(near_sup & shrink) & valid] = 1
    sig[(broke_res & expand) & valid] = 2
    d["signal"] = sig

    # 次日(避免同一天价格和信号的相关性噪声)及未来收益: shift(-h) 用未来收盘/当前收盘-1
    # 收益用次日开盘到未来N日收盘, 避免使用当日收盘(与信号同源)
    d["next_open"] = d["open"].shift(-1)
    for h in (1, 3, 5):
        d[f"fwd_{h}"] = d["close"].shift(-h) / d["next_open"] - 1
    return d


def eval_ic(frame: pd.DataFrame, horizon: int = 3, label: str = "") -> dict:
    """计算指定 horizon 的 IC. 用信号类别转数值分桶做秩相关."""
    d = frame.dropna(subset=["signal", f"fwd_{horizon}"])
    # 信号数值本身只有{-2,-1,0,1,2}, 秩相关有效
    sig = d["signal"].astype(float).values
    fwd = d[f"fwd_{horizon}"].values
    if len(sig) < 10:
        return {"n": len(sig), "ic": None, "ir": None, "win": None, "label": label}

    ic, _ = spearmanr(sig, fwd)
    # IR = 平均IC / IC标准差(稳健信息比率, 类似夏普但基于IC)
    # 分块计算IC序列: 每~21个交易日一块
    ic_series = []
    blk = 21
    for s in range(0, len(sig) - blk + 1, blk):
        ic_b, _ = spearmanr(sig[s:s+blk], fwd[s:s+blk])
        if not np.isnan(ic_b):
            ic_series.append(ic_b)
    ir = float(np.mean(ic_series) / np.std(ic_series)) if len(ic_series) > 2 else None
    # 胜率: 信号为正(买入)时未来上涨比例, 信号为负(卖出)时未来下跌比例
    buy = sig > 0
    sell = sig < 0
    win = None
    if buy.any():
        win_buy = (fwd[buy] > 0).mean()
        if sell.any():
            win_sell = (fwd[sell] < 0).mean()
            win = (win_buy * buy.sum() + win_sell * sell.sum()) / (buy.sum() + sell.sum())
        else:
            win = win_buy
    return {"n": len(sig), "ic": ic, "ir": ir, "win": win, "label": label}


def eval_buy_sell(frame: pd.DataFrame, horizon: int = 3) -> dict:
    """分别评估买入类与卖出类信号的胜率."""
    d = frame.dropna(subset=["signal", f"fwd_{horizon}"])
    out = {}
    buy = d[d["signal"] > 0]
    sell = d[d["signal"] < 0]
    out["buy_n"] = len(buy)
    out["buy_win"] = (buy[f"fwd_{horizon}"] > 0).mean() if len(buy) else None
    out["sell_n"] = len(sell)
    out["sell_win"] = (sell[f"fwd_{horizon}"] < 0).mean() if len(sell) else None
    # 平均未来收益(买入类信号触发后的平均涨幅)
    out["buy_avg_fwd"] = buy[f"fwd_{horizon}"].mean() if len(buy) else None
    out["sell_avg_fwd"] = sell[f"fwd_{horizon}"].mean() if len(sell) else None
    return out


def compute_macd(df: pd.DataFrame, short=12, long=26, signal=9) -> pd.DataFrame:
    """计算 MACD 指标列(标准12/26/9)."""
    d = df.copy()
    ema_short = d["close"].ewm(span=short, adjust=False).mean()
    ema_long = d["close"].ewm(span=long, adjust=False).mean()
    d["macd_dif"] = ema_short - ema_long
    d["macd_dea"] = d["macd_dif"].ewm(span=signal, adjust=False).mean()
    d["macd_hist"] = d["macd_dif"] - d["macd_dea"]
    return d


def macd_golden_cross(df: pd.DataFrame, below_zero_only=True) -> pd.Series:
    """MACD 金叉信号(布尔). 可选仅零轴下方.

    金叉 = DIF 上穿 DEA(前一日 DIF<=DEA, 今日 DIF>DEA).
    below_zero_only=True 时, 仅统计发生在 DIF<0 区间的金叉(超跌反弹/底部信号).
    """
    d = compute_macd(df)
    cross = (d["macd_dif"].shift(1) <= d["macd_dea"].shift(1)) & \
            (d["macd_dif"] > d["macd_dea"])
    if below_zero_only:
        cross = cross & (d["macd_dif"] < 0)
    return cross.fillna(False)


def eval_macd(code: str, name: str, horizons=(3, 5), lookback=None,
              below_zero_only=True) -> str:
    """评估 MACD 金叉(含零轴下二次金叉思路)触发后的未来收益胜率.

    注意: MACD 是"事件"信号, 不适合混入主IC的连续数值序列, 这里单独评估
    "金叉触发后N日"的胜率和平均收益.
    """
    try:
        df = fetch_history(code, name)
    except Exception as e:
        return f"[{code}] {name} 数据失败: {e}"
    if lookback and len(df) > lookback:
        df = df.tail(lookback)
    if len(df) < 100:
        return f"[{code}] {name} 数据不足"

    d = compute_macd(df).copy().reset_index(drop=True)
    cross = macd_golden_cross(d, below_zero_only)
    d["cross"] = cross
    # 未来N日收益(用次日开盘避免与信号同日收盘同源)
    d["next_open"] = d["open"].shift(-1)
    for h in horizons:
        d[f"fwd_{h}"] = d["close"].shift(-h) / d["next_open"] - 1

    lines = [f"▎{name} ({code}) — MACD{'零轴下' if below_zero_only else ''}金叉评估  样本{len(d)}日"]
    total_cross = int(cross.sum())
    lines.append(f"  金叉触发次数: {total_cross}  (触发率{total_cross/len(d)*100:.1f}%)")
    for h in horizons:
        hit = d[d["cross"]].dropna(subset=[f"fwd_{h}"])
        if len(hit) < 5:
            lines.append(f"  未来{h}日: 样本不足({len(hit)}次)")
            continue
        win = (hit[f"fwd_{h}"] > 0).mean()
        avg = hit[f"fwd_{h}"].mean()
        lines.append(f"  未来{h}日: 胜率{win*100:.0f}%  平均收益{avg*100:+.2f}%  (样本{len(hit)}次)")
    # 解读
    h3 = d[d["cross"]].dropna(subset=["fwd_3"])
    if len(h3) >= 5:
        win3 = (h3["fwd_3"] > 0).mean()
        avg3 = h3["fwd_3"].mean()
        if win3 >= 0.55 and avg3 > 0:
            lines.append(f"  解读: 金叉后3日胜率{win3*100:.0f}%/均涨{avg3*100:+.2f}% → 信号有一定价值")
        elif win3 < 0.5:
            lines.append(f"  解读: 金叉后3日胜率仅{win3*100:.0f}% → 该信号无显著预测力")
        else:
            lines.append(f"  解读: 胜率{win3*100:.0f}% → 信号中性, 待更多样本")
    return "\n".join(lines)


def eval_one(code: str, name: str, horizons=(1, 3, 5), lookback=None) -> str:
    """评估单只股票的 IC."""
    try:
        df = fetch_history(code, name)
    except Exception as e:
        return f"[{code}] {name} 数据失败: {e}"

    if lookback and len(df) > lookback:
        df = df.tail(lookback)
    cfg = get_cfg(code)
    frame = build_signal_frame(df, cfg)
    if len(frame) < 50:
        return f"[{code}] {name} 数据不足({len(frame)}行), 跳过IC评估"

    lines = [f"▎{name} ({code}) — DSA信号IC评估  样本{len(frame)}个交易日"]
    for h in horizons:
        r = eval_ic(frame, h, f"H{h}")
        bs = eval_buy_sell(frame, h)
        lines.append(
            f"  未来{h}日: IC={r['ic']:+.3f} | IR={r['ir']:+.2f}" if r["ic"] is not None
            else f"  未来{h}日: 样本不足"
        )
        if r["win"] is not None:
            bn = bs["buy_n"] or 0
            sn = bs["sell_n"] or 0
            bw = bs["buy_win"] or 0
            bf = bs["buy_avg_fwd"] or 0
            sw = bs["sell_win"] or 0
            lines.append(
                f"    信号胜率={r['win']*100:.0f}% | "
                f"买入信号{bn}次胜率{bw*100:.0f}% 均涨{bf*100:+.2f}% | "
                f"卖出信号{sn}次胜率{sw*100:.0f}%"
            )

    # 信号覆盖率: 有多少比例的交易日触发了非零信号
    nonzero = (frame["signal"] != 0).mean()
    lines.append(f"  信号覆盖率: {nonzero*100:.0f}% (非零信号占比)")

    # 解读
    ic_3 = eval_ic(frame, 3)["ic"]
    if ic_3 is None:
        lines.append("  解读: 样本不足, 无法判断信号预测力")
    elif abs(ic_3) < 0.03:
        lines.append("  解读: IC≈0, 该信号对未来收益基本无预测力(纯盘感)")
    elif ic_3 > 0:
        lines.append("  解读: 正向IC, 信号有一定预测力; IC>0.05则较可靠")
    else:
        lines.append("  解读: 负向IC, 信号方向可能反了(需检查信号定义)")
    return "\n".join(lines)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    horizons = [1, 3, 5]
    lookback = None
    if "--horizon" in sys.argv:
        i = sys.argv.index("--horizon")
        horizons = [int(x) for x in sys.argv[i+1].split(",")]
    if "--lookback" in sys.argv:
        i = sys.argv.index("--lookback")
        lookback = int(sys.argv[i+1])

    targets = {c: STOCKS[c] for c in (args or STOCKS.keys()) if c in STOCKS}

    # MACD 金叉单独评估(事件信号, 不混入主IC)
    if "--macd" in sys.argv:
        print(f"MACD {'零轴下' if '--anywhere' not in sys.argv else ''}金叉评估\n" + "=" * 44)
        below_zero = "--anywhere" not in sys.argv
        for code, name in targets.items():
            print(eval_macd(code, name, [3, 5], lookback, below_zero_only=below_zero))
            print()
        print("=" * 44)
        print("注: 评估'金叉触发后N日'胜率/平均收益; MACD是事件信号不参与整体IC")
        return

    print(f"DSA 信号 IC 评估 · 未来{horizons}日收益预测力\n" + "=" * 44)
    for code, name in targets.items():
        print(eval_one(code, name, horizons, lookback))
        print()
    print("=" * 44)
    print("IC 判断标准(参考): |IC|<0.03≈无预测力, 0.03-0.05弱, >0.05较可靠")
    print("注: 用次日开盘价计算收益, 避免与信号同日收盘同源; 已shift避免未来函数")


if __name__ == "__main__":
    main()
