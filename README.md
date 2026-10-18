# Chinese Furry Convention Dataset, 2015–2027

A census of **511 furry-fandom events** held in mainland China, Hong Kong and
Taiwan between 2015 and 2027 — dates, cities, venues, organisers, size tiers —
as a snapshot taken on **2026-10-17**.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23448131.svg)](https://doi.org/10.5281/zenodo.23448131)

> Two DOIs, two jobs. The badge points at the **concept DOI**
> [`10.5281/zenodo.23448131`](https://doi.org/10.5281/zenodo.23448131), which
> always resolves to the newest version — cite that when you want "this dataset".
> The BibTeX entry below pins the **version DOI**
> [`10.5281/zenodo.23448132`](https://doi.org/10.5281/zenodo.23448132) — cite that
> when you need exactly the bytes analysed in a paper.

---

## What this is

- **511 rows × 31 columns**, one row per event.
- **Coverage**: 2015–2027, **81 cities**, **172 organising groups**.
- **Regions**: mainland China 443 (86.7%) · Taiwan 65 (12.7%) · Hong Kong 3 (0.6%).
- **Languages**: all string fields are in the original Chinese. Column names are
  English; `docs/codebook.md` defines every one.
- **Formats**: `data/fec_events_clean.csv` (UTF-8 with BOM — opens directly in
  Excel), `data/fec_events_clean.json` (real JSON types, not all-strings).

What it is **not**: it contains no attendance figures. `scale` is the source's
own size *estimate*, not a head count. See *Known limitations*.

Row counts by year:

| 2015 | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | 2027 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 3 | 3 | 8 | 10 | 12 | 16 | 16 | 15 | 56 | 94 | 127 | 132 | 19 |

The 2027 rows are announced dates, not events that have happened.

---

## Where it comes from

**Primary and only source**: [FEC 兽展日历](https://www.furrycons.cn/), a
community-maintained calendar of Chinese-language furry events. The scraper in
`scripts/00_scrape.py` reads the site's Next.js payloads — three list endpoints
(`/years`, `/city`, `/organization`) plus one detail page per event.

Everything in this release is the source's data, with the exception of
**8 records restored from the source's own change log** (the site removed them
between 2026-10-17 and 2026-10-18; see `docs/methodology.md` step 2). No value
was inferred, imputed or geocoded by this project.

The source is **not** affiliated with this release. It was not asked for
permission because it publishes these listings openly; if its maintainers object,
this dataset will be withdrawn.

---

## How it was collected

```
00_scrape.py  →  data/fec_raw.csv                  (live export, 2026-10-18, 503 rows)
01_profile.py →  docs/field_report.txt             (census of the raw file)
02_snapshot.py→  data/fec_snapshot_20261017.csv    (511 rows: 8 removed records restored)
03_clean.py   →  data/fec_events_clean.csv         (511 rows × 31 cols — the released file)
04_summary.py →  docs/summary.txt                  (descriptive tables)
05_fieldstats.py → docs/field_stats.txt            (per-field missing rates)
06_export.py  →  data/fec_events_clean.json        (typed JSON)
```

All six scripts resolve their paths from `__file__`, so they can be run from any
working directory; each reads files already on disk and makes no network
request. `00_scrape.py` is the exception — it is the only script that touches the
network, and it is included for provenance rather than for re-running.

The pipeline is byte-reproducible: running 01→06 on a clean copy produces the
same SHA-256 for every output. Full rationale for every cleaning rule, and for
the four dropped columns, is in [`docs/methodology.md`](docs/methodology.md).

---

## Known limitations

1. **One source, no cross-validation.** No second Chinese-language convention
   calendar exists to check these 511 rows against. Coverage of the smallest
   events — the `cosy` tier (0–100 people) holds 236 of 511 rows — is plausibly
   incomplete, since small meetups are the least likely to be listed anywhere.

2. **`scale` is an estimate, not a measurement.** The source labels it
   `预估这是一个 … 的兽展`. No column records actual attendance. The upper two
   tier definitions overlap in the source itself (`xxlarge` = 5000+, `mega` =
   10000+); this is reproduced unaltered.

3. **The release is partly a reconstruction.** The source deletes entries. The
   live export held 503 rows on 2026-10-18 versus 511 on 2026-10-17; the missing
   8 are restored from the source's change log. Re-scraping later will give a
   different row count.

4. **`type` is missing in 33.7% of rows** and `info_source` in 66.1%. Both were
   left blank rather than inferred.

5. **Attendance reporting is absent at the level of the whole fandom, not just
   this dataset.** WikiFur's global
   [list of furry conventions by attendance](https://en.wikifur.com/wiki/List_of_in-person_furry_conventions_by_attendance)
   contains **zero mainland Chinese entries** — an absence of public attendance
   reporting, not an absence of events. Do not read a join between the two
   sources as a coverage measure.

6. **Political geography.** The source's `country` column treats Taiwan as a peer
   of China. This dataset does not reproduce that column; `region` is derived
   from the source's own seven-way `macro_region` instead, yielding mainland
   China / Taiwan / Hong Kong as three separate values. The derivation is stated
   explicitly in `docs/methodology.md` rule 3 and in
   [`docs/known_issues.md`](docs/known_issues.md) §2, along with the two records
   it reclassifies.

More: [`docs/known_issues.md`](docs/known_issues.md) lists eleven further
defects — non-unique `event_key`, a negative `days` value, eleven events named
after a bare year, missing coordinates, and others — all preserved rather than
silently corrected.

---

## Citation

```bibtex
@dataset{quanlayer2026fec,
  author    = {圈层观察员},
  title     = {Chinese Furry Convention Dataset, 2015--2027},
  year      = {2026},
  publisher = {Zenodo},
  version   = {1.0.0},
  doi       = {10.5281/zenodo.23448132}
}
```

The BibTeX above pins the **version DOI**
([`10.5281/zenodo.23448132`](https://doi.org/10.5281/zenodo.23448132)) — that is
the right choice when you need exactly the bytes a paper analysed. To cite "this
dataset, whatever the latest release is", use the concept DOI
[`10.5281/zenodo.23448131`](https://doi.org/10.5281/zenodo.23448131) instead.

A [`CITATION.cff`](CITATION.cff) is included for GitHub's "Cite this repository"
button. If you use this dataset, please also cite the source calendar
(furrycons.cn) as the origin of the records.

---

## License

- **Data** (`data/`, `docs/`): [CC BY 4.0](LICENSE) — use it, remix it, sell it,
  just say where it came from.
- **Code** (`scripts/`): MIT.

The licence covers this compilation and its derived columns. The underlying
event facts originate with FEC 兽展日历 and its contributors.

---

## Files

| Path | What it is |
|---|---|
| `data/fec_events_clean.csv` | **The dataset.** 511 rows × 31 columns, UTF-8 BOM |
| `data/fec_events_clean.json` | Same data as typed JSON (511 objects) |
| `data/fec_raw.csv` | Live scraper export, 503 rows, unmodified — provenance only |
| `data/fec_snapshot_20261017.csv` | 511-row pre-cleaning state, source column names |
| `data/changes_20261018_120009.json` | The scraper's change log — source of the 8 restored records |
| `data/summary_counts.csv` | Every count cited above, machine-readable |
| `docs/codebook.md` | All 31 fields: type, definition, missing rate |
| `docs/methodology.md` | Every cleaning rule and why it exists |
| `docs/known_issues.md` | Twelve known defects, preserved not corrected |
| `docs/field_stats.txt` | Per-field census (the codebook's source) |
| `docs/summary.txt` | Descriptive tables (the counts above) |
| `docs/clean_report.txt` | Row-by-row effect of each cleaning rule |
| `docs/snapshot_diff.txt` | The 8 restored records |
| `docs/export_report.txt` | Type conversion, key uniqueness, date checks |
| `scripts/00_scrape.py` … `06_export.py` | The full pipeline, stdlib only |
| `scripts/make_manifest.py` | Regenerates `MANIFEST.txt` |
| `MANIFEST.txt` | Path, byte size and SHA-256 of every released file |
