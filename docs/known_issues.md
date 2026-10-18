# Known issues

Everything below is a defect this dataset carries **on purpose** or a defect it
could not fix. Where a value looks wrong, the source's value is preserved and
the reason is recorded here rather than silently corrected, so that any row can
still be joined back to the source page.

## 1. The source site deletes entries, so the release is a reconstruction

The scraper's live export on 2026-10-18 held **503** events. On 2026-10-17 it
held **511**. The site removed 8 entries in between:

| Removed event | City | Date |
|---|---|---|
| 福州踏岁长歌 | 福州 | 2026-12-31 |
| 台州第四届 | 台州 | 2027-02-11 |
| 昆明暖冬奇迹 | 昆明 | 2027-01-22 |
| 义乌山海赴约 | 义乌 | 2027-08-27 |
| 郑州2701 | 郑州 | 2027-01-22 |
| 长春2.0 | 长春 | 2026-01-23 |
| 广州星回启元 | 广州 | 2026-12-31 |
| 长春3.0 | 长春 | 2027-01-15 |

All 8 are restored in the released file (see `methodology.md` step 2) from the
scraper's own change log, which stores each removed record in full. Nothing was
invented; nothing was recomputed.

**Consequence for users:** the row count is not reproducible by re-scraping.
Re-running the scraper at any later date will yield a different number, and
future removals will not be recoverable unless the change log still holds them.

## 2. Country attribution: two records reclassified, three Hong Kong records kept separate

The source's `country` column has two values only — `中国` and `台湾`. It places
Taiwan and mainland China as peers, and it files Hong Kong under `中国`.

This dataset does not reproduce that column. `region` is derived from the
source's `macro_region` instead (`methodology.md`, rule 3), giving
**中国大陆 443 / 台湾 65 / 香港 3**.

Two records have `country = 中国` but `macro_region = 台湾`, and are assigned
`region = 台湾`:

| Event | Date | City | `country` | `macro_region` | `region` |
|---|---|---|---|---|---|
| 台湾金毛影展 | 2024-07-13 | 宜兰 | 中国 | 台湾 | 台湾 |
| 第一届 | 2026-03-28 | 南投 | 中国 | 台湾 | 台湾 |

A third record that is sometimes cited as a similar case is **not** one:
`毛爪2號` (2025-02-21, 南港) already carries `country = 台湾` in the source.

Three Hong Kong records (`香港獸×人外Only` 2023-11-26, `波西米亞度假風`
2025-11-30, `街頭生活` 2027-08-07) keep `region = 香港` and are **not** folded
into 中国大陆, because their `macro_region` is `港澳`. Users who need a
mainland-only subset should filter `region = '中国大陆'`, which excludes them;
users who need "mainland + HK + Macau" should filter `region != '台湾'`.

## 3. Hong Kong appears under its full administrative name

`city` is reproduced verbatim, so Hong Kong records read
`香港特别行政区` rather than `香港`. No alias merging was performed anywhere in
this dataset: 香港 / 香港特别行政区 are not normalised, and neither are variants
such as 台北 vs 臺北 if they occur. If you group by `city`, group by the exact
string, or normalise first.

## 4. `event_key` is not unique

511 rows hold only 499 distinct `event_key` values. Nine keys are shared by two
or three editions, because the source reuses one page (slug) for a series:

| `event_key` | Rows | Editions |
|---|---|---|
| `2024-dec-taibei-con-qircc9b` | 3 | 2017 / 2018 / 2019, each named after its year |
| `2024-dec-xinbei-con-t3npmgc` | 3 | 亞特蘭提斯 / 戲獸台灣（延期）/ 戲獸台灣 |
| `2024-dec-tainan-con-uvzg8bf` | 3 | 2024-09-14 / 2024-12-01 / 2024-12-26 |
| `2024-dec-gaoxiong-con-1fd5cm5` | 2 | 2018 / 偵探之宴（延期） |
| `2020-oct-tianjin-con-vqhuvom` | 2 | 十月小聚1 / 十月小聚2 |
| `2024-dec-xinbei-con-leme7vr` | 2 | Furrymosa5 / Furrymosa6 |
| `2024-dec-jinan-con-6v268lg` | 2 | V5.0 / V8.0 |
| `2025-oct-ningbo-con-6jk3dqu` | 2 | 听海沐阳 / 韩岭 |
| `2026-may-tianjin-con-m2xzth0` | 2 | 初夏·第一爪小聚 / 夏日民宿线下聚会 |

This is the source's page structure, not a scraping error. `url` is not unique
for the same reason. **Use `source_id` as the key** — it is unique across all
511 rows.

## 5. One record has `end_date` before `start_date`

`2026-apr-ningbo-con-419ld85` (生日小聚, 宁波): `start_date` 2026-04-30,
`end_date` 2026-04-19, `days` = **−10**. The source has the dates wrong. The
record is left exactly as published so that it remains joinable; clamping it
would hide a real defect in the upstream data.

## 6. Eleven names are bare years

Eleven rows have `name` equal to a four-digit year (`2015`, `2016`, …, `2025`).
This is the source's data-entry style for early editions of a recurring event,
not a scraping failure. Flagged by `name_is_year`.

## 7. `scale` is an estimate, and two tiers overlap

The source describes `scale` as `预估这是一个 … 的兽展` — an estimate, not a
measured attendance figure. No column in this dataset records how many people
actually attended.

The source's own tier definitions are inconsistent at the top end: `xxlarge`
is `5000以上` while `mega` is `10000以上`, so the two overlap. No row takes
`xxlarge`. The definitions are reproduced unaltered in `codebook.md`.

## 8. `type` is missing in a third of the rows

172 of 511 rows (33.7%) have no `type`. The field was left empty rather than
inferred from the event name. Users needing a complete type column should treat
the blank as its own category, not impute it.

## 9. `info_source` is sparse

338 of 511 rows (66.1%) have no `info_source`. It is a citation-tracing field
only and should not be used as a measure of documentation quality: the source
fills it inconsistently, not proportionally to how well an event is documented.

## 10. Coordinates are missing for a fifth of the rows

`lat` / `lng` are missing in 104 rows (20.4%), mostly for events whose venue is
a private booking with no published address. They were not geocoded from the
venue name — any such geocoding would be this dataset's inference, not the
source's data.

## 11. No second source exists, so nothing here is cross-validated

Every row except the 8 restored ones comes from a single community-maintained
calendar (FEC 兽展日历, furrycons.cn). No comparable Chinese-language convention
calendar exists to check it against. Coverage of small meetups in particular is
plausibly incomplete: the smallest tier (`cosy`, 0–100 people) holds 236 of 511
rows, and those are exactly the events least likely to be listed anywhere.

## 12. Attendance figures are not in this dataset

If you need attendance numbers, they are not here and cannot be derived from
here. A separate global series exists (WikiFur's
`List of in-person furry conventions by attendance`, CC BY-SA 3.0), but it
contains **zero mainland Chinese entries** — a fact worth knowing before you try
to join the two: the absence reflects an absence of public attendance reporting,
not an absence of events.
