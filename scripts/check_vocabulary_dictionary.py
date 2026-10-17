"""
Dictionary evidence for data/vocabulary/aliases.csv from two Wiktionary-based
sources, both cached locally and not committed:
    kaikki_en      kaikki.org Swahili extract of English Wiktionary (data/raw/kaikki/)
    sw_wiktionary  Swahili Wiktionary pages (data/raw/sw_wiktionary/, fetched by
                   scripts/fetch_sw_wiktionary.py); only pages with a Swahili
                   ({{sw}}) section count

For each alias, the full phrase and each component are looked up in each source.
A component counts as found if it is a headword, or (kaikki) an inflected or
alternative form of one (mabomba -> bomba, kufulia -> fulia), or (sw) a page
for its ku- verb stem. Function words (wa, ya, vya, la) are recorded but do not
decide the result; English tokens are not looked up.

dictionary_check (combined over both sources):
    found_exact        the full phrase is a headword in either source
    found_components   every Swahili content component is found in at least one source
    not_found          some Swahili content component is found in neither
    not_checked        English-only alias

Outputs:
    data/vocabulary/dictionary_evidence.csv   one row per (alias, component, source)
    data/vocabulary/aliases.csv               dictionary_check, dictionary_source
                                              and entry_url updated in place;
                                              every other column is preserved
No dictionary glosses are written to either file (Wiktionary text is CC BY-SA);
gloss_note in aliases.csv is written by hand. Glosses are only held in memory,
e.g. for scripts/propose_vocabulary_status.py.

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
SW_CACHE = REPO_ROOT / "data/raw/sw_wiktionary/pages.json"
ALIASES = REPO_ROOT / "data/vocabulary/aliases.csv"
EVIDENCE = REPO_ROOT / "data/vocabulary/dictionary_evidence.csv"
SOURCE_LABELS = {
    "kaikki_en": "kaikki.org Swahili (Wiktionary extract, file dated 2026-10-03)",
    "sw_wiktionary": "sw.wiktionary.org (fetched 2026-10-06)",
}

FUNCTION_WORDS = {"wa", "ya", "vya", "la", "za", "cha", "kwa"}
ENGLISH_TOKENS = {"courier", "repairer", "welder", "plumber", "carpenter"}

EVIDENCE_COLUMNS = [
    "area_id", "alias", "component", "role", "source", "result", "headword", "pos",
    "occupation_tagged", "url",
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

NOT_FOUND = {"result": "not_found", "headword": "", "pos": "", "occupation_tagged": False,
             "url": "", "glosses": []}


def wiktionary_url(word: str) -> str:
    return f"https://en.wiktionary.org/wiki/{urllib.parse.quote(word.replace(' ', '_'))}#Swahili"


def sw_wiktionary_url(word: str) -> str:
    return f"https://sw.wiktionary.org/wiki/{urllib.parse.quote(word.replace(' ', '_'))}"


# kaikki (English Wiktionary)

def load_index(path: Path = KAIKKI) -> tuple[dict, dict]:
    """headword -> [{pos, occupation_tagged, form_of, glosses, categories}], and form -> {headwords}."""
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
    """kaikki lookup: headword, else inflected/alternative form of a headword."""
    hits = entries.get(term, [])
    lemma_hits = [h for h in hits if not h["form_of"]]
    if lemma_hits:
        return {"result": "headword", "headword": term, "pos": "/".join(sorted({h["pos"] for h in lemma_hits})),
                "occupation_tagged": any(h["occupation_tagged"] for h in lemma_hits),
                "url": wiktionary_url(term), "glosses": [g for h in hits for g in h["glosses"]]}
    # Verb lemmas are cited as "-fulia" in glosses but stored and titled "fulia".
    targets = {t.lstrip("-") for h in hits for t in h["form_of"]} | forms.get(term, set())
    if targets:
        lemma = sorted(targets)[0]
        lemma_entries = entries.get(lemma, [])
        return {"result": "form_of", "headword": lemma,
                "pos": "/".join(sorted({h["pos"] for h in lemma_entries} or {h["pos"] for h in hits})),
                "occupation_tagged": any(h["occupation_tagged"] for h in lemma_entries),
                "url": wiktionary_url(lemma),
                "glosses": [g for h in hits + lemma_entries for g in h["glosses"]]}
    return dict(NOT_FOUND)


# Swahili Wiktionary

_HEADER_RE = re.compile(r"^(=+)\s*(.*?)\s*=+\s*$")
_SW_TEMPLATE_RE = re.compile(r"\{\{(?:-+\|)?sw\}\}")
_EN_LINE_RE = re.compile(r"\{\{(ta|tafs)\|en\}\}|\{\{en\}\}")
_EN_TERM_RE = re.compile(r"\{\{t\|en\|([^}|]+)[^}]*\}\}|\[\[([^\]:|]+)(?:\|[^\]]*)?\]\]")
# Section headers that are not languages, even when written at level 2 (==Tafsiri==).
_NON_LANGUAGE_HEADERS = {"tafsiri", "mfano", "matamshi", "etimolojia", "visawe", "marejeo", "tazama pia"}


def parse_sw_page(wikitext: str) -> dict | None:
    """Swahili section of a sw.wiktionary page: part-of-speech headers and English translations.

    Returns None if the page has no Swahili section. A Swahili section starts at
    a {{sw}} / {{-|sw}} / {{--|sw}} header or a header reading "Kiswahili" (at
    any level), and ends at the next level-2 language header, e.g. =={{en}}== or
    ==Kiyoruba==. Level-2 "==Tafsiri==" (translations) does not end it.
    """
    in_sw, seen_sw, pos, english = False, False, [], []
    for line in wikitext.splitlines():
        header = _HEADER_RE.match(line.strip())
        if header:
            level, text = len(header.group(1)), header.group(2)
            if _SW_TEMPLATE_RE.search(text) or text.lower() == "kiswahili":
                in_sw = seen_sw = True
            elif level == 2 and text.lower() not in _NON_LANGUAGE_HEADERS:
                in_sw = False
            elif in_sw and text.lower() not in _NON_LANGUAGE_HEADERS:
                pos.append(text.lower())
            continue
        if in_sw and _EN_LINE_RE.search(line):
            english += [(a or b).strip() for a, b in _EN_TERM_RE.findall(line.split(":", 1)[-1])]
    return {"pos": pos, "english": english} if seen_sw else None


def load_sw_index(path: Path = SW_CACHE) -> dict[str, dict]:
    """title -> {pos, english} for cached pages with a Swahili section."""
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run scripts/fetch_sw_wiktionary.py")
    pages = json.loads(path.read_text(encoding="utf-8"))["pages"]
    index = {}
    for title, text in pages.items():
        parsed = parse_sw_page(text) if text else None
        if parsed is not None:
            index[title.lower()] = parsed
    return index


def sw_lookup(term: str, sw_index: dict) -> dict:
    candidates = [term] + ([term[2:], "-" + term[2:]] if term.startswith("ku") and len(term) > 4 else [])
    for c in candidates:
        if c in sw_index:
            hit = sw_index[c]
            return {"result": "headword" if c == term else "verb_stem", "headword": c,
                    "pos": "/".join(hit["pos"]), "occupation_tagged": False,
                    "url": sw_wiktionary_url(c), "glosses": list(hit["english"])}
    return dict(NOT_FOUND)


# Combined evidence

class Sources:
    """Both dictionaries behind one lookup(term) -> {source: result}."""

    def __init__(self, kaikki_path: Path = KAIKKI, sw_path: Path = SW_CACHE):
        self.entries, self.forms = load_index(kaikki_path)
        self.sw_index = load_sw_index(sw_path)

    def lookup(self, term: str) -> dict[str, dict]:
        return {"kaikki_en": lookup(term, self.entries, self.forms),
                "sw_wiktionary": sw_lookup(term, self.sw_index)}


def tokens(alias: str) -> list[str]:
    return re.sub(r"[^\w\s']", " ", alias.lower()).split()


def _found(results: dict[str, dict]) -> bool:
    return any(r["result"] != "not_found" for r in results.values())


def gather(alias: str, sources: Sources) -> dict:
    """Per-source lookups for an alias: {"english_only", "phrase", "components": [(token, role, results)]}."""
    toks = tokens(alias)
    if all(t in ENGLISH_TOKENS for t in toks):
        return {"english_only": True, "phrase": None, "components": []}
    phrase = sources.lookup(" ".join(toks))
    components, seen_content = [], False
    for t in toks:
        if t in ENGLISH_TOKENS:
            components.append((t, "english", None))
            continue
        role = "function_word" if t in FUNCTION_WORDS else ("complement" if seen_content else "head")
        seen_content |= role != "function_word"
        components.append((t, role, sources.lookup(t)))
    return {"english_only": False, "phrase": phrase, "components": components, "multiword": len(toks) > 1}


def summarise(g: dict) -> dict:
    """dictionary_check, dictionary_source and entry_url for one alias."""
    if g["english_only"]:
        return {"dictionary_check": "not_checked", "dictionary_source": "", "entry_url": ""}
    content = [res for _, role, res in g["components"] if role in {"head", "complement"}]
    if _found(g["phrase"]):
        check, hits = "found_exact", [g["phrase"]]
    elif content and all(_found(r) for r in content):
        check, hits = "found_components", content
    else:
        check, hits = "not_found", [r for r in content if _found(r)]
    used = [s for s in SOURCE_LABELS if any(h[s]["result"] != "not_found" for h in hits)]
    urls = [h[s]["url"] for h in hits for s in SOURCE_LABELS if h[s]["result"] != "not_found"]
    return {"dictionary_check": check,
            "dictionary_source": " ; ".join(SOURCE_LABELS[s] for s in used) or "; ".join(SOURCE_LABELS.values()),
            "entry_url": " ; ".join(dict.fromkeys(urls))}


def evidence_rows(row: dict, g: dict) -> list[dict]:
    out = []

    def add(component, role, source, res):
        out.append({"area_id": row["area_id"], "alias": row["alias"], "component": component, "role": role,
                    "source": source, "result": res["result"], "headword": res["headword"], "pos": res["pos"],
                    "occupation_tagged": ("yes" if res["occupation_tagged"] else "no")
                    if source == "kaikki_en" else "",
                    "url": res["url"]})

    if g["english_only"]:
        add(row["alias"].lower(), "phrase", "", {**NOT_FOUND, "result": "not_checked_english"})
        return out
    if g["multiword"]:  # a single-word alias is its own phrase; recorded below as "head"
        for source, res in g["phrase"].items():
            add(" ".join(tokens(row["alias"])), "phrase", source, res)
    for t, role, results in g["components"]:
        if results is None:
            add(t, role, "", {**NOT_FOUND, "result": "not_checked_english"})
            continue
        for source, res in results.items():
            add(t, role, source, res)
    return out


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
    parser.add_argument("--sw-cache", type=Path, default=SW_CACHE)
    parser.add_argument("--aliases", type=Path, default=ALIASES)
    parser.add_argument("--evidence", type=Path, default=EVIDENCE)
    parser.add_argument("--occupations", action="store_true",
                        help="print occupation-tagged headwords matched to areas (glosses shown, not saved)")
    args = parser.parse_args()

    sources = Sources(args.kaikki, args.sw_cache)
    with open(args.aliases, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns, rows = reader.fieldnames, list(reader)

    all_evidence = []
    for row in rows:
        g = gather(row["alias"], sources)
        row.update(summarise(g))
        all_evidence += evidence_rows(row, g)

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
        for e in occupation_entries(sources.entries):
            print(f"{e['word']}\t{e['areas']}\t{e['glosses'][:90]}")


if __name__ == "__main__":
    main()
