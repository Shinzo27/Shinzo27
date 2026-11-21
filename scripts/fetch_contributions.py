#!/usr/bin/env python3
"""Scrape the public GitHub contribution calendar into data/contributions.json.

No token required: github.com/users/<user>/contributions is public HTML and
each calendar cell carries data-date + data-level, with a <tool-tip> sibling
holding the exact count ("3 contributions on May 4, 2026").
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from datetime import date, datetime

USER = os.environ.get("GH_USER", "Shinzo27")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "contributions.json")

CELL = re.compile(
    r'data-date="(?P<date>\d{4}-\d{2}-\d{2})"\s+id="(?P<id>contribution-day-component-[^"]+)"'
    r'[^>]*?data-level="(?P<level>\d)"'
)
TIP = re.compile(
    r'<tool-tip[^>]*\bfor="(?P<id>contribution-day-component-[^"]+)"[^>]*>(?P<text>[^<]*)</tool-tip>'
)
COUNT = re.compile(r"(?P<n>[\d,]+)\s+contribution")
NONE = re.compile(r"^No contributions", re.I)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; readme-cards)"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", "replace")


def scrape(html: str) -> dict:
    days: dict[str, int] = {}
    levels: dict[str, int] = {}
    by_id: dict[str, str] = {}
    for m in CELL.finditer(html):
        days.setdefault(m.group("date"), 0)
        levels[m.group("date")] = int(m.group("level"))
        by_id[m.group("id")] = m.group("date")

    for m in TIP.finditer(html):
        text = m.group("text").strip()
        day = by_id.get(m.group("id"))
        if not day:
            continue
        if NONE.search(text):
            days[day] = 0
        else:
            c = COUNT.search(text)
            if c:
                days[day] = int(c.group("n").replace(",", ""))

    total_match = re.search(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", html)
    if not total_match:
        total_match = re.search(r"([\d,]+)\s+contributions?\s+in\s+\d{4}", html)
    total = int(total_match.group(1).replace(",", "")) if total_match else sum(days.values())

    return {"days": days, "levels": levels, "total": total}


def streaks(days: dict[str, int]) -> dict:
    keys = sorted(days)
    best = cur = 0
    best_end = None
    run_start = None
    prev = None
    for k in keys:
        d = date.fromisoformat(k)
        if days[k] > 0:
            if prev is not None and (d - prev).days == 1:
                cur += 1
            else:
                cur = 1
                run_start = k
            if cur > best:
                best, best_end = cur, k
        else:
            cur = 0
        prev = d

    # A streak is alive if it reaches today *or* yesterday: an empty cell for
    # today (before you've committed) must not reset a run that just happened.
    today = date.today()
    keys_desc = sorted(days, reverse=True)
    if keys_desc:
        newest = date.fromisoformat(keys_desc[0])
        if (today - newest).days > 1:
            keys_desc = []  # stale calendar: no live run to report
        elif days[keys_desc[0]] == 0:
            keys_desc = keys_desc[1:]  # skip an empty today
    live = 0
    prev = None
    for k in keys_desc:
        if days[k] == 0:
            break
        d = date.fromisoformat(k)
        if prev is not None and (prev - d).days != 1:
            break
        live += 1
        prev = d

    active = sum(1 for v in days.values() if v)
    busiest = max(days.items(), key=lambda kv: (kv[1], kv[0])) if days else ("", 0)
    return {
        "current": live,
        "longest": best,
        "longest_end": best_end,
        "active_days": active,
        "busiest_day": busiest[0],
        "busiest_count": busiest[1],
        "window": [keys[0], keys[-1]] if keys else [],
    }


def months(days: dict[str, int]) -> list[dict]:
    buckets: dict[str, int] = {}
    for k, v in sorted(days.items()):
        buckets.setdefault(k[:7], 0)
        buckets[k[:7]] += v
    out = []
    for key, value in buckets.items():
        d = datetime.strptime(key + "-01", "%Y-%m-%d")
        out.append({"month": key, "label": d.strftime("%b"), "value": value})
    return out


def main() -> int:
    html = fetch(f"https://github.com/users/{USER}/contributions")
    data = scrape(html)
    if not data["days"]:
        print("no calendar cells found — GitHub markup changed?", file=sys.stderr)
        return 1
    data.update(streaks(data["days"]))
    data["months"] = months(data["days"])
    data["updated"] = datetime.now().astimezone().strftime("%Y-%m-%d")
    data["user"] = USER
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1, sort_keys=True)
    print(
        f"wrote {OUT}: {len(data['days'])} days, total {data['total']}, "
        f"streak {data['current']} (best {data['longest']}), "
        f"active {data['active_days']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
