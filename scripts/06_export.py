# -*- coding: utf-8 -*-
"""
06_export.py — 导出 JSON 版本，并做发布前的一致性检查

输入 : data/fec_events_clean.csv
输出 : data/fec_events_clean.json
       docs/export_report.txt

零依赖（只用标准库），与 01–05 保持一致。
"""
import csv
import json
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "data" / "fec_events_clean.csv"
DST = SRC.with_suffix(".json")
REP = SRC.parent.parent / "docs" / "export_report.txt"

INT_FIELDS = {"year", "days", "days_published", "organizer_count",
              "is_repeat_city", "is_repeat_org", "first_year_in_city",
              "org_event_seq", "same_name_city_seq", "name_is_year"}
FLOAT_FIELDS = {"lat", "lng"}


def convert(row):
    out = {}
    for k, v in row.items():
        v = v.strip() if isinstance(v, str) else v
        if v == "" or v is None:
            out[k] = None
        elif k in INT_FIELDS:
            try:
                out[k] = int(v)
            except ValueError:
                out[k] = None
        elif k in FLOAT_FIELDS:
            try:
                out[k] = float(v)
            except ValueError:
                out[k] = None
        else:
            out[k] = v
    return out


def main():
    with open(SRC, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    records = [convert(r) for r in rows]

    with open(DST, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)

    lines = []
    lines.append("导出报告")
    lines.append("=" * 78)
    lines.append(f"CSV   : {len(rows)} 行 × {len(rows[0])} 列")
    lines.append(f"JSON  : {len(records)} 条（orient=records，逐条一个对象）")
    lines.append(f"编码  : CSV 为 UTF-8 with BOM（Excel 直接双击不乱码）；JSON 为 UTF-8 无 BOM")
    lines.append("")

    # 类型检查：INT/FLOAT 字段有无解析失败
    bad = []
    for i, (raw, rec) in enumerate(zip(rows, records)):
        for k in INT_FIELDS | FLOAT_FIELDS:
            if raw[k].strip() and rec[k] is None:
                bad.append((i + 2, k, raw[k]))
    lines.append("类型转换失败：" + ("无" if not bad else f"{len(bad)} 处"))
    for ln, k, v in bad:
        lines.append(f"  第 {ln} 行 {k} = {v!r}")
    lines.append("")

    # 主键检查
    ids = [r["source_id"] for r in records]
    keys = [r["event_key"] for r in records]
    lines.append(f"source_id 唯一值 : {len(set(ids))} / {len(ids)}"
                 + ("  ✓ 可作主键" if len(set(ids)) == len(ids) else "  ✗ 存在重复"))
    lines.append(f"event_key 唯一值 : {len(set(keys))} / {len(keys)}"
                 + ("（源站 slug 复用，不可作主键，已在 codebook 说明）"
                    if len(set(keys)) != len(keys) else ""))
    lines.append("")

    # 日期一致性
    from datetime import date
    d_err = []
    for rec in records:
        try:
            s = date.fromisoformat(rec["start_date"])
            e = date.fromisoformat(rec["end_date"])
        except (TypeError, ValueError):
            d_err.append((rec["event_key"], "日期无法解析"))
            continue
        if e < s:
            d_err.append((rec["event_key"], f"end_date 早于 start_date：{s} → {e}"))
        if rec["days"] != (e - s).days + 1:
            d_err.append((rec["event_key"], f"days 与日期不符：{rec['days']} vs {(e-s).days+1}"))
    lines.append("日期/天数一致性：" + ("全部通过" if not d_err else f"{len(d_err)} 处例外"))
    for k, m in d_err:
        lines.append(f"  {k} : {m}")
    lines.append("")

    # 空值分布
    lines.append("空值（null）字段排行：")
    nullc = {}
    for rec in records:
        for k, v in rec.items():
            if v is None:
                nullc[k] = nullc.get(k, 0) + 1
    for k, n in sorted(nullc.items(), key=lambda x: -x[1]):
        lines.append(f"  {k:24s}{n:5d}  {n/len(records):6.1%}")
    lines.append("")

    lines.append("列清单（31）：")
    for c in rows[0].keys():
        lines.append(f"  {c}")

    REP.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
