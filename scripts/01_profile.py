#!/usr/bin/env python3
"""Data profiling for fec_raw.csv — zero dependencies (stdlib only).

Writes docs/field_report.txt and prints a summary to stdout.

Usage:
    python scripts/01_profile.py
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "fec_raw.csv"
DOCS = ROOT / "docs"


def main() -> int:
    if not SRC.exists():
        print(f"ERROR: {SRC} not found", file=sys.stderr)
        return 1

    # 中文 CSV 编码不确定，按顺序试
    rows = None
    used_enc = None
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            with open(SRC, encoding=enc, newline="") as f:
                rows = list(csv.DictReader(f))
            used_enc = enc
            break
        except UnicodeDecodeError:
            continue
    if rows is None:
        print("ERROR: none of utf-8-sig/utf-8/gbk/gb18030 could decode the file", file=sys.stderr)
        return 1

    cols = list(rows[0].keys()) if rows else []
    n = len(rows)
    print(f"encoding: {used_enc}")
    print(f"rows: {n}")
    print(f"cols: {len(cols)}")
    print()

    report = []
    for c in cols:
        vals = [r.get(c) or "" for r in rows]
        nonempty = [v for v in vals if v.strip()]
        miss = 1 - len(nonempty) / n if n else 1.0
        uniq = len(set(nonempty))
        sample = nonempty[0][:40] if nonempty else ""
        report.append((c, miss, uniq, sample))

    report.sort(key=lambda x: x[1])

    print(f"{'field':24s}{'missing':>9s}{'unique':>8s}  sample")
    print("-" * 78)
    for c, miss, uniq, sample in report:
        print(f"{c:24s}{miss:8.1%}{uniq:9d}  {sample}")

    DOCS.mkdir(exist_ok=True)
    with open(DOCS / "field_report.txt", "w", encoding="utf-8") as f:
        f.write(f"encoding: {used_enc}\nrows: {n}  cols: {len(cols)}\n\n")
        for c, miss, uniq, sample in report:
            f.write(f"{c}\t{miss:.1%}\t{uniq}\t{sample}\n")

    print(f"\nwritten: {DOCS / 'field_report.txt'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
