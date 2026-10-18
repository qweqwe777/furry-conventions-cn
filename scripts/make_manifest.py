# -*- coding: utf-8 -*-
"""生成 MANIFEST：发布物清单 + SHA-256。"""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP = {"MANIFEST.txt", ".git", ".gitattributes"}

rows = []
for p in sorted(ROOT.rglob("*")):
    if not p.is_file():
        continue
    rel = p.relative_to(ROOT).as_posix()
    if rel in SKIP or rel.startswith(".git/"):
        continue
    h = hashlib.sha256(p.read_bytes()).hexdigest()
    rows.append((rel, p.stat().st_size, h))

w_name = max(len(r[0]) for r in rows) + 2
lines = ["# MANIFEST — 发布物清单与校验和", "# 由 scripts/make_manifest.py 生成，请勿手改",
         f"# 文件数 {len(rows)}　合计 {sum(r[1] for r in rows):,} 字节", ""]
lines.append(f"{'path':<{w_name}}{'bytes':>10}  sha256")
lines.append("-" * (w_name + 10 + 2 + 64))
for rel, size, h in rows:
    lines.append(f"{rel:<{w_name}}{size:>10}  {h}")
(ROOT / "MANIFEST.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
print("\n".join(lines[:8]))
print(f"\n... 共 {len(rows)} 个文件")
