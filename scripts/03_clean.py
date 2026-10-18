#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""03_clean.py —— 从 511 行原始快照生成可发布的整理版数据表。

设计原则
--------
1. 只做**可复述**的改动：每一条清洗规则都能在 codebook.md 里对应上一句规则说明。
2. 不猜。缺失就留空，异常就标记，绝不按"看起来应该是"去补。
3. 派生的计数列（第 N 次、是否重复）明确标注为派生列，排序规则写死在代码里，
   别人换一种排序会得到不同结果——这是必须公开告诉使用者的事。

保留 / 丢弃 / 改写
------------------
丢弃：slug（不唯一，且可从 url 得到）、address（511 行中与 place_name 全同）、
      place_kind（与 locationType 合并）、fetched（常量）、has_desc、detail_len、
      image_count、ticket_channel_count、source_count、pageviews
      —— 后七项是抓取器自身的状态，不是展会的属性。
合并：locationType + place_kind → venue_type（前者缺失时取后者）
改写：country（中国/台湾）→ region（中国大陆 / 台湾 / 香港）
      —— 源站把台湾与大陆并列为 country 值；本项目改为区域标签，一为避免歧义，
         二为把"港澳"从"中国大陆"里分出来（合并会让珠三角统计虚高）。
派生：days / is_repeat_city / is_repeat_org / first_year_in_city /
      org_event_seq / same_name_city_seq / name_is_year

用法
----
    python scripts/03_clean.py

输入  data/fec_snapshot_20261017.csv（511 行，见 02_snapshot.py）
输出  data/fec_events_clean.csv（511 行 × 24 列）
      docs/clean_report.txt（逐条规则的命中数）
