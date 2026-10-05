"""
Dictionary evidence for data/vocabulary/aliases.csv from the kaikki.org Swahili
extract of Wiktionary (data/raw/kaikki/, see its README; not committed).

For each alias, the full phrase and each component are looked up. A component
counts as found if it is a headword, or an inflected/alternative form of one
(e.g. mabomba -> bomba, kufulia -> fulia). Function words (wa, ya, vya, la) are
recorded but do not decide the result; English tokens are not looked up.

dictionary_check:
    found_exact        the full phrase is a headword
    found_components   every Swahili content component is found
    not_found          some Swahili content component is missing
    not_checked        English-only alias

Outputs:
    data/vocabulary/dictionary_evidence.csv   one row per (alias, component)
    data/vocabulary/aliases.csv               dictionary_check, dictionary_source
                                              and entry_url updated in place;
                                              every other column is preserved
No dictionary glosses are written to either file (Wiktionary text is CC BY-SA);
gloss_note in aliases.csv is written by hand.

Usage: python scripts/check_vocabulary_dictionary.py [--occupations]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import urllib.parse
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
KAIKKI = REPO_ROOT / "data/raw/kaikki/kaikki.org-dictionary-Swahili.jsonl"
ALIASES = REPO_ROOT / "data/vocabulary/aliases.csv"
EVIDENCE = REPO_ROOT / "data/vocabulary/dictionary_evidence.csv"
SOURCE = "kaikki.org Swahili (Wiktionary extract, file dated 2026-10-03)"

FUNCTION_WORDS = {"wa", "ya", "vya", "la", "za", "cha", "kwa"}
ENGLISH_TOKENS = {"courier", "repairer", "welder", "plumber", "carpenter"}

EVIDENCE_COLUMNS = [
    "area_id", "alias", "component", "role", "result", "headword", "pos",
    "occupation_tagged", "wiktionary_url",
]

# Gloss keywords used only for the --occupations report (area_id -> regex).
OCCUPATION_GLOSS_KEYWORDS = {
    1: r"electric", 2: r"plumb", 3: r"carpent|joiner", 4: r"mason|brick", 5: r"\bpaint",
    6: r"weld|blacksmith", 7: r"mechanic", 8: r"motorcycl", 9: r"applian|electronic",
    10: r"phone", 11: r"tailor|dressmak|seamst|sewer", 12: r"barber|hairdress|braider",
    13: r"beaut|cosmet|manicur", 14: r"clean|sweeper|housemaid|servant|nanny",
    15: r"laund|washer", 16: r"\bcook|cater|chef|baker", 17: r"garden|groundskeep",
    18: r"driver|chauffeur", 19: r"deliver|courier|messenger|porter|carrier",
    20: r"build|construct|labou?rer|contractor|foreman|dockworker",
}


def wiktionary_url(word: str) -> str:
    return f"https://en.wiktionary.org/wiki/{urllib.parse.quote(word.replace(' ', '_'))}#Swahili"


def load_index(path: Path = KAIKKI) -> tuple[dict, dict]:
    """headword -> [{pos, occupation_tagged, form_of}], and form -> {headwords}."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; see data/raw/kaikki/README.md")
    entries, forms = defaultdict(list), defaultdict(set)
    with open(path, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line)
            word = e["word"].lower()
            senses = e.get("senses", [])
            form_of = [t["word"].lower() for s in senses for t in s.get("form_of", []) + s.get("alt_of", [])]
            entries[word].append({
                "pos": e["pos"],
                "occupation_tagged": any(
                    c.get("name", "").endswith("ccupations") for s in senses for c in s.get("categories", [])
                ),
                "form_of": form_of,
                "glosses": [g for s in senses for g in s.get("glosses", [])],
                "categories": [c.get("name", "") for s in senses for c in s.get("categories", [])],
            })
            for fm in e.get("forms", []):
                form = fm.get("form", "").lower()
                if form and form != word:
                    forms[form].add(word)
    return entries, forms


