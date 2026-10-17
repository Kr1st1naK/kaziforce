"""Alias normalisation, KG vocabulary loader, and aliases.csv integrity."""

import csv
from collections import defaultdict
from pathlib import Path

import pytest

from kaziforce_kg.vocabulary import (
    aliases_equivalent,
    held_out_aliases,
    load_kg_vocabulary,
    normalize_alias,
    read_aliases,
)

VOCAB_DIR = Path(__file__).resolve().parents[1] / "data" / "vocabulary"
ALIASES = VOCAB_DIR / "aliases.csv"
AREA_MAP = VOCAB_DIR / "area_esco_map.csv"

COLUMNS = [
    "area_id", "esco_uri", "esco_label", "alias", "language", "register", "status",
    "kg_included", "dictionary_check", "dictionary_source", "entry_url", "gloss_note",
    "sense_ok", "usage_evidence_url", "validated_by", "notes",
    "proposed_sense_ok", "proposed_status", "confidence", "proposed_reason", "decision_date",
]
ALLOWED = {
    "language": {"sw", "en", "code-switched"},
    "register": {"trade_name", "descriptive", "english_label", "rejected"},
    "status": {"pending_review", "accepted", "rejected"},
    "kg_included": {"yes", "no", "undecided"},
    "dictionary_check": {"found_exact", "found_components", "not_found", "not_checked"},
    "sense_ok": {"yes", "no", "unclear"},
    "proposed_sense_ok": {"yes", "no", "unclear", ""},
    "proposed_status": {"recommend_accept", "recommend_reject", "needs_human", ""},
    "confidence": {"high", "medium", ""},
}


# Normalisation

@pytest.mark.parametrize("a, b", [
    ("fundi wa stima", "fundi stima"),
    ("Fundi Wa Stima", "fundi stima"),
    ("fundi wa stimu", "fundi wa stima"),
    ("mafundi wa stima", "fundi stima"),
    ("  fundi-wa-stima!  ", "fundi stima"),
    ("mfanyikazi wa ujenzi", "mfanyakazi ujenzi"),
    ("Fundi  bomba.", "fundi bomba"),
    ("fundi\twa\nmbao", "fundi mbao"),
])
def test_equivalent_forms(a, b):
    assert aliases_equivalent(a, b)


@pytest.mark.parametrize("a, b", [
    ("fundi wa umeme", "fundi bomba"),
    ("fundi wa umeme", "fundi wa stima"),  # synonyms stay separate aliases
    ("fundi wa simu", "fundi wa nguo"),
    ("mama fua", "mfanyakazi wa kufulia"),
    ("mpishi", "mpishi mkuu"),
    ("fundi wa magari", "fundi wa pikipiki"),
])
def test_distinct_aliases_stay_distinct(a, b):
    assert not aliases_equivalent(a, b)


def test_normalize_alias_canonical_form():
    assert normalize_alias("Mafundi wa Stimu") == "fundi stima"
    assert normalize_alias("ng'ombe") == "ngombe"  # apostrophe removed, not split


def test_variants_apply_to_whole_tokens_only():
    assert normalize_alias("mafundisho") == "mafundisho"
    assert normalize_alias("wakala wa simu") == "wakala simu"


# KG vocabulary loader

def _write_aliases(path: Path, rows: list[dict]) -> Path:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({c: row.get(c, "") for c in COLUMNS})
    return path


def _row(alias, status, kg_included):
    return {"area_id": "1", "alias": alias, "status": status, "kg_included": kg_included}


def test_loader_uses_only_accepted_and_included(tmp_path):
    path = _write_aliases(tmp_path / "aliases.csv", [
        _row("fundi wa umeme", "accepted", "yes"),
        _row("fundi wa stima", "accepted", "no"),
        _row("fundi bomba", "pending_review", "yes"),
        _row("mchoraji", "rejected", "yes"),
        _row("mwashi", "accepted", "undecided"),
    ])
    out = load_kg_vocabulary(path)
    assert [r["alias"] for r in out] == ["fundi wa umeme"]
    assert out[0]["normalized"] == "fundi umeme"


def test_held_out_alias_never_in_loader_output(tmp_path):
    path = _write_aliases(tmp_path / "aliases.csv", [
        _row("fundi wa umeme", "accepted", "yes"),
        _row("kinyozi", "accepted", "yes"),
        _row("fundi wa stima", "accepted", "no"),
    ])
    out_keys = {r["normalized"] for r in load_kg_vocabulary(path)}
    held_out = held_out_aliases(read_aliases(path))
    assert [r["alias"] for r in held_out] == ["fundi wa stima"]
    assert not out_keys & {normalize_alias(r["alias"]) for r in held_out}


def test_loader_rejects_held_out_alias_equivalent_to_included(tmp_path):
    path = _write_aliases(tmp_path / "aliases.csv", [
        _row("fundi wa stima", "accepted", "yes"),
        _row("Mafundi stimu", "accepted", "no"),
    ])
    with pytest.raises(ValueError, match="Mafundi stimu"):
        load_kg_vocabulary(path)


def test_loader_on_committed_aliases_excludes_held_out():
    out_keys = {r["normalized"] for r in load_kg_vocabulary(ALIASES)}
    held_out_keys = {normalize_alias(r["alias"]) for r in held_out_aliases(read_aliases(ALIASES))}
    assert not out_keys & held_out_keys


# aliases.csv integrity