"""

from __future__ import annotations

import csv
import sys
from datetime import date
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = ROOT / "data"
DOCS = ROOT / "docs"

SRC = DATA / "fec_snapshot_20261017.csv"
OUT = DATA / "fec_events_clean.csv"
REPORT = DOCS / "clean_report.txt"

OUT_COLUMNS = [
    "event_key",
    "source_id",
    "name",
    "start_date",
    "end_date",
    "year",
    "weekday_start",
    "days",
    "days_published",
    "scale",
    "type",
    "venue_type",
    "status",
    "city",
    "city_slug",
    "region",
    "macro_region",
    "venue_name",
    "lat",
    "lng",
    "org_slug",
    "org_name",
    "organizer_count",
    "info_source",
    "url",
    # ---- 以下为派生列，不是源站字段 ----
    "is_repeat_city",
    "is_repeat_org",
    "first_year_in_city",
    "org_event_seq",
    "same_name_city_seq",
    "name_is_year",
]

SCALE_ORDER = ["cosy", "small", "medium", "large", "xlarge", "mega"]


def main() -> int:
    if not SRC.exists():
        print(f"[FAIL] 缺少 {SRC}，请先运行 scripts/02_snapshot.py", file=sys.stderr)
        return 2

    with SRC.open("r", encoding="utf-8-sig", newline="") as f:
        raw = list(csv.DictReader(f))

    log: list[str] = []

    def say(s: str = "") -> None:
        log.append(s)

    say("清洗报告")
    say("=" * 64)
    say(f"输入  : {SRC.name}  {len(raw)} 行 × {len(raw[0])} 列")
    say(f"输出  : {OUT.name}  见下方列清单")
    say("")

    # ---------- 1. 排序：所有派生列都依赖这个顺序 ----------
    raw.sort(key=lambda r: (r["start_date"], r["end_date"], r["eventKey"]))
    say("[规则 1] 排序：start_date → end_date → event_key 升序。")
    say("         派生列（第 N 次、是否重复）以此顺序为准；换顺序结果会变。")
    say("")

    # ---------- 2. 逐行改写 ----------
    rows: list[dict] = []
    stat = {
        "venue_type_from_location": 0,
        "venue_type_from_place_kind": 0,
        "venue_type_missing": 0,
        "region_tw": 0,
        "region_hk": 0,
        "region_mainland": 0,
        "days_off_by_one": 0,
        "days_negative": 0,
        "days_zero": 0,
        "days_gt_14": 0,
        "name_is_year": 0,
        "type_missing": 0,
    }

    for r in raw:
        lt = (r.get("locationType") or "").strip()
        pk = (r.get("place_kind") or "").strip()
        if lt:
            venue_type = lt
            stat["venue_type_from_location"] += 1
        elif pk:
            venue_type = pk
            stat["venue_type_from_place_kind"] += 1
        else:
            venue_type = ""
            stat["venue_type_missing"] += 1

        mr = (r.get("macro_region") or "").strip()
        if mr == "台湾":
            region = "台湾"
            stat["region_tw"] += 1
        elif mr == "港澳":
            region = "香港"
            stat["region_hk"] += 1
        else:
            region = "中国大陆"
            stat["region_mainland"] += 1

        days_calc, flag = _days(r.get("start_date", ""), r.get("end_date", ""))
        published = (r.get("days") or "").strip()
        if days_calc is not None and published and _int(published) != days_calc:
            stat["days_off_by_one"] += 1
        if flag == "negative":
            stat["days_negative"] += 1
        elif flag == "single":
            stat["days_zero"] += 1
        elif flag == "gt14":
            stat["days_gt_14"] += 1

        name = (r.get("name") or "").strip()
        is_year_name = name.isdigit() and len(name) == 4
        if is_year_name:
            stat["name_is_year"] += 1
        if not (r.get("type") or "").strip():
            stat["type_missing"] += 1

        rows.append(
            {
                "event_key": r["eventKey"],
                "source_id": r["id"],
                "name": name,
                "start_date": r["start_date"],
                "end_date": r["end_date"],
                "year": r["year"],
                "weekday_start": r["weekday_start"],
                "days": "" if days_calc is None else str(days_calc),
                "days_published": r["days"],
                "scale": r["scale"],
                "type": r["type"],
                "venue_type": venue_type,
                "status": r["status"],
                "city": r["city"],
                "city_slug": r["city_slug"],
                "region": region,
                "macro_region": mr,
                "venue_name": r.get("place_name", ""),
                "lat": r["lat"],
                "lng": r["lng"],
                "org_slug": r["org_slug"],
                "org_name": r["org_name"],
                "organizer_count": r["organizer_count"],
                "info_source": r.get("source_names", ""),
                "url": r["url"],
            }
        )

    say("[规则 2] venue_type = locationType，缺失时取 place_kind。")
    say(f"         取自 locationType {stat['venue_type_from_location']} 行；"
        f"取自 place_kind {stat['venue_type_from_place_kind']} 行；"
        f"两列皆空 {stat['venue_type_missing']} 行。")
    say("")
    say("[规则 3] region 由源站 macro_region 映射：台湾→台湾，港澳→香港，其余→中国大陆。")
    say(f"         中国大陆 {stat['region_mainland']} / 台湾 {stat['region_tw']} / 香港 {stat['region_hk']}。")
    say("         说明：源站 country 列把台湾与大陆并列为国家值，本数据集不沿用该列。")
    say("         宜兰、南投两条在源站 country=中国 而 macro_region=台湾，按 macro_region 归入台湾。")
    say("")
    say("[规则 4] days 由起止日期重算：(end_date - start_date).days + 1，含首尾。")
    say(f"         重算值与源站 days 列不一致 {stat['days_off_by_one']} 行，以重算值为准，")
    say(f"         源站原值保留在 days_published 列。负值 {stat['days_negative']} 行、")
    say(f"         单日展会 {stat['days_zero']} 行、超过 14 天 {stat['days_gt_14']} 行——见 known_issues。")

    # ---------- 3. 派生列 ----------
    seen_city: dict[str, int] = {}
    seen_org: dict[str, int] = {}
    first_year: dict[str, str] = {}
    seen_name_city: dict[tuple[str, str], int] = {}

    for r in rows:
        c = r["city"]
        o = r["org_slug"]
        nc = (r["name"], c)

        r["is_repeat_city"] = "0" if c not in seen_city else "1"
        r["is_repeat_org"] = "0" if o not in seen_org else "1"

        if c not in first_year:
            first_year[c] = r["year"]
        r["first_year_in_city"] = first_year[c]

        seen_city[c] = seen_city.get(c, 0) + 1
        seen_org[o] = seen_org.get(o, 0) + 1
        seen_name_city[nc] = seen_name_city.get(nc, 0) + 1

        r["org_event_seq"] = str(seen_org[o])
        r["same_name_city_seq"] = str(seen_name_city[nc])
        r["name_is_year"] = "1" if r["name"].isdigit() and len(r["name"]) == 4 else "0"

    say("")
    say("[派生列] 全部按上面的排序顺序累加，不是源站字段：")
    say("  is_repeat_city     该城市在本数据集中此前是否已出现过一次展会")
    say("  is_repeat_org      该主办方（org_slug）此前是否已出现过一次")
    say("  first_year_in_city 该城市在本数据集中的首个展会年份")
    say("  org_event_seq      该主办方在本数据集中的第几场（从 1 起）")
    say("  same_name_city_seq 同名同城在本数据集中的第几场（从 1 起）")
    say("  name_is_year       名称就是一个四位年份（源站如此，非抓取损坏）")
    say("")
    say(f"[规则 5] info_source 直接沿用源站 source_names（信息出处：WikiFur / QQ空间 / 官方微博等），")
    say("         缺失率较高，仅作溯引用途。")
    say("")
    say(f"[规则 6] type 缺失 {stat['type_missing']} 行（{stat['type_missing']/len(rows)*100:.1f}%），留空不推断。")
    say("")
    say(f"[规则 7] name_is_year 命中 {stat['name_is_year']} 行：源站该条目的名称就是一个年份，")
    say("         本数据集不替它编名字，仅打标记。")
    say("")

    # ---------- 4. 完整性自检 ----------
    say("=" * 64)
    say("自检")
    say("-" * 64)
    keys = [r["event_key"] for r in rows]
    ids = [r["source_id"] for r in rows]
    say(f"行数                     : {len(rows)}")
    say(f"source_id 唯一            : {len(set(ids))}")
    say(f"event_key 唯一            : {len(set(keys))}  ← 不唯一，见 known_issues（源站 slug 复用）")
    dup = len(rows) - len(set(i for i in ids))
    if dup:
        say(f"[FAIL] source_id 出现 {dup} 个重复，数据集主键不成立")
        return 1
    bad_date = [r for r in rows if not _is_date(r["start_date"])]
    if bad_date:
        say(f"[FAIL] {len(bad_date)} 行 start_date 非法")
        return 1
    say(f"start_date 全部可解析      : 是")
    say(f"年份范围                 : {min(r['year'] for r in rows)} – {max(r['year'] for r in rows)}")
    say(f"城市数                   : {len({r['city'] for r in rows})}")
    say(f"主办方数                 : {len({r['org_slug'] for r in rows})}")
    say("")

    DATA.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in OUT_COLUMNS})

    text = "\n".join(log) + "\n"
    REPORT.write_text(text, encoding="utf-8")
    print(text)
    print(f"[OK] {OUT}  {len(rows)} 行 × {len(OUT_COLUMNS)} 列")
    print(f"[OK] {REPORT}")
    return 0


def _days(sd: str, ed: str) -> tuple[int | None, str]:
    """返回 (含首尾天数, 异常标记)。异常标记只为统计用。"""
    if not sd or not ed:
        return None, ""
    d0 = date.fromisoformat(sd)
    d1 = date.fromisoformat(ed)
    n = (d1 - d0).days + 1
    if n < 1:
        return n, "negative"
    if n == 1:
        return n, "single"
    if n > 14:
        return n, "gt14"
    return n, ""


def _int(s: str) -> int | None:
    try:
        return int(float(s))
    except Exception:
        return None


def _is_date(s: str) -> bool:
    try:
        date.fromisoformat(s)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    raise SystemExit(main())
