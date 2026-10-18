# -*- coding: utf-8 -*-
"""
FEC 兽展日历（https://www.furrycons.cn/）全量抓取器
=====================================================
圈层观察员 ｜ 2026-10-17 建

站点是 Next.js：所有数据在每页的 <script id="__NEXT_DATA__" type="application/json"> 里。
三个列表页 + 511 个详情页即可覆盖全库。

用法（在仓库根目录或任意目录均可）：
    python scripts/00_scrape.py                # 全量（列表 + 全部详情页）
    python scripts/00_scrape.py --lists-only   # 只抓列表页
    python scripts/00_scrape.py                # 详情页已存在则复用缓存（增量）
    python scripts/00_scrape.py --refresh      # 忽略缓存，全部详情页重抓

产出（相对仓库根目录）：
    raw/{years,city,organization}.json   三个列表页原始 pageProps
    raw/events/<eventKey>.json            每个展会详情页原始 event 对象
    data/fec_events.json                  汇总（全量，扁平）
    data/fec_events.csv                   汇总（表格，供 Excel/pandas）← 本数据集里叫 fec_raw.csv
    data/fec_orgs.json                    展商
    data/fec_regions.json                 城市分组
    data/runs.jsonl                       每次运行的审计记录
    data/changes_<时间戳>.json            每次运行的增删改日志（02_snapshot.py 依赖它）

注意：重跑本脚本会刷新上述文件，但不会覆盖 data/fec_events_clean.csv 等发布物。
"""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

BASE = "https://www.furrycons.cn"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)                 # 仓库根目录
RAW = os.path.join(ROOT, "raw")
RAW_EV = os.path.join(RAW, "events")
DATA = os.path.join(ROOT, "data")
CST = timezone(timedelta(hours=8))

for d in (RAW, RAW_EV, DATA):
    os.makedirs(d, exist_ok=True)


# ---------------------------------------------------------------- fetch
def fetch(url, tries=3, timeout=45):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:          # noqa: BLE001
            last = e
            time.sleep(1.2 * (i + 1))
    raise last


def nextdata(html):
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                  html, re.S)
    if not m:
        raise ValueError("__NEXT_DATA__ not found")
    return json.loads(m.group(1))