def lookup(term: str, entries: dict, forms: dict) -> dict:
    hits = entries.get(term, [])
    lemma_hits = [h for h in hits if not h["form_of"]]
    if lemma_hits:
        return {"result": "headword", "headword": term, "pos": "/".join(sorted({h["pos"] for h in lemma_hits})),
                "occupation_tagged": any(h["occupation_tagged"] for h in lemma_hits)}
    # Verb lemmas are cited as "-fulia" in glosses but stored and titled "fulia".
    targets = {t.lstrip("-") for h in hits for t in h["form_of"]} | forms.get(term, set())
    if targets:
        lemma = sorted(targets)[0]
        lemma_entries = entries.get(lemma, [])
        return {"result": "form_of", "headword": lemma,
                "pos": "/".join(sorted({h["pos"] for h in lemma_entries} or {h["pos"] for h in hits})),
                "occupation_tagged": any(h["occupation_tagged"] for h in lemma_entries)}
    return {"result": "not_found", "headword": "", "pos": "", "occupation_tagged": False}


def tokens(alias: str) -> list[str]:
    return re.sub(r"[^\w\s']", " ", alias.lower()).split()


def check_alias(row: dict, entries: dict, forms: dict) -> tuple[dict, list[dict]]:
    alias = row["alias"].strip().lower()
    toks = tokens(alias)
    evidence = []

    def add(component, role, res):
        evidence.append({
            "area_id": row["area_id"], "alias": row["alias"], "component": component, "role": role,
            "result": res["result"], "headword": res["headword"], "pos": res["pos"],
            "occupation_tagged": "yes" if res["occupation_tagged"] else "no",
            "wiktionary_url": wiktionary_url(res["headword"]) if res["headword"] else "",
        })

    if all(t in ENGLISH_TOKENS for t in toks):
        add(alias, "phrase", {"result": "not_checked_english", "headword": "", "pos": "", "occupation_tagged": False})
        return {"dictionary_check": "not_checked", "dictionary_source": "", "entry_url": ""}, evidence

    phrase = lookup(" ".join(toks), entries, forms)
    if len(toks) > 1:  # a single-word alias is its own phrase; recorded once below as "head"
        add(" ".join(toks), "phrase", phrase)
    content = []
    for i, t in enumerate(toks):
        if t in ENGLISH_TOKENS:
            add(t, "english", {"result": "not_checked_english", "headword": "", "pos": "", "occupation_tagged": False})
            continue
        res = lookup(t, entries, forms)
        role = "function_word" if t in FUNCTION_WORDS else ("head" if not content else "complement")
        add(t, role, res)
        if role != "function_word":
            content.append(res)

    if phrase and phrase["result"] != "not_found":
        check, urls = "found_exact", [wiktionary_url(phrase["headword"])]
    elif content and all(r["result"] != "not_found" for r in content):
        check, urls = "found_components", [wiktionary_url(r["headword"]) for r in content]
    else:
        check, urls = "not_found", [wiktionary_url(r["headword"]) for r in content if r["headword"]]
    return {"dictionary_check": check, "dictionary_source": SOURCE, "entry_url": " ; ".join(urls)}, evidence


def occupation_entries(entries: dict) -> list[dict]:
    """Headwords with a sense in the Swahili 'Occupations' category, matched to areas by gloss."""
    out = []
    for word, hits in sorted(entries.items()):
        occ = [h for h in hits if "Occupations" in h["categories"]]
        if not occ:
            continue
        glosses = " ; ".join(g for h in hits for g in h["glosses"])
        areas = [a for a, kw in OCCUPATION_GLOSS_KEYWORDS.items() if re.search(kw, glosses, re.I)]
        out.append({"word": word, "areas": areas, "glosses": glosses})
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--kaikki", type=Path, default=KAIKKI)
    parser.add_argument("--aliases", type=Path, default=ALIASES)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--occupations", action="store_true",
                        help="print occupation-tagged headwords matched to areas (glosses shown, not saved)")
    args = parser.parse_args()

    entries, forms = load_index(args.kaikki)
    with open(args.aliases, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns, rows = reader.fieldnames, list(reader)

    all_evidence = []
    for row in rows:
        update, evidence = check_alias(row, entries, forms)
        row.update(update)
        all_evidence += evidence

    with open(args.aliases, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    with open(args.evidence, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=EVIDENCE_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(all_evidence)

    counts = defaultdict(int)
    for row in rows:
        counts[row["dictionary_check"]] += 1
    print(dict(counts))
    if args.occupations:
        for e in occupation_entries(entries):
            print(f"{e['word']}\t{e['areas']}\t{e['glosses'][:90]}")


if __name__ == "__main__":
    main()
