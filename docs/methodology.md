# Methodology

How `data/fec_events_clean.csv` was produced, in the order the steps were run.
All scripts are in `scripts/` and use only the Python standard library
(`csv`, `json`, `re`, `datetime`, `pathlib`). No pandas, no network access at
runtime — every script reads files already on disk.

```
data/fec_raw.csv                     503 rows × 34 cols   (scraper export, 2026-10-18 12:00)
        │
        ├── 02_snapshot.py  ← ../data/changes_20261018_120009.json
        ▼
data/fec_snapshot_20261017.csv       511 rows × 34 cols   (state as of 2026-10-17)
        │
        ├── 03_clean.py
        ▼
data/fec_events_clean.csv            511 rows × 31 cols   ← the released file
        │
        ├── 04_summary.py   → docs/summary.txt, data/summary_counts.csv
        ├── 05_fieldstats.py → docs/field_stats.txt, docs/field_stats.csv
        └── 06_export.py    → data/fec_events_clean.json, docs/export_report.txt
```

`01_profile.py` runs on `fec_raw.csv` before anything else and writes
`docs/field_report.txt`; it is a census, not a transformation.

---

## Step 1 — Profile the raw export (`01_profile.py`)

Reads `data/fec_raw.csv` with a fallback chain of encodings
(`utf-8-sig` → `utf-8` → `gbk` → `gb18030`) and reports, for every column,
missing rate / distinct count / first non-empty sample.

Result: 503 rows × 34 columns, encoding `utf-8-sig`.

## Step 2 — Restore the 2026-10-17 snapshot (`02_snapshot.py`)

**Why this step exists.** The scraper's most recent export is a *live* export:
between 2026-10-17 and 2026-10-18 the source site removed 8 entries, so the
export holds 503 rows, not 511. The analysis this dataset accompanies was
performed on the 511-row state. Releasing 503 rows would make every table in
that analysis impossible to reproduce.

The scraper writes a change log on every run
(`../data/changes_20261018_120009.json`), and the log's `removed` array stores
each removed record in full (all 35 fields). Step 2 therefore **re-inserts the
8 removed records** and re-sorts the result by
`(start_date, end_date, eventKey)`.

Output: `data/fec_snapshot_20261017.csv`, 511 rows. The diff between the two
files is written to `docs/snapshot_diff.txt`.

This is restoration, not imputation — every restored value comes from the
source's own record of that entry, byte for byte.

## Step 3 — Clean (`03_clean.py`)

Seven rules, applied in this order. Rule 1 must come first because rules 5–7
produce cumulative counters that depend on row order.

**Rule 1 — sort.** By `(start_date, end_date, eventKey)`. All derived sequence
columns below assume this order; reordering the file by hand will invalidate
them.

**Rule 2 — merge venue type.** `venue_type` takes the source's `locationType`;
where that is blank it falls back to `place_kind`. The two columns are
complementary rather than overlapping (cross-tab in `docs/clean_report.txt`),
so the merge leaves 8 rows blank instead of 99. `locationType` alone is
missing 19.7% and `place_kind` alone 7.2%.

**Rule 3 — region.** `region` ∈ {`中国大陆`, `台湾`, `香港`} is mapped **from
`macro_region`**, not from the source's `country` column:

| `macro_region` | `region` |
|---|---|
| 台湾 | 台湾 |
| 港澳 | 香港 |
| 其他 / 长三角 / 珠三角 / 成渝 / 京津冀 | 中国大陆 |

**Why not `country`.** The source's `country` column has exactly two values,
`中国` and `台湾`, treating Taiwan as a peer of China. Reproducing that verbatim
would embed a political claim in a dataset that has no business making one. The
source's own seven-way `macro_region` provides a consistent alternative: two of
its values (`台湾`, `港澳`) are exactly the subdivisions that `country` conflates.

Consequence: two records whose `country` says `中国` but whose `macro_region`
says `台湾` (宜兰 2024-07-13, 南投 2026-03-28) are assigned `region = 台湾`.
That is the intended behaviour of this rule, and it is why the released file has
443 / 65 / 3 rather than 445 / 63 / 3.

