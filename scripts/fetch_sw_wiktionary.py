"""
Fetches Swahili Wiktionary (sw.wiktionary.org) pages for every alias phrase and
its components, and caches the raw wikitext for offline parsing by
scripts/check_vocabulary_dictionary.py.

Titles: each alias (lowercased, punctuation removed), each word in it, and for
ku- infinitives the verb stem (kufulia -> fulia, -fulia). Batches of up to 50
titles, one request at a time with REQUEST_GAP_S between them, descriptive
User-Agent.

Output (not committed, see data/raw/sw_wiktionary/README.md):
    data/raw/sw_wiktionary/pages.json   {fetched_at, api, pages: {title: wikitext|null}}

Usage: python scripts/fetch_sw_wiktionary.py
"""

from __future__ import annotations

import csv
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALIASES = REPO_ROOT / "data/vocabulary/aliases.csv"
CACHE = REPO_ROOT / "data/raw/sw_wiktionary/pages.json"
API = "https://sw.wiktionary.org/w/api.php"
USER_AGENT = "KaziForce-vocab-research/0.1 (student thesis project; kristina.kemoi@strathmore.edu)"
REQUEST_GAP_S = 1.1
BATCH = 50
ENGLISH_ONLY = {"en"}


def titles_for(alias: str) -> list[str]:
    words = re.sub(r"[^\w\s']", " ", alias.lower()).split()
    titles = [" ".join(words)] + words
    for w in words:
        if w.startswith("ku") and len(w) > 4:
            titles += [w[2:], "-" + w[2:]]
    return titles


def wanted_titles(path: Path = ALIASES) -> list[str]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["language"] not in ENGLISH_ONLY]
    return sorted({t for r in rows for t in titles_for(r["alias"])})


def fetch(titles: list[str]) -> dict[str, str | None]:
    pages: dict[str, str | None] = {}
    for i in range(0, len(titles), BATCH):
        batch = titles[i:i + BATCH]
        params = {"action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main",
                  "redirects": "1", "format": "json", "formatversion": "2", "titles": "|".join(batch)}
        req = urllib.request.Request(f"{API}?{urllib.parse.urlencode(params)}",
                                     headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=60) as resp:
            query = json.load(resp)["query"]
        # Map each requested title through MediaWiki's normalisation and redirects.
        alias_of = {t: t for t in batch}
        for step in ("normalized", "redirects"):
            for m in query.get(step, []):
                for t, cur in alias_of.items():
                    if cur == m["from"]:
                        alias_of[t] = m["to"]
        content = {p["title"]: (None if p.get("missing") else p["revisions"][0]["slots"]["main"]["content"])
                   for p in query["pages"]}
        for t in batch:
            pages[t] = content.get(alias_of[t])
        time.sleep(REQUEST_GAP_S)
    return pages


def main() -> None:
    titles = wanted_titles()
    pages = fetch(titles)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "api": API, "pages": pages,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(titles)} titles, {sum(v is not None for v in pages.values())} pages found")


if __name__ == "__main__":
    main()