@pytest.fixture(scope="module")
def aliases():
    with open(ALIASES, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == COLUMNS
        return list(reader)


@pytest.fixture(scope="module")
def area_map():
    with open(AREA_MAP, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_enumerated_columns_use_allowed_values(aliases):
    for row in aliases:
        for col, allowed in ALLOWED.items():
            assert row[col] in allowed, (row["alias"], col, row[col])


def test_accepted_rows_name_a_validator(aliases):
    assert all(r["validated_by"] for r in aliases if r["status"] == "accepted")


def test_rejected_rows_keep_a_reason(aliases):
    for row in aliases:
        if row["status"] == "rejected":
            assert row["register"] == "rejected" and row["notes"], row["alias"]


def test_gloss_notes_are_at_most_five_words(aliases):
    assert all(len(r["gloss_note"].split()) <= 5 for r in aliases)


def test_no_duplicate_alias_within_an_area(aliases):
    keys = [(r["area_id"], normalize_alias(r["alias"])) for r in aliases]
    assert len(keys) == len(set(keys))


def test_area_ids_exist_in_area_map(aliases, area_map):
    known = {r["area_id"] for r in area_map}
    for row in aliases:
        if row["area_id"]:
            assert row["area_id"] in known, row["alias"]
        else:
            assert row["status"] == "rejected", f"{row['alias']}: only rejected rows may lack an area"


def test_esco_uri_is_an_exact_match_for_its_area(aliases, area_map):
    exact = {(r["area_id"], r["esco_uri"]) for r in area_map if r["match_type"].startswith("exact")}
    for row in aliases:
        if row["esco_uri"]:
            assert (row["area_id"], row["esco_uri"]) in exact, row["alias"]


def test_no_alias_maps_to_two_esco_occupations_unless_ambiguous(aliases, area_map):
    status = {r["area_id"]: r["mapping_status"] for r in area_map}
    uris, areas = defaultdict(set), defaultdict(set)
    for row in aliases:
        if row["esco_uri"]:
            key = normalize_alias(row["alias"])
            uris[key].add(row["esco_uri"])
            areas[key].add(row["area_id"])
    for key, found in uris.items():
        if len(found) > 1:
            assert all(status[a] == "multiple" for a in areas[key]), f"{key} maps to {sorted(found)}"


def test_no_excluded_alias_equivalent_to_included_alias(aliases):
    included = {normalize_alias(r["alias"]) for r in aliases if r["kg_included"] == "yes"}
    excluded = {normalize_alias(r["alias"]) for r in aliases if r["kg_included"] == "no"}
    assert not included & excluded


# area_esco_map.csv: shortlist and ESCO proposals

def test_every_shortlisted_area_has_a_proposed_exact_match(area_map):
    shortlisted = {r["area_id"] for r in area_map if r["shortlisted"] == "yes"}
    proposed = {r["area_id"] for r in area_map if r["proposed"] == "yes"}
    assert len(shortlisted) == 10 and shortlisted <= proposed
    for row in area_map:
        if row["proposed"] == "yes":
            assert row["match_type"].startswith("exact") and row["proposed_reason"], row["esco_label"]
        assert row["proposed"] in {"yes", ""} and row["selected"] in {"yes", ""}


def test_regenerating_the_area_map_keeps_manual_columns():
    import importlib.util

    import pandas as pd

    spec = importlib.util.spec_from_file_location(
        "map_vocabulary_areas", Path(__file__).resolve().parents[1] / "scripts" / "map_vocabulary_areas.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    new = pd.DataFrame({"area_id": [1, 1, 2], "esco_uri": ["u1", "u2", "u3"]})
    old = pd.DataFrame({"area_id": ["1", "2"], "esco_uri": ["u2", "u3"], "selected": ["yes", ""],
                        "proposed": ["yes", "yes"], "proposed_reason": ["r1", "r2"],
                        "shortlisted": ["yes", "no"]})
    out = module.carry_over_manual_columns(new, old)
    assert list(out["selected"]) == ["", "yes", ""]
    assert list(out["proposed_reason"]) == ["", "r1", "r2"]
    assert list(out["shortlisted"]) == ["yes", "yes", "no"]


# usage_evidence.csv: held-out candidates only, no personal data

USAGE = VOCAB_DIR / "usage_evidence.csv"


def test_usage_evidence_has_only_the_agreed_fields_and_no_contact_details():
    import re

    with open(USAGE, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == ["alias", "url", "page_title", "accessed_on"]
        rows = list(reader)
    phone = re.compile(r"(\+?254|\b0)[17]\d{8}\b|\d{3}[\s-]\d{3}[\s-]\d{3,4}")
    for row in rows:
        text = " ".join(row.values())
        assert "@" not in text and not phone.search(text), row["alias"]
        assert row["url"] == "none" or row["url"].startswith("https://")
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", row["accessed_on"])
    per_alias = defaultdict(int)
    for row in rows:
        per_alias[row["alias"]] += 1
    assert all(n <= 2 for n in per_alias.values())


def test_usage_evidence_urls_match_aliases_csv(aliases):
    with open(USAGE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for alias in {r["alias"] for r in rows}:
        urls = [r["url"] for r in rows if r["alias"] == alias and r["url"] != "none"]
        recorded = next(r["usage_evidence_url"] for r in aliases if r["alias"] == alias)
        assert recorded == (" ; ".join(urls) or "none")