**Rule 4 — recompute `days`.** `days = (end_date − start_date) + 1`, inclusive
of both endpoints. The source's own value is preserved as `days_published`.
They differ in 7 rows, where the source appears to count the interval rather
than the span. One record has a negative value (see `codebook.md`); it is left
as computed rather than clamped.

**Rule 5 — `info_source`.** Renamed from `source_names`. Unmodified.

**Rule 6 — `type`.** Missing in 172 rows (33.7%). Left empty. The source does
not fill it and this dataset does not guess: inferring `all-in-con` from the
event name would manufacture a distribution.

**Rule 7 — `name_is_year`.** Flags the 11 rows whose `name` is a bare four-digit
year. These are the source's own data-entry style, not a scraping artifact; the
flag exists so downstream users can exclude them.

**Dropped columns.** Four columns were dropped from the 34:

| Dropped | Reason |
|---|---|
| `address` | Byte-identical to `place_name` in all 503 rows of the raw export; carries no independent information. Renamed column `venue_name` keeps the value. |
| `country` | Superseded by `region` (rule 3). Kept out of the release so no user is tempted to aggregate on it by accident. |
| `place_name` | Renamed to `venue_name`. |
| `source_names` | Renamed to `info_source`. |

Remaining source-side bookkeeping columns (`fetched`, `has_desc`, `detail_len`,
`source_count`, `ticket_channel_count`, `image_count`, `pageviews`,
`organizer_count`) — of these, `organizer_count` was kept because it carries
analytical content; the rest were dropped as scraper bookkeeping with no
bearing on the events themselves.

## Step 4 — Descriptive summary (`04_summary.py`)

Writes `docs/summary.txt` (human-readable) and `data/summary_counts.csv`
(82 rows, machine-readable). Every count cited in `README.md` and
`codebook.md` traces to one of these two files.

## Step 5 — Per-field statistics (`05_fieldstats.py`)

Writes `docs/field_stats.txt` and `docs/field_stats.csv`: for each of the 31
columns, the missing count, missing rate, distinct count, a sample value, and
whether the column is **source-side** or **derived**.

This file is the sole source of the missing rates in `codebook.md`. No rate in
that document was typed by hand.

## Step 6 — Export (`06_export.py`)

Writes `data/fec_events_clean.json` (511 objects, `orient=records`,
`ensure_ascii=False`, indent 1) with real JSON types: `year`, `days`,
`organizer_count` and the six sequence/flag columns become integers; `lat` and
`lng` become floats; empty strings become `null`. `docs/export_report.txt`
records the type-conversion result, the uniqueness check on both candidate
keys, and every date/duration inconsistency found.

## Reproducibility

Every script resolves its paths from `Path(__file__).resolve().parent.parent`,
never from the current working directory, so the pipeline runs from anywhere.
`02_snapshot.py` looks for the change log at `data/changes_20261018_120009.json`
first and falls back to `../data/` only when running inside the scraper's own
working directory; the change log is shipped inside `data/` so that the
repository is self-contained.

Verified: a clean copy of `data/fec_raw.csv` + `data/changes_20261018_120009.json`
plus `scripts/01–06`, run from an unrelated working directory, reproduces
byte-identical outputs for `fec_snapshot_20261017.csv`, `fec_events_clean.csv`,
`fec_events_clean.json`, `summary_counts.csv` and `field_stats.csv`.

---

## Scope and limits of this methodology

- **One snapshot, not a time series.** 511 rows is the state of the calendar on
  2026-10-17. The source adds and removes entries continuously; the 8 removed
  records in step 2 are direct evidence of that. Anyone re-running the scraper
  later will get a different row count, and that is expected.
- **`scale` is an estimate, not a measurement.** The source labels it
  `预估这是一个 … 的兽展`. No column in this dataset records actual attendance.
- **Single source.** Everything except the 8 restored records comes from one
  community-maintained calendar. Cross-checking against a second calendar was
  not possible — no comparable Chinese-language calendar exists (see
  `known_issues.md`).
- **Reconstruction is bounded by the change log.** Step 2 can only restore
  entries that were removed *and* logged. An entry removed before logging
  began is not recoverable.
