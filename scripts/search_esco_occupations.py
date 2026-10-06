"""
Searches the full public ESCO API by label for areas the local subset maps
poorly (Painter, Beauty worker, Delivery/courier, General construction, Driver)
and flags whether each candidate occupation is already in the subset.

Read-only: the subset in data/raw/esco/ is not changed. Candidates are for the
author to judge; none is selected here.

Outputs (committed):
    data/vocabulary/esco_search_candidates.csv

Usage: python scripts/search_esco_occupations.py [--limit 10]
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path

from download_esco import get_json  # scripts/ is on sys.path when run as a script

REPO_ROOT = Path(__file__).resolve().parents[1]
SUBSET = REPO_ROOT / "data/raw/esco/occupations_en.csv"
OUT = REPO_ROOT / "data/vocabulary/esco_search_candidates.csv"
REQUEST_GAP_S = 1.0
SEARCH_HIT_CHARS = 80  # hits can be whole ESCO descriptions

# area_id -> search labels
QUERIES: dict[int, list[str]] = {
    5: ["painter", "house painter", "decorator"],
    13: ["beautician", "beauty"],
    18: ["driver", "chauffeur"],
    19: ["courier", "delivery", "messenger"],
    20: ["construction labourer", "construction worker", "building maintenance", "handyman"],
}
AREA_NAMES = {5: "Painter", 13: "Beauty worker", 18: "Driver",
              19: "Delivery / courier worker", 20: "General construction / maintenance worker"}
COLUMNS = ["area_id", "area", "query", "rank", "esco_uri", "esco_label", "isco_code",
           "search_hit", "in_subset"]


def subset_uris(path: Path = SUBSET) -> set[str]:
    with open(path, newline="", encoding="utf-8") as f:
        return {row["conceptUri"] for row in csv.DictReader(f)}


def search_rows(area_id: int, query: str, results: list[dict], in_subset: set[str]) -> list[dict]:
    return [{
        "area_id": area_id, "area": AREA_NAMES[area_id], "query": query, "rank": rank,
        "esco_uri": r["uri"], "esco_label": r.get("title", ""), "isco_code": r.get("code", ""),
        "search_hit": r.get("searchHit", "")[:SEARCH_HIT_CHARS],
        "in_subset": "yes" if r["uri"] in in_subset else "no",
    } for rank, r in enumerate(results, start=1)]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()

    in_subset = subset_uris()
    rows = []
    for area_id, queries in QUERIES.items():
        for query in queries:
            data = get_json("search", [("type", "occupation"), ("language", "en"),
                                       ("text", query), ("limit", str(args.limit))])
            rows += search_rows(area_id, query, data.get("_embedded", {}).get("results", []), in_subset)
            time.sleep(REQUEST_GAP_S)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    print(f"{len(rows)} candidate rows, {sum(r['in_subset'] == 'yes' for r in rows)} already in subset")


if __name__ == "__main__":
    main()
