#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""02_snapshot.py —— 把抓取器的最新导出还原为论文所用的那一版快照（511 条）。

背景
----
本数据集的采集源是 furrycons.cn 的展会日历，它会在两次抓取之间**删除**条目。
抓取器每天 12:00 跑一次增量，导出 data/fec_events.csv 只反映「最近一次」的状态：

    2026-10-17T20:52   511 events / 498 details / 178 orgs / 81 cities
    2026-10-18T12:00   503 events / 491 details / 178 orgs / 80 cities
                       new 0, gone 8, mutated 4

配套论文分析的是 2026-10-17 那一版（n=511）。为了让数据集与论文表格能够互相
复现，本脚本用增量日志 data/changes_20261018_120009.json 把 10-18 被删掉的
8 条记录补回来，得到 511 行的快照。

字段值的处理
------------
行集（哪些记录存在）= 2026-10-17 的状态。
字段值 = 截至 2026-10-18 的最后一次观测。10-18 有 4 处字段被站点修正，采用的是
修正后的值（例如名称由 "1.0" 改为 "拼兽聚"）。这两条规则都写在 known_issues.md。

用法
----
    python scripts/02_snapshot.py

输入  data/fec_raw.csv（= 抓取器最新导出，503 行）
      data/changes_20261018_120009.json（增量日志，含被删记录的完整字段；
      若本目录没有，则回退到上一级的 ../data/，即抓取器的工作目录）
输出  data/fec_snapshot_20261017.csv（511 行 × 34 列，未清洗）
      docs/snapshot_diff.txt（本次还原的差异清单）

零第三方依赖，只用标准库。
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent                      # dataset-v1/
DATA = ROOT / "data"
DOCS = ROOT / "docs"

RAW = DATA / "fec_raw.csv"
# 变更日志优先取本目录内的副本；数据集是自包含的，不应依赖外部路径。
CHANGES_LOCAL = DATA / "changes_20261018_120009.json"
# 兼容：在抓取器工作目录内直接运行时，日志在上一级的 data/ 下。
CHANGES_PARENT = ROOT.parent / "data" / "changes_20261018_120009.json"
CHANGES = CHANGES_LOCAL if CHANGES_LOCAL.exists() else CHANGES_PARENT
OUT = DATA / "fec_snapshot_20261017.csv"
REPORT = DOCS / "snapshot_diff.txt"

# 抓取器 CSV 的列顺序（34 列）。增量日志里的记录多一个 thumbnail，这里丢掉。
COLUMNS = [
    "eventKey", "id", "slug", "name", "start_date", "end_date", "year",
    "weekday_start", "days", "scale", "type", "locationType", "status",
    "city", "city_slug", "country", "macro_region", "place_name",
    "place_kind", "address", "lat", "lng", "org_slug", "org_name",
    "organizer_count", "pageviews", "fetched", "has_desc", "detail_len",
    "source_count", "source_names", "ticket_channel_count", "image_count",
    "url",
]


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    for p in (RAW, CHANGES):
        if not p.exists():
            print(f"[FAIL] 缺少输入文件：{p}", file=sys.stderr)
            return 2

    rows = read_csv(RAW)
    log = json.loads(CHANGES.read_text(encoding="utf-8"))

    have = {r["eventKey"] for r in rows}
    added: list[dict] = []
    for rec in log.get("removed", []):
        key = rec["eventKey"]
        if key in have:
            print(f"[SKIP] {key} 已存在于当前导出，不重复添加")
            continue
        row = {c: _cell(rec.get(c)) for c in COLUMNS}
        added.append(row)

    out = rows + added
    out.sort(key=lambda r: (r["start_date"], r["eventKey"]))

    DATA.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(out)

    lines = []
    lines.append("快照还原报告")
    lines.append("=" * 60)
    lines.append(f"生成时间        : {_now()}")
    lines.append(f"最新导出（10-18）: {len(rows)} 行")
    lines.append(f"补回被删记录     : {len(added)} 行")
    lines.append(f"快照合计（10-17）: {len(out)} 行")
    lines.append("")
    lines.append("被站点删除、本数据集予以保留的条目：")
    for r in added:
        lines.append(
            f"  {r['start_date']}  {r['city']:<4}  {r['name']}  "
            f"({r['scale']}, {r['status']})  key={r['eventKey']}"
        )
    lines.append("")
    lines.append("10-18 被站点修正的字段（本数据集采用修正后的值）：")
    for ch in log.get("changed", []):
        for field, (old, new) in ch.get("fields", {}).items():
            lines.append(
                f"  {ch['eventKey']}  {field}: {old!r} -> {new!r}"
            )
    lines.append("")
    lines.append("注意：源站点会删除条目。10-17 与 10-18 两次抓取相差 8 条，")
    lines.append("这不是抓取错误，而是站点侧的内容治理。复现论文表格请用本文件")
    lines.append("（511 行），复现「站点当前状态」请用 data/fec_raw.csv（503 行）。")
    text = "\n".join(lines) + "\n"
    REPORT.write_text(text, encoding="utf-8")
    print(text)
    print(f"[OK] 写出 {OUT}（{len(out)} 行）")
    print(f"[OK] 写出 {REPORT}")
    return 0


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "1" if v else "0"
    return str(v)


def _now() -> str:
    from datetime import datetime
    return datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")


if __name__ == "__main__":
    raise SystemExit(main())
