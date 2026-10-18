# Codebook — fec_events_clean.csv

511 rows × 31 columns. Encoding: UTF-8 with BOM (opens directly in Excel).
All missing rates below are produced by `scripts/05_fieldstats.py` and identical to
`docs/field_stats.csv`.

## Identity and dates

| Field | Type | Definition | Missing |
|---|---|---|---|
| `event_key` | string | Source-site event key, form `YYYY-mon-city-con-xxxxxxx`. **Not unique**: one page (slug) can carry several editions, so 511 rows hold 499 distinct values. Do not use as a primary key. | 0.0% |
| `source_id` | string | UUID from the source database. Unique across all 511 rows. **This is the primary key.** | 0.0% |
| `name` | string | Event name as published. 11 rows consist of a bare four-digit year (the source has them that way); flagged by `name_is_year`. | 0.0% |
| `start_date` | date | Start date, ISO 8601, **local date** (converted from the source's UTC timestamps). | 0.0% |
| `end_date` | date | End date, ISO 8601, local. Equal to `start_date` for one-day events. | 0.0% |
| `year` | int | Calendar year of `start_date`. Range 2015–2027. | 0.0% |
| `weekday_start` | enum | Day of week of `start_date`, one Chinese character (`一`…`日`). | 0.0% |
| `days` | int | Duration in days **inclusive of both endpoints** = `(end_date − start_date) + 1`. Derived; **use this column**. | 0.0% |
| `days_published` | int | Duration exactly as published by the source. Differs from `days` in 7 rows (the source appears to count days between, not days inclusive). Kept only for traceability. | 0.0% |

## Classification

| Field | Type | Definition | Missing |
|---|---|---|---|
| `scale` | enum | Size tier. **This is the source's own estimate, not a measured attendance figure** (the source's tooltip reads `预估这是一个 {{scale}} 的兽展`). Six values occur: `cosy` 236, `small` 106, `medium` 136, `large` 24, `xlarge` 4, `mega` 5. Tier boundaries in the table below. | 0.0% |
| `type` | enum | Event type. 5 values: `all-in-con` 215, `fandom-meetup` 81, `suit-only-con` 20, `travel-con` 13, `comic-market` 10. Empty in 172 rows — the source left it blank; **this dataset does not infer it**. | 33.7% |
| `venue_type` | enum | `hotel` 348 (68.1%) or `venue` 155. Merged from the source's `locationType`, falling back to `place_kind` when the former is blank (411 rows from `locationType`, 92 from `place_kind`, 8 blank in both). | 1.6% |
| `status` | enum | `scheduled` 459, `cancelled` 35, `rescheduled` 11, `postponed` 5. One row blank (the source never filled it). | 0.2% |

### `scale` tier boundaries (verbatim from the source's i18n bundle)

| Value | Source label | Rows |
|---|---|---|
| `cosy` | 迷你（0-100） | 236 |
| `small` | 小型（100-500） | 106 |
| `medium` | 中型（500-1000） | 136 |
| `large` | 大型（1000-3000） | 24 |
| `xlarge` | 特大型（3000-5000） | 4 |
| `xxlarge` | 超特大型（5000以上） | 0 |
| `mega` | 巨型（10000以上） | 5 |

`xxlarge` is defined by the source but no record takes that value. The `mega`
lower bound (10000) overlaps the `xxlarge` range (5000+), which is the source's
own inconsistency; it is reproduced here unaltered.

## Geography

| Field | Type | Definition | Missing |
|---|---|---|---|
| `city` | string | City name in Chinese, as published. 81 distinct values. **No alias merging was performed** — e.g. 香港特别行政区 appears in full. | 0.0% |
| `city_slug` | string | Pinyin slug for the city, matching the source's URL structure. | 0.2% |
| `region` | enum | Three values: `中国大陆` 443 (86.7%), `台湾` 65 (12.7%), `香港` 3 (0.6%). **Derived from `macro_region`, not from the source's `country` column** — see `known_issues.md`. | 0.0% |
| `macro_region` | enum | The source's own seven-way split: `其他` 158, `长三角` 104, `珠三角` 92, `台湾` 65, `成渝` 45, `京津冀` 44, `港澳` 3. Reproduced as published. | 0.0% |
| `venue_name` | string | Venue name (hotel or hall). Renamed from the source's `place_name`; the source's `address` column was a verbatim duplicate of it and was dropped. | 7.2% |
| `lat` | float | Latitude, WGS84. | 20.4% |
| `lng` | float | Longitude, WGS84. | 20.4% |

## Organiser

| Field | Type | Definition | Missing |
|---|---|---|---|
| `org_slug` | string | Organiser slug, stable identifier. 172 distinct values. | 0.0% |
| `org_name` | string | Organiser name as published. | 0.0% |
| `organizer_count` | int | Number of co-organisers listed for the event. Mostly 1. | 0.0% |

## Provenance

| Field | Type | Definition | Missing |
|---|---|---|---|
| `info_source` | string | Where the source says its information came from (WikiFur, QQ空间, Bilibili, …). 28 distinct values. High missing rate; for citation tracing only. | 66.1% |
| `url` | string | Source page URL. All 511 point at `www.furrycons.cn`. **Not unique** — one page can carry several editions, same as `event_key`. | 0.0% |

## Derived sequence flags

| Field | Type | Definition | Missing |
|---|---|---|---|
| `is_repeat_city` | 0/1 | Whether this city already had an earlier event in this dataset. **Depends on row order** — see `methodology.md`, cleaning rule 1. | 0.0% |
| `is_repeat_org` | 0/1 | Whether this organiser already had an earlier event in this dataset. | 0.0% |
| `first_year_in_city` | int | Year of this city's first event in this dataset | 0.0% |
| `org_event_seq` | int | Ordinal of this event within its organiser's events (from 1). Max 18. | 0.0% |
| `same_name_city_seq` | int | Ordinal of this name within this city (from 1). **Matching is by exact name string**, so it misses renamings — e.g. a Guangzhou event literally named `第一届` is flagged `2`. | 0.0% |
| `name_is_year` | 0/1 | Whether `name` is a bare four-digit year. 11 rows. | 0.0% |

## Known data anomalies (not corrected)

| `event_key` | Anomaly |
|---|---|
| `2026-apr-ningbo-con-419ld85` | `end_date` 2026-04-19 is **earlier** than `start_date` 2026-04-30; `days` = −10. The source data is wrong; it is reproduced unchanged so that the record stays joinable to the source. |
| `2024-dec-foshan-con-8bmwici` | `days` = 61 (2025-07-01 → 2025-08-30), status `cancelled`. Long-duration booking rather than a 61-day convention. |
| `2027-feb-taizhou-con` | The only row with both `city_slug` and `status` empty; also the only row whose city has no other event. |
| 8 rows | Removed from the source between 2026-10-17 and 2026-10-18, and restored here from the source's own change log so that this snapshot matches the count used in the accompanying paper. See `methodology.md`, step 2. |

Negative and zero day counts are left as published deliberately. Filter with
`status = 'scheduled' AND days > 0` if you need a clean working set.
