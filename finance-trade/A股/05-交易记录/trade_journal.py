"""
交易反馈循环工具 (trade_journal.py)
=================================
制度化"信号→结果→调整"反馈循环(Alpha-GPT 论文核心结论: 交互一轮 IC 翻倍)。

用法:
    python trade_journal.py record                # 交互式记录一笔平仓交易
    python trade_journal.py stats                 # 统计信号胜率/盈亏(数据化决定去留)
    python trade_journal.py list                  # 列出全部交易
    python trade_journal.py report                # 生成信号留存建议报告

记录一笔交易后, 系统会提示: 这笔交易是否说明某信号该调整? 这是反馈循环的关键。
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import date

LIB = Path(__file__).parent
JOURNAL = LIB / "trade_journal.json"


def load() -> dict:
    with open(JOURNAL, encoding="utf-8") as f:
        return json.load(f)


def save(data: dict) -> None:
    with open(JOURNAL, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _ask(prompt: str, default: str = "") -> str:
    v = input(f"{prompt}" + (f" [{default}]" if default else "") + ": ").strip()
    return v or default


def record() -> None:
    """交互式记录一笔平仓交易, 并引导反馈循环."""
    data = load()
    t = {
        "trade_id": f"T-{len(data['trades'])+1:03d}",
        "date_entry": _ask("买入日期(YYYY-MM-DD)"),
        "date_exit": _ask("卖出日期(YYYY-MM-DD)"),
        "stock": _ask("股票(代码+名称, 如 002475立讯精密)"),
        "shares": _ask("股数", "100"),
        "entry_price": _ask("买入价"),
        "exit_price": _ask("卖出价"),
    }
    try:
        shares = int(t["shares"])
        ep = float(t["entry_price"])
        xp = float(t["exit_price"])
        t["pnl"] = round((xp - ep) * shares, 2)
        t["pnl_pct"] = round((xp / ep - 1) * 100, 2)
        t["outcome"] = "win" if t["pnl"] > 0 else ("loss" if t["pnl"] < 0 else "breakeven")
    except Exception:
        print("❌ 价格/股数格式错误, 已取消")
        return

    t["signal_id"] = _ask("触发的信号ID(查signal_library.json, 如SIG-001)", "SIG-001")
    t["signal_reason"] = _ask("信号理由(当时为什么买/卖)")
    t["holding_days"] = _ask("持仓天数")
    t["adjustment"] = _ask("这笔交易后, 是否调整信号条件?(如'保留'/'收紧'/'取消')")
    t["lesson"] = _ask("经验教训")
    t["follow_up"] = _ask("待办(是否需要重新IC验证等)", "无")

    data["trades"].append(t)
    save(data)
    # 反馈循环引导
    print("\n" + "=" * 40)
    print(f"✅ 已记录 {t['trade_id']}  {t['stock']}  PnL {t['pnl']:+.0f}元({t['pnl_pct']:+.2f}%)")
    print(f"   信号: {t['signal_id']} → 结果: {t['outcome']}")
    print(f"   调整建议: {t['adjustment'] or '(未填)'}")
    print("=" * 40)
    print("💡 反馈循环已捕获。提示: 每笔交易都在给信号库提供'该留还是该砍'的证据。")
    print("   建议执行 stats 查看累计胜率, 或继续记录下一笔。")


def stats() -> None:
    """统计信号胜率, 数据化决定信号去留."""
    data = load()
    trades = data["trades"]
    if not trades:
        print("📭 交易日志为空, 先用 record 记录第一笔。")
        return

    print(f"📊 交易统计 · 共 {len(trades)} 笔\n" + "=" * 44)
    wins = [t for t in trades if t["outcome"] == "win"]
    losses = [t for t in trades if t["outcome"] == "loss"]
    total_pnl = sum(t["pnl"] for t in trades)
    win_rate = len(wins) / len(trades) * 100
    print(f"总盈亏: {total_pnl:+.0f}元 | 胜率: {win_rate:.0f}% "
          f"({len(wins)}胜/{len(losses)}负/{len(trades)-len(wins)-len(losses)}平)")
    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t["pnl"] for t in losses) / len(losses) if losses else 0
    print(f"平均盈利: {avg_win:+.0f}元 | 平均亏损: {avg_loss:+.0f}元 | 盈亏比: "
          f"{abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "")

    # 按信号分组
    print("\n按信号ID统计:")
    by_sig = {}
    for t in trades:
        by_sig.setdefault(t["signal_id"], []).append(t)
    for sig, ts in by_sig.items():
        sw = len([t for t in ts if t["outcome"] == "win"])
        pnl = sum(t["pnl"] for t in ts)
        print(f"  {sig}: {len(ts)}笔 胜率{sw/len(ts)*100:.0f}% 累计盈亏{pnl:+.0f}元")


def list_trades() -> None:
    data = load()
    if not data["trades"]:
        print("📭 交易日志为空")
        return
    for t in data["trades"]:
        print(f"{t['trade_id']} {t['stock']} {t['date_entry']}→{t['date_exit']} "
              f"PnL {t['pnl']:+.0f}元({t['pnl_pct']:+.2f}%) [{t['outcome']}] "
              f"信号:{t['signal_id']} 调整:{t.get('adjustment','')}")


def report() -> None:
    """生成信号留存建议报告(基于反馈循环数据)."""
    data = load()
    trades = data["trades"]
    if not trades:
        print("📭 暂无交易数据, 无法生成建议。先记录几笔。")
        return
    print("📋 信号留存建议报告\n" + "=" * 44)
    by_sig = {}
    for t in trades:
        by_sig.setdefault(t["signal_id"], []).append(t)
    for sig, ts in by_sig.items():
        sw = len([t for t in ts if t["outcome"] == "win"])
        pnl = sum(t["pnl"] for t in ts)
        rate = sw / len(ts) * 100
        if len(ts) >= 5 and rate >= 60 and pnl > 0:
            verdict = "✅ 保留(胜率高且有正收益)"
        elif len(ts) >= 5 and rate < 40:
            verdict = "❌ 建议砍掉(胜率低)"
        elif len(ts) >= 3 and pnl < 0:
            verdict = "⚠️ 谨慎(有亏损, 需收紧)"
        else:
            verdict = "⏳ 样本不足, 继续积累"
        print(f"  {sig}: {len(ts)}笔 胜率{rate:.0f}% 盈亏{pnl:+.0f} → {verdict}")
    print("\n注: 建议积累20-30笔后再做最终去留决定(当前可能样本不足)。")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "record":
        record()
    elif cmd == "stats":
        stats()
    elif cmd == "list":
        list_trades()
    elif cmd == "report":
        report()
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
