"""
信号库检索工具 (简化版 RAG 检索端)
================================
从 signal_library.json 检索与某场景/股票/关键词相关的交易信号。

用法:
    python search_signals.py "缩量 低吸"          # 关键词检索
    python search_signals.py --stock 601138      # 按股票检索
    python search_signals.py --type entry        # 按类型检索(entry/exit/risk/filter)
    python search_signals.py --all               # 列出全部信号
    python search_signals.py --add               # 交互式新增信号(提示输入)

检索说明:
- 默认对 name/logic/trigger/scenario/notes 做关键词匹配
- 返回匹配信号 + 可靠性评级, 供 Hermes 生成新信号前参考
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LIB_PATH = Path(__file__).parent / "signal_library.json"


def load_library() -> dict:
    with open(LIB_PATH, encoding="utf-8") as f:
        return json.load(f)


def search(query: str, lib: dict) -> list:
    """在信号库中检索, 返回按可靠性排序的匹配信号."""
    q = query.lower()
    fields = ["name", "logic", "trigger", "scenario", "notes", "stocks"]
    hits = []
    for s in lib["signals"]:
        text = " ".join(str(s.get(f, "")) for f in fields).lower()
        score = 0
        for kw in q.split():
            if kw in text:
                score += 1
        if score > 0:
            # 可靠性加权
            rel_boost = {"high": 2, "medium": 1, "low": 0.5, "unverified": 0}.get(
                s.get("reliability", "medium"), 0)
            hits.append((score + rel_boost, s))
    hits.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in hits]


def by_stock(code: str, lib: dict) -> list:
    return [s for s in lib["signals"] if code in " ".join(s.get("stocks", []))]


def by_type(t: str, lib: dict) -> list:
    return [s for s in lib["signals"] if s.get("type") == t]


def fmt(s: dict) -> str:
    lines = [
        f"【{s['id']}】{s['name']}  [{s['type']}]  可靠性:{s.get('reliability','medium')}",
        f"  逻辑: {s['logic']}",
        f"  触发: {s['trigger']}",
        f"  参数: {s['params']}",
        f"  适用: {s['scenario']}",
    ]
    if s.get("validation"):
        lines.append(f"  验证: {s['validation']}")
    if s.get("stocks"):
        lines.append(f"  股票: {', '.join(s['stocks'])}")
    if s.get("live_pnl"):
        lines.append(f"  实盘: {'; '.join(map(str, s['live_pnl']))}")
    if s.get("notes"):
        lines.append(f"  备注: {s['notes']}")
    return "\n".join(lines)


def interactive_add(lib: dict) -> None:
    """交互式新增信号."""
    print("交互式新增信号(直接回车可跳过可选字段):")
    s = {
        "id": f"SIG-{len(lib['signals'])+1:03d}",
        "name": input("信号名称: ").strip(),
        "type": input("类型(entry/exit/risk/filter): ").strip() or "entry",
        "logic": input("核心逻辑: ").strip(),
        "trigger": input("触发条件: ").strip(),
        "params": {},
        "scenario": input("适用场景: ").strip(),
        "validation": input("验证数据(回测/IC): ").strip(),
        "reliability": input("可靠性(high/medium/low/unverified): ").strip() or "unverified",
        "stocks": [x.strip() for x in input("相关股票(逗号分隔, 如601138工业富联): ").split(",") if x.strip()],
        "live_pnl": [],
        "notes": input("备注: ").strip(),
    }
    if not s["name"] or not s["logic"]:
        print("❌ 名称和逻辑必填, 已放弃")
        return
    lib["signals"].append(s)
    with open(LIB_PATH, "w", encoding="utf-8") as f:
        json.dump(lib, f, ensure_ascii=False, indent=2)
    print(f"✅ 已保存 {s['id']} {s['name']}")


def main():
    lib = load_library()
    args = sys.argv[1:]

    if "--add" in args:
        interactive_add(lib)
        return
    if "--all" in args:
        hits = lib["signals"]
        title = f"全部信号 ({len(hits)})"
    elif "--stock" in args:
        code = args[args.index("--stock") + 1]
        hits = by_stock(code, lib)
        title = f"股票 {code} 相关信号 ({len(hits)})"
    elif "--type" in args:
        t = args[args.index("--type") + 1]
        hits = by_type(t, lib)
        title = f"类型 {t} 的信号 ({len(hits)})"
    elif args:
        q = " ".join(args)
        hits = search(q, lib)
        title = f"检索 \"{q}\" 命中 ({len(hits)})"
    else:
        hits = lib["signals"]
        title = f"全部信号 ({len(hits)})"

    print(f"📚 {title}\n" + "=" * 40)
    if not hits:
        print("  无匹配信号")
    for s in hits:
        print(fmt(s))
        print()


if __name__ == "__main__":
    main()
