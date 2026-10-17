"""
Kenya-specific informal trade vocabulary extension.

Validation pipeline (proposal Limitations section):
    1. LLM-assisted candidate generation for a given ESCO occupation/skill
    2. ESCO cross-reference (formal equivalent exists?)
    3. Manual review before the term is added to the graph.

Alias records live in data/vocabulary/aliases.csv. The KG uses only rows the
author has accepted and marked kg_included=yes; accepted rows marked
kg_included=no are held out (unseen terms for the cold-start experiment).
"""

from __future__ import annotations

import csv
import os
import re
import unicodedata
from pathlib import Path

# Orthographic variants treated as the same token. Lexical synonyms (e.g. umeme
# vs stima) are deliberately NOT merged: they are separate aliases.
_TOKEN_VARIANTS = {
    "mafundi": "fundi",
    "stimu": "stima",
    "mfanyikazi": "mfanyakazi",
}
_OPTIONAL_TOKENS = {"wa"}  # "fundi wa stima" == "fundi stima"
_APOSTROPHE_RE = re.compile(r"['’‘`]")  # ng'ombe -> ngombe, not "ng ombe"
_PUNCT_RE = re.compile(r"[^\w\s]|_")


def normalize_alias(text: str) -> str:
    """Canonical key for comparing aliases.

    Lowercases, trims, removes punctuation, collapses whitespace, drops the
    optional connective "wa", and maps orthographic variants
    (mafundi -> fundi, stimu -> stima, mfanyikazi -> mfanyakazi).
    """
    text = unicodedata.normalize("NFKC", str(text)).casefold()
    text = _APOSTROPHE_RE.sub("", text)
    text = _PUNCT_RE.sub(" ", text)
    tokens = [_TOKEN_VARIANTS.get(t, t) for t in text.split() if t not in _OPTIONAL_TOKENS]
    return " ".join(tokens)


def aliases_equivalent(a: str, b: str) -> bool:
    return normalize_alias(a) == normalize_alias(b)


def _default_aliases_path() -> Path:
    override = os.getenv("KAZIFORCE_DATA_DIR")
    if override:
        return Path(override).resolve() / "vocabulary" / "aliases.csv"
    for parent in Path(__file__).resolve().parents:
        if (parent / "data" / "vocabulary" / "aliases.csv").exists():
            return parent / "data" / "vocabulary" / "aliases.csv"
    raise FileNotFoundError("data/vocabulary/aliases.csv not found; set KAZIFORCE_DATA_DIR.")


def read_aliases(path: Path | None = None) -> list[dict]:
    with open(path or _default_aliases_path(), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def held_out_aliases(rows: list[dict]) -> list[dict]:
    """Accepted aliases deliberately kept out of the KG."""
    return [r for r in rows if r["status"] == "accepted" and r["kg_included"] == "no"]


def load_kg_vocabulary(path: Path | None = None) -> list[dict]:
    """Alias rows for the KG: status=accepted AND kg_included=yes only.

    Each returned row gains a `normalized` key. Raises ValueError if a
    kg_included=no alias normalises to the same key as an included one, since
    the held-out term would then reach the KG through normalisation.
    """
    rows = read_aliases(path)
    included = [r for r in rows if r["status"] == "accepted" and r["kg_included"] == "yes"]
    included_keys = {normalize_alias(r["alias"]) for r in included}
    leaks = sorted(
        r["alias"] for r in rows
        if r["kg_included"] == "no" and normalize_alias(r["alias"]) in included_keys
    )
    if leaks:
        raise ValueError(f"kg_included=no aliases equivalent to included ones: {leaks}")
    return [{**r, "normalized": normalize_alias(r["alias"])} for r in included]


class VocabularyExtension:
    """The Kenya-specific informal-term extension of the ESCO backbone.

    kg_terms() are the only aliases the knowledge graph may contain; loading
    fails if a held-out alias normalises to the same key as an included one.
    """

    def __init__(self, aliases_path: Path | None = None):
        self.aliases_path = aliases_path or _default_aliases_path()
        self._rows = read_aliases(self.aliases_path)
        self._kg_terms = load_kg_vocabulary(self.aliases_path)

    def kg_terms(self) -> list[dict]:
        """Accepted, kg_included=yes rows, each with a `normalized` key."""
        return [dict(r) for r in self._kg_terms]

    def held_out_terms(self) -> list[dict]:
        """Accepted rows deliberately kept out of the graph (unseen-term test)."""
        return [{**r, "normalized": normalize_alias(r["alias"])} for r in held_out_aliases(self._rows)]

    @staticmethod
    def normalize(text: str) -> str:
        return normalize_alias(text)


def generate_candidate_terms(esco_label: str) -> list[str]:
    """Prompt an LLM for candidate informal/vernacular terms for an ESCO label.

    TODO: implement LLM call, see LLM_API_KEY in .env
    """
    raise NotImplementedError


def validate_against_esco(term: str, formal_label: str) -> bool:
    """Cross-check whether the informal term plausibly maps to the formal ESCO label.

    TODO: implement using ESCO alternative labels (including Swahili where available).
    """
    raise NotImplementedError


def review_candidate(term: str, formal_label: str, sources: list[str]) -> dict:
    """Manually review a candidate term and return an approval record.

    Returns a dict with keys: informal_term, formal_term, approved, notes.
    """
    raise NotImplementedError
