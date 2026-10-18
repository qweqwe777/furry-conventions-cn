#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""05_fieldstats.py —— 为 codebook 生成逐字段的实测统计（缺失率 / 取值数 / 示例）。

codebook 里的每一个缺失率都应该由这个脚本产生，不要手写。
手写的数字会随数据更新而失效，而脚本跑出来的不会。

用法
----
    python scripts/05_fieldstats.py

输入  data/fec_events_clean.csv
输出  docs/field_stats.txt（人读）与 docs/field_stats.csv（机读）
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"

SRC = DATA / "fec_events_clean.csv"
OUT_TXT = DOCS / "field_stats.txt"
OUT_CSV = DOCS / "field_stats.csv"

# 每一列的来源与含义，供 codebook 直接引用
DESC = {
    "event_key": ("源站", "事件键。**不唯一**：源站允许同一页面（slug）承载多届活动，511 行里只有 499 个不同的 event_key。不要当主键。"),
    "source_id": ("源站", "源站数据库的 UUID。511 行全唯一，**这才是主键**。"),
    "name": ("源站", "活动名称。11 行是纯四位年份（源站如此），用 name_is_year 标记。"),
    "start_date": ("源站", "开始日期（本地日期，已从 UTC 换算）。"),
    "end_date": ("源站", "结束日期（本地日期）。单日活动的值与 start_date 相同。"),
    "year": ("源站", "开始日期所在年份。"),
    "weekday_start": ("源站", "开始日期的星期，汉字单字（一…日）。"),
    "days": ("派生", "含首尾的天数 =(end_date − start_date)+1。**以本列为准**。"),
    "days_published": ("源站", "源站原样给出的天数。有 7 行与重算值差 1 天，保留仅为可追溯。"),
    "scale": ("源站", "规模档位，源站给的**预估**，不是实测到场人数。定义见下方档位表。"),
    "type": ("源站", "活动类型。缺失 33.7%，源站未填，本数据集不推断。"),
    "venue_type": ("源站合并", "场地类型：locationType 缺失时取 place_kind。"),
    "status": ("源站", "活动状态。1 行缺失（源站未填）。"),
    "city": ("源站", "城市名，中文。"),
    "city_slug": ("源站", "城市名的拼音 slug，便于与源站 URL 对照。"),
    "region": ("派生", "区域：中国大陆 / 台湾 / 香港。由 macro_region 映射，见 03_clean.py 规则 3。"),
    "macro_region": ("源站", "源站自带的七个宏观分区：其他 / 长三角 / 珠三角 / 台湾 / 成渝 / 京津冀 / 港澳。"),
    "venue_name": ("源站", "场地名称（酒店名、场馆名）。原 place_name 列。"),
    "lat": ("源站", "纬度。缺失约两成。"),
    "lng": ("源站", "经度。缺失约两成。"),
    "org_slug": ("源站", "主办方的 slug，稳定标识。"),
    "org_name": ("源站", "主办方名称。"),
    "organizer_count": ("源站", "该活动的联合主办方数量。多数为 1。"),
    "info_source": ("源站", "源站标注的信息出处（WikiFur / QQ空间 / Bilibili 等），缺失率高，仅作溯引用。"),
    "url": ("源站", "源站页面地址。与 event_key 一样不唯一（同一页面多届）。"),
    "is_repeat_city": ("派生", "该城市在本数据集中此前是否已有展会（0/1）。依赖排序，见规则 1。"),
    "is_repeat_org": ("派生", "该主办方此前是否已有展会（0/1）。"),
    "first_year_in_city": ("派生", "该城市在本数据集中的首个展会年份。"),
    "org_event_seq": ("派生", "该主办方在本数据集中的第几场（从 1 起）。"),
    "same_name_city_seq": ("派生", "同名同城在本数据集中的第几场（从 1 起）。"),
    "name_is_year": ("派生", "名称是否为纯四位年份（0/1）。"),
}


def main() -> int:
    rows = list(csv.DictReader(open(SRC, encoding="utf-8-sig", newline="")))
    n = len(rows)
    lines: list[str] = []
    out: list[tuple[str, ...]] = []

    def say(s: str = "") -> None:
        lines.append(s)

    say("逐字段实测统计")
    say("=" * 78)
    say(f"数据文件 : {SRC.name}")
    say(f"记录数   : {n}")
    say(f"字段数   : {len(rows[0])}")
    say("")
    say(f"{'字段':<20s}{'缺失':>6s}{'缺失率':>9s}{'不同值':>8s}  示例")
    say("-" * 78)

    for col in rows[0].keys():
        vals = [r[col] for r in rows]
        miss = sum(1 for v in vals if v.strip() == "")
        uniq = len({v for v in vals if v.strip() != ""})
        sample = next((v for v in vals if v.strip() != ""), "")
        if len(sample) > 34:
            sample = sample[:31] + "..."
        say(f"{col:<20s}{miss:>6d}{miss/n*100:>8.1f}%{uniq:>8d}  {sample}")
        out.append((col, str(miss), f"{miss/n*100:.1f}", str(uniq), sample))

    say("")
    say("字段说明")
    say("-" * 78)
    for col in rows[0].keys():
        src, desc = DESC.get(col, ("", ""))
        say(f"· {col}  [{src}]")
        say(f"    {desc}")
        say("")

    say("=" * 78)
    say("规模档位对照（源站 i18n 原文，未改动）")
    say("-" * 78)
    scale_rows = [
        ("cosy", "迷你（0-100）"),
        ("small", "小型（100-500）"),
        ("medium", "中型（500-1000）"),
        ("large", "大型（1000-3000）"),
        ("xlarge", "特大型（3000-5000）"),
        ("xxlarge", "超特大型（5000以上）"),
        ("mega", "巨型（10000以上）"),
    ]
    c = Counter(r["scale"] for r in rows)
    say(f"{'取值':<10s}{'源站标签':<22s}{'本数据集条数':>10s}")
    for k, lab in scale_rows:
        say(f"{k:<10s}{lab:<22s}{c[k]:>10d}")
    say("")
    say("注：xxlarge 是源站定义里存在的档位，但当前 511 条记录中没有任何一条取该值。")
    say("    「巨型（10000以上）」的区间下限与「超特大型（5000以上）」重叠，是源站自身的口径问题。")

    text = "\n".join(lines) + "\n"
    OUT_TXT.write_text(text, encoding="utf-8")
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["field", "missing", "missing_pct", "distinct", "sample"])
        w.writerows(out)

    print(text)
    print(f"[OK] {OUT_TXT}")
    print(f"[OK] {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
