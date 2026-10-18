#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""04_summary.py —— 生成数据集自身的分布统计，用于核对 README / codebook 里的数字。

这个脚本不做分析，只做**可复算的计数**。论文里出现的每一个来自本数据集的数字，
都应该能在这里跑出来。跑不出来就说明论文里那个数不是从这份数据来的。

用法
----
    python scripts/04_summary.py

输入  data/fec_events_clean.csv
输出  docs/summary.txt（人读）
      data/summary_counts.csv（机读，两个维度：scale / region / year / status / type / venue_type）
"""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"

SRC = DATA / "fec_events_clean.csv"
OUT_TXT = DOCS / "summary.txt"
OUT_CSV = DATA / "summary_counts.csv"

# 源站 i18n 里的官方档位定义（raw/years.json → _nextI18Next → zh-Hans → common）
SCALE_LABEL = {
    "cosy": "迷你（0-100）",
    "small": "小型（100-500）",
    "medium": "中型（500-1000）",
    "large": "大型（1000-3000）",
    "xlarge": "特大型（3000-5000）",
    "xxlarge": "超特大型（5000以上）",
    "mega": "巨型（10000以上）",
}
SCALE_ORDER = ["cosy", "small", "medium", "large", "xlarge", "xxlarge", "mega"]

TYPE_LABEL = {
    "all-in-con": "综合性展会",
    "comic-market": "贩售展会",
    "fandom-meetup": "专项聚会",
    "suit-only-con": "毛毛聚会",
    "travel-con": "旅游聚会",
}
VENUE_LABEL = {"hotel": "酒店", "venue": "场馆", "online": "线上"}


def main() -> int:
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig", newline="")))
    lines: list[str] = []
    counts: list[tuple[str, str, str, int]] = []

    def say(s: str = "") -> None:
        lines.append(s)

    def tab(dim: str, counter: Counter, label: dict | None = None, order: list | None = None):
        items = counter.most_common()
        if order:
            items = [(k, counter[k]) for k in order if counter[k]]
            items += [(k, v) for k, v in counter.most_common() if k not in order]
        total = sum(counter.values())
        for k, v in items:
            name = f"{k}（{label[k]}）" if label and k in label else (k or "(缺失)")
            say(f"    {name:<22s} {v:>4d}   {v/total*100:5.1f}%")
            counts.append((dim, k or "", "", v))
        if "" in counter or any(k == "" for k in counter):
            pass
        say(f"    {'合计':<22s} {total:>4d}")
        say("")

    say("FEC 中国兽展数据集 · 分布统计")
    say("=" * 64)
    say(f"总记录数 : {len(rows)}")
    say(f"年份范围 : {min(r['year'] for r in rows)} – {max(r['year'] for r in rows)}")
    say(f"城市数   : {len({r['city'] for r in rows})}")
    say(f"主办方数 : {len({r['org_slug'] for r in rows})}")
    say("")

    say("【规模档位 scale】定义取自源站 i18n，括号内为到场人数的预估区间，不是实测人数。")
    tab("scale", Counter(r["scale"] for r in rows), SCALE_LABEL, SCALE_ORDER)

    say("【区域 region】由源站 macro_region 映射，见 03_clean.py 规则 3。")
    tab("region", Counter(r["region"] for r in rows))

    say("【宏观区域 macro_region】源站自带的七个分区，原样保留。")
    tab("macro_region", Counter(r["macro_region"] for r in rows))

    say("【状态 status】")
    tab("status", Counter(r["status"] for r in rows))

    say("【类型 type】空值是源站就没有填，本数据集不推断。")
    tab("type", Counter(r["type"] for r in rows), TYPE_LABEL)

    say("【场地类型 venue_type】")
    tab("venue_type", Counter(r["venue_type"] for r in rows), VENUE_LABEL)

    say("【年份 year】")
    years = sorted({r["year"] for r in rows})
    yc = Counter(r["year"] for r in rows)
    for y in years:
        say(f"    {y}   {yc[y]:>4d}")
        counts.append(("year", y, "", yc[y]))
    say(f"    {'合计':<6s} {sum(yc.values()):>4d}")
    say("")

    say("【天数 days】由起止日期重算，含首尾。")
    dc = Counter(r["days"] for r in rows)
    for d in sorted(dc, key=lambda x: (len(x), x)):
        say(f"    {d:>4s} 天   {dc[d]:>4d}")
        counts.append(("days", d, "", dc[d]))
    say("")

    say("【城市前 15 名】")
    cc = Counter(r["city"] for r in rows)
    for city, n in cc.most_common(15):
        say(f"    {city:<8s} {n:>4d}")
        counts.append(("city", city, "", n))
    say("")

    say("【主办方前 15 名】按 org_slug 计，同一主办方多个城市合并。")
    oc = Counter((r["org_slug"], r["org_name"]) for r in rows)
    for (slug, name), n in oc.most_common(15):
        say(f"    {name:<24s} {slug:<22s} {n:>3d}")
        counts.append(("org", slug, name, n))
    say("")

    say("【年度 × 区域】")
    grid: dict[tuple[str, str], int] = defaultdict(int)
    for r in rows:
        grid[(r["year"], r["region"])] += 1
    regions = ["中国大陆", "台湾", "香港"]
    say("    年份   " + "".join(f"{x:>10s}" for x in regions) + f"{'合计':>8s}")
    for y in years:
        vals = [grid[(y, rg)] for rg in regions]
        say(f"    {y}   " + "".join(f"{v:>10d}" for v in vals) + f"{sum(vals):>8d}")
    say("")

    say("=" * 64)
    say("口径提醒：")
    say("  1. 规模档位是**预估**，不是到场人数。源站原文：「预估这是一个 X 的兽展」。")
    say("  2. 本数据集不含任何到场人数、票房、观众构成数据——源站没有这些字段。")
    say("  3. 2027 年的记录是已公布排期，未必全部举办。")
    say("  4. 源站会删除条目；本文件是 2026-10-17 的快照，见 docs/snapshot_diff.txt。")

    text = "\n".join(lines) + "\n"
    OUT_TXT.write_text(text, encoding="utf-8")

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["dimension", "value", "label", "count"])
        w.writerows(counts)

    print(text)
    print(f"[OK] {OUT_TXT}")
    print(f"[OK] {OUT_CSV}  {len(counts)} 行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
