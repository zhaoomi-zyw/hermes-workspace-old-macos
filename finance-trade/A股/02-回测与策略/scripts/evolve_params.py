"""
DSA 参数遗传规划进化层
=====================
用遗传算法自动搜索比手工更优的 DSA 参数组合, 并做样本外验证防过拟合。

思路(源自 Alpha-GPT 论文的"搜索增强 + 防过拟合"):
- 时间切分: 每只股票前 70% 数据做进化(in-sample), 后 30% 做验证(out-of-sample)
- 遗传算子: 锦标赛选择 + 均匀交叉 + 高斯变异 + 精英保留
- 适应度: 样本内夏普比(带交易惩罚, 防过度拟合噪音)
- 评估: 进化后把最优个体放到样本外回测, 若样本外也表现好 → 泛化参数

用法:
    python evolve_params.py                        # 全部有CSV的股票
    python evolve_params.py 601138 601899          # 指定股票
    python evolve_params.py --gens 20 --popsize 40 # 自定义进化规模
    python evolve_params.py --train 0.7            # 训练集占比
"""
from __future__ import annotations

import sys
import random
from pathlib import Path
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from strategies.dsa_strategy import backtest_dsa, DSAConfig
from strategies.ma_strategy import load_data

# 可用CSV的股票
STOCKS = {
    "601138": "工业富联",
    "601899": "紫金矿业",
    "600487": "亨通光电",
    "000938": "紫光股份",
}


# 默认基准参数(你当前的手工调参结果)
DEFAULT_PARAMS = {
    "lookback": 20, "vol_window": 5,
    "shrink_coef": 0.8, "expand_coef": 1.5,
    "stop_loss": 0.07, "trend_exit_ma": 60,
    "profit_lock": 0.03, "trailing_stop": 0.05,
    "exit_mode": "trend",
}

# 进化参数的范围(离散整数 / 连续浮点)
PARAM_RANGES = {
    "lookback": (10, 40, int),        # 支撑/压力窗口
    "shrink_coef": (0.5, 0.95, float),  # 缩量系数
    "expand_coef": (1.2, 2.5, float),   # 放量系数
    "trailing_stop": (0.02, 0.08, float),  # 移动止损
    "profit_lock": (0.0, 0.06, float),  # 盈利保护
    "stop_loss": (0.05, 0.12, float),   # 硬止损
    "trend_exit_ma": (20, 60, int),    # 趋势离场均线
}


def make_cfg(params: dict, initial_cash: float = 100_000.0) -> DSAConfig:
    """把参数字典转成 DSAConfig."""
    merged = {**DEFAULT_PARAMS, **params}
    # 浮点四舍五入到合理精度, 整数取整
    clean = {}
    for k, v in merged.items():
        if k in PARAM_RANGES and PARAM_RANGES[k][2] is int:
            clean[k] = int(round(v))
        elif isinstance(v, float):
            clean[k] = round(v, 3)
        else:
            clean[k] = v
    return DSAConfig(initial_cash=initial_cash, **clean)


def fitness(cfg: DSAConfig, df: pd.DataFrame) -> float:
    """适应度: 样本内回测的综合得分(夏普主导 + 收益 + 交易惩罚)."""
    try:
        r = backtest_dsa(df, cfg)
        m = r.metrics
    except Exception:
        return -999.0
    def num(v, default=0.0):
        try:
            s = str(v).rstrip("%")
            return float(s)
        except Exception:
            return default
    sharpe = num(m.get("夏普比率", 0), 0)
    total = num(m.get("累计收益", 0), 0)
    trades = int(m.get("交易次数", 0))
    # 交易太少没意义, 太多是噪音; 目标区间 8-40 笔
    trade_penalty = 0.0
    if trades < 6:
        trade_penalty = -1.0
    elif trades > 60:
        trade_penalty = -0.5
    return sharpe + 0.05 * total / 100.0 + trade_penalty


def init_individual() -> dict:
    """随机初始化一个参数个体(带默认值附近扰动 + 随机探索)."""
    ind = {}
    for k, (lo, hi, typ) in PARAM_RANGES.items():
        if random.random() < 0.4:
            # 40% 概率从默认值附近采样
            v = DEFAULT_PARAMS.get(k, (lo + hi) / 2)
            v = v * random.uniform(0.85, 1.15)
        else:
            v = random.uniform(lo, hi)
        ind[k] = int(round(v)) if typ is int else round(v, 3)
    return ind


def mutate(ind: dict, prob: float = 0.3) -> dict:
    """高斯变异."""
    out = dict(ind)
    for k, (lo, hi, typ) in PARAM_RANGES.items():
        if random.random() < prob:
            v = out[k]
            scale = (hi - lo) * 0.15
            v = v + random.gauss(0, scale)
            v = max(lo, min(hi, v))
            out[k] = int(round(v)) if typ is int else round(v, 3)
    return out


def crossover(a: dict, b: dict) -> dict:
    """均匀交叉."""
    child = {}
    for k in PARAM_RANGES:
        child[k] = a[k] if random.random() < 0.5 else b[k]
    return child