def page_props(path):
    j = nextdata(fetch(BASE + path))
    return j["props"]["pageProps"], hashlib.sha256(
        json.dumps(j, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def to_cst(iso):
    """站点存 UTC；'2027-08-26T16:00:00.000Z' 其实是北京时间 8/27 00:00。"""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone(CST)


# ---------------------------------------------------------------- flatten
def flat_event(ev, detail=None):
    d = detail or {}
    st = to_cst(ev.get("startAt"))
    en = to_cst(ev.get("endAt"))
    place = d.get("place") or {}
    region = d.get("region") or ev.get("region") or {}
    org = ev.get("organization") or {}
    organizers = d.get("organizers") or []
    primary = next((o for o in organizers if o.get("isPrimary")), None)
    if primary is None and organizers:
        primary = organizers[0]
    return {
        "eventKey": d.get("eventKey") or ev.get("slug"),
        "id": ev.get("id") or d.get("id"),
        "slug": ev.get("slug") or d.get("slug"),
        "name": (ev.get("name") or d.get("name") or "").strip(),
        "start_date": st.strftime("%Y-%m-%d") if st else "",
        "end_date": en.strftime("%Y-%m-%d") if en else "",
        "year": st.strftime("%Y") if st else "",
        "weekday_start": "一二三四五六日"[st.weekday()] if st else "",
        "days": (en - st).days + 1 if (st and en) else "",
        "scale": ev.get("scale") or d.get("scale") or "",
        "type": d.get("type") or "",
        "locationType": d.get("locationType") or "",
        "status": d.get("status") or "",
        "city": region.get("localName") or "",
        "city_slug": region.get("slug") or "",
        "country": CITY2COUNTRY.get(region.get("localName") or "", ""),
        "macro_region": ("台湾" if (region.get("localName") in TW_CITIES)
                         else "港澳" if any(k in (region.get("localName") or "") for k in ("香港", "澳门"))
                         else MACRO.get(region.get("localName") or "", "其他")),
        "place_name": place.get("name") or "",
        "place_kind": place.get("kind") or "",
        "address": place.get("address") or "",
        "lat": place.get("latitude") or "",
        "lng": place.get("longitude") or "",
        "org_slug": (primary or {}).get("organization", {}).get("slug") or org.get("slug") or "",
        "org_name": (primary or {}).get("organization", {}).get("name") or org.get("name") or "",
        "organizer_count": len(organizers),
        "pageviews": d.get("pageviewCount", ""),
        "fetched": 1 if detail else 0,
        "has_desc": 1 if d.get("detail") else 0,
        "detail_len": len(d.get("detail") or ""),
        "source_count": len(d.get("sources") or []),
        "source_names": "|".join(sorted({(s.get("name") or "") for s in (d.get("sources") or []) if s})),
        "ticket_channel_count": len(d.get("ticketChannels") or []),
        "image_count": len((d.get("media") or {}).get("images") or []),
        "thumbnail": d.get("thumbnail") or "",
        "url": f"{BASE}/{(primary or {}).get('organization', {}).get('slug') or org.get('slug') or ''}/{ev.get('slug') or d.get('slug')}",
    }


CITY2COUNTRY = {}   # 由 /city 的 regionGroups 填充：城市 localName -> 上级（国家）

# 研究者补录的大区划分。FEC 的城市层级只有「城市 → 国家」，没有省级，
# 所以「珠三角 / 长三角 / 京津冀 / 成渝」这四个论文要用的大区由本脚本手工归类。
# 未列出的城市归「其他」；台湾、港澳单列。
MACRO = {}
for _c in ("广州", "深圳", "佛山", "东莞", "珠海", "中山", "惠州", "江门", "肇庆"):
    MACRO[_c] = "珠三角"
for _c in ("上海", "杭州", "南京", "苏州", "宁波", "无锡", "常州", "南通", "嘉兴",
           "湖州", "绍兴", "金华", "台州", "温州", "合肥", "徐州", "淮安", "义乌"):
    MACRO[_c] = "长三角"
for _c in ("北京", "天津", "石家庄", "保定", "唐山", "廊坊"):
    MACRO[_c] = "京津冀"
for _c in ("成都", "重庆", "绵阳", "自贡", "泸州", "宜宾"):
    MACRO[_c] = "成渝"
TW_CITIES = {"台北", "新北", "台中", "台南", "高雄", "桃园", "桃園", "新竹", "苗栗",
             "彰化", "嘉义", "宜兰", "花莲", "南投", "屏东", "南港", "板桥", "基隆"}

CSV_COLS = ["eventKey", "id", "slug", "name", "start_date", "end_date", "year", "weekday_start",
            "days", "scale", "type", "locationType", "status", "city", "city_slug", "country", "macro_region",
            "place_name", "place_kind", "address", "lat", "lng", "org_slug", "org_name",
            "organizer_count", "pageviews", "fetched", "has_desc", "detail_len", "source_count",
            "source_names", "ticket_channel_count", "image_count", "url"]


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lists-only", action="store_true")
    ap.add_argument("--refresh", action="store_true", help="忽略缓存，全部详情页重抓")
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    t_start = time.time()
    run = {"started_at": datetime.now(CST).isoformat(timespec="seconds"),
           "mode": "refresh" if args.refresh else ("lists-only" if args.lists_only else "incremental")}

    # --- 三个列表页 ---
    lists = {}
    for path, fname, key in [("/years", "years.json", "events"),
                             ("/city", "city.json", "regionGroups"),
                             ("/organization", "organization.json", "organizations")]:
        pp, h = page_props(path)
        lists[key] = pp[key]
        with open(os.path.join(RAW, fname), "w", encoding="utf-8") as f:
            json.dump(pp, f, ensure_ascii=False, indent=1)
        print(f"[list] {path}: {len(pp[key])} 条  ({h})")

    events = lists["events"]
    for _grp in (lists["regionGroups"] or {}).values():
        for _r in _grp:
            _par = ((_r.get("parent") or {}).get("localName")
                            or (_r.get("parent") or {}).get("name"))
            if _r.get("localName") and _par:
                CITY2COUNTRY[_r["localName"]] = _par
    with open(os.path.join(DATA, "fec_orgs.json"), "w", encoding="utf-8") as f:
        json.dump(lists["organizations"], f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "fec_regions.json"), "w", encoding="utf-8") as f:
        json.dump(lists["regionGroups"], f, ensure_ascii=False, indent=1)

    # --- 详情页 ---
    # 注意：event.slug 全站不唯一（同一「日期+城市」可有多家主办各办一场，最多 5 条同 slug），
    # 唯一键是 (organization.slug, event.slug) —— 详情页 URL 正是 /<org>/<slug>。
    #
    # 增量策略（定期抓取用，默认开启）：
    #   · 本地无缓存        → 新展会，抓
    #   · 开展日在 [今-30d, 今+90d] → 状态可能仍在变（改期/取消/加票），强制刷新
    #   · 其余              → 用缓存
    # --refresh 关闭增量，全量重抓；--lists-only 只抓列表页。
    details = {}
    failures = []
    if not args.lists_only:
        now = datetime.now(CST)

        def need_refresh(ev, path):
            if args.refresh or not os.path.exists(path):
                return True
            st = to_cst(ev.get("startAt"))
            if st is None:
                return False
            return timedelta(days=-30) <= (st - now) <= timedelta(days=90)

        def one(ev):
            org = (ev.get("organization") or {}).get("slug") or ""
            key = f"{org}/{ev.get('slug')}"
            url = f"{BASE}/{key}"
            path = os.path.join(RAW_EV, f"{org}__{ev.get('slug')}.json")
            if not need_refresh(ev, path):
                with open(path, encoding="utf-8") as f:
                    return key, json.load(f), None
            try:
                pp, _ = page_props(f"/{key}")
                evt = pp.get("event") or {}
                evt["_pageviewCount"] = pp.get("pageviewCount")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(evt, f, ensure_ascii=False, indent=1)
                return key, evt, None
            except Exception as e:      # noqa: BLE001
                msg = f"{type(e).__name__}: {e}"
                print(f"[warn] {url}: {msg}", file=sys.stderr)
                if os.path.exists(path):        # 抓失败但有旧缓存 → 用旧的，不记失败
                    with open(path, encoding="utf-8") as f:
                        return key, json.load(f), None
                return key, None, {"key": key, "url": url, "error": msg}

        done = 0
        with ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(one, ev): ev for ev in events}
            for fut in as_completed(futs):
                key, evt, fail = fut.result()
                if evt:
                    details[key] = evt
                if fail:
                    failures.append(fail)
                done += 1
                if done % 50 == 0:
                    print(f"[detail] {done}/{len(events)}  {time.time() - t_start:.0f}s")
        print(f"[detail] 完成 {len(details)}/{len(events)}，失败 {len(failures)}")
        with open(os.path.join(DATA, "fetch_failures.json"), "w", encoding="utf-8") as f:
            json.dump(failures, f, ensure_ascii=False, indent=1)

    # --- 汇总 ---
    rows = []
    for ev in events:
        _org = (ev.get("organization") or {}).get("slug") or ""
        det = details.get(f"{_org}/{ev.get('slug')}")
        if det is not None:
            det = dict(det)
            det["pageviewCount"] = det.get("_pageviewCount")
        rows.append(flat_event(ev, det))

    rows.sort(key=lambda r: (r["start_date"], r["name"]))

    # --- 与上一次快照比对（定期抓取的价值就在这里：知道变了什么）---
    prev_path = os.path.join(DATA, "fec_events.json")
    prev = {}
    if os.path.exists(prev_path):
        try:
            with open(prev_path, encoding="utf-8") as f:
                prev = {r["eventKey"]: r for r in json.load(f)}
        except Exception:               # noqa: BLE001
            prev = {}
    cur = {r["eventKey"]: r for r in rows}
    diff = {
        "at": datetime.now(CST).isoformat(timespec="seconds"),
        "added": [cur[k] for k in cur.keys() - prev.keys()],
        "removed": [prev[k] for k in prev.keys() - cur.keys()],
        "changed": [],
    }
    WATCH = ("name", "start_date", "end_date", "status", "scale", "city", "place_name", "address")
    if prev:
        for k in cur.keys() & prev.keys():
            ch = {f: [prev[k].get(f), cur[k].get(f)] for f in WATCH
                  if prev[k].get(f) != cur[k].get(f)}
            if ch:
                diff["changed"].append({"eventKey": k, "name": cur[k]["name"], "fields": ch})

    with open(os.path.join(DATA, "fec_events.json"), "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=1)
    with open(os.path.join(DATA, "fec_events.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_COLS})
    with open(os.path.join(DATA, f'changes_{datetime.now(CST):%Y%m%d_%H%M%S}.json'),
              "w", encoding="utf-8") as f:
        json.dump(diff, f, ensure_ascii=False, indent=1)

    run.update({
        "events": len(rows),
        "details": len(details),
        "orgs": len(lists["organizations"]),
        "cities": len({r["city"] for r in rows if r["city"]}),
        "new": len(diff["added"]),
        "gone": len(diff["removed"]),
        "mutated": len(diff["changed"]),
        "elapsed_s": round(time.time() - t_start, 1),
        "finished_at": datetime.now(CST).isoformat(timespec="seconds"),
    })
    with open(os.path.join(DATA, "runs.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(run, ensure_ascii=False) + "\n")

    print(f"\n=== {run['events']} 场 / {run['orgs']} 展商 / {run['cities']} 城市 / "
          f"{run['elapsed_s']}s → {DATA}")
    if prev:
        print(f"    变更：新增 {run['new']}｜消失 {run['gone']}｜字段变化 {run['mutated']}")
        for a in diff["added"][:10]:
            print(f"      + {a['start_date']} {a['name']} ({a['city']})")
        for c in diff["changed"][:10]:
            print(f"      ~ {c['name']}: {c['fields']}")


if __name__ == "__main__":
    main()