def evolve(df: pd.DataFrame, pop_size: int = 30, gens: int = 15,
           elite: int = 3) -> tuple:
    """遗传算法主循环, 返回 (最优个体, 最优适应度, 进化历史)."""
    # 锦标赛选择
    def select(pop, fits):
        i = random.randrange(len(pop))
        for _ in range(3):
            j = random.randrange(len(pop))
            if fits[j] > fits[i]:
                i = j
        return pop[i]

    pop = [init_individual() for _ in range(pop_size)]
    best_ind, best_fit = None, -999
    history = []
    for gen in range(gens):
        fits = [fitness(make_cfg(ind), df) for ind in pop]
        # 精英保留
        ranked = sorted(range(len(pop)), key=lambda i: fits[i], reverse=True)
        new_pop = [pop[i] for i in ranked[:elite]]
        # 生成下一代
        while len(new_pop) < pop_size:
            a = select(pop, fits)
            b = select(pop, fits)
            child = crossover(a, b)
            child = mutate(child)
            new_pop.append(child)
        pop = new_pop
        gen_best = max(fits)
        if gen_best > best_fit:
            best_fit = gen_best
            best_ind = pop[ranked[0]].copy()
        history.append(gen_best)
    return best_ind, best_fit, history


def eval_one(code: str, name: str, train_ratio: float = 0.7,
             pop_size: int = 30, gens: int = 15, initial_cash: float = 100_000.0) -> str:
    """对单只股票: 样本内进化 + 样本外验证."""
    path = Path("data") / f"{code}_{name}.csv"
    if not path.exists():
        return f"[{code}] {name} 无本地CSV({path.name}), 跳过"

    df = load_data(code, name)
    if len(df) < 120:
        return f"[{code}] {name} 数据不足({len(df)}行), 跳过"

    split = int(len(df) * train_ratio)
    train_df = df.iloc[:split].reset_index(drop=True)
    test_df = df.iloc[split:].reset_index(drop=True)

    # 默认参数基准(样本内+样本外)
    def run(df, cfg):
        r = backtest_dsa(df, cfg)
        m = r.metrics
        return m
    base_cfg = make_cfg(DEFAULT_PARAMS, initial_cash)
    base_train = run(train_df, base_cfg)
    base_test = run(test_df, base_cfg)

    # 遗传进化(在样本内)
    best_ind, best_fit, history = evolve(train_df, pop_size, gens)
    best_cfg = make_cfg(best_ind, initial_cash)
    best_train = run(train_df, best_cfg)
    best_test = run(test_df, best_cfg)

    def num(m, k, default=0.0):
        try:
            return float(str(m.get(k, default)).rstrip("%"))
        except Exception:
            return default

    lines = [
        f"▎{name} ({code}) — 遗传规划参数进化  样本{len(df)}日 "
        f"(训练{len(train_df)}/验证{len(test_df)})",
        f"  默认参数: {DEFAULT_PARAMS}",
        f"    样本内: 累计{num(base_train,'累计收益'):+.1f}% 夏普{num(base_train,'夏普比率'):.2f} "
        f"回撤{num(base_train,'最大回撤'):+.1f}% 交易{base_train.get('交易次数')}",
        f"    样本外: 累计{num(base_test,'累计收益'):+.1f}% 夏普{num(base_test,'夏普比率'):.2f} "
        f"回撤{num(base_test,'最大回撤'):+.1f}% 交易{base_test.get('交易次数')}",
        f"  进化最优参数: {best_ind}  (适应度{best_fit:+.2f})",
        f"    样本内: 累计{num(best_train,'累计收益'):+.1f}% 夏普{num(best_train,'夏普比率'):.2f} "
        f"回撤{num(best_train,'最大回撤'):+.1f}% 交易{best_train.get('交易次数')}",
        f"    样本外: 累计{num(best_test,'累计收益'):+.1f}% 夏普{num(best_test,'夏普比率'):.2f} "
        f"回撤{num(best_test,'最大回撤'):+.1f}% 交易{best_test.get('交易次数')}",
    ]
    # 判断是否改进
    oos_improve = num(best_test, "夏普比率") - num(base_test, "夏普比率")
    oos_ret_improve = num(best_test, "累计收益") - num(base_test, "累计收益")
    if oos_improve > 0.1 and oos_ret_improve > 5:
        lines.append(f"  ✅ 进化参数样本外更优: 夏普+{oos_improve:+.2f}, 收益+{oos_ret_improve:+.1f}%")
    elif oos_improve > 0:
        lines.append(f"  ⚠️ 样本外略改善: 夏普+{oos_improve:+.2f}")
    else:
        lines.append(f"  ❌ 样本外未改善(夏普{oos_improve:+.2f}), 默认参数可能已足够/数据有噪声")
    return "\n".join(lines)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    pop_size, gens, train_ratio = 30, 15, 0.7
    if "--gens" in sys.argv:
        gens = int(sys.argv[sys.argv.index("--gens") + 1])
    if "--popsize" in sys.argv:
        pop_size = int(sys.argv[sys.argv.index("--popsize") + 1])
    if "--train" in sys.argv:
        train_ratio = float(sys.argv[sys.argv.index("--train") + 1])

    targets = {c: STOCKS[c] for c in (args or STOCKS.keys()) if c in STOCKS}
    print(f"DSA 参数遗传规划进化 · {gens}代 × {pop_size}个体 · 训练占比{train_ratio}\n" + "=" * 60)
    for code, name in targets.items():
        print(eval_one(code, name, train_ratio, pop_size, gens))
        print()
    print("=" * 60)
    print("说明: 样本内(前70%)进化, 样本外(后30%)验证防过拟合;")
    print("     进化参数若样本外也优于默认 → 泛化更好, 可替换手工参数。")


if __name__ == "__main__":
    main()
