"""ESCO API response parsing in scripts/download_esco.py (offline, fixture-based)."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "download_esco", Path(__file__).resolve().parents[1] / "scripts" / "download_esco.py"
)
download_esco = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(download_esco)

SKILL_URI = "http://data.europa.eu/esco/skill/abc"
OCCUPATION = {
    "uri": "http://data.europa.eu/esco/occupation/xyz",
    "code": "7411.1",
    "preferredLabel": {"en": "electrician"},
    "alternativeLabel": {"en": ["installation electrician", "wirewoman"]},
    "description": {"en": {"literal": "Electricians fit and repair wiring."}},
    "_links": {
        "hasEssentialSkill": [{"uri": SKILL_URI, "skillType": "http://data.europa.eu/esco/skill-type/skill"}],
        "hasOptionalSkill": [{"uri": SKILL_URI + "2", "skillType": "http://data.europa.eu/esco/skill-type/knowledge"}],
    },
}


def test_parse_occupation():
    row = download_esco.parse_occupation(OCCUPATION, "7411", ["Electrician"])
    assert row["preferredLabel"] == "electrician"
    assert row["altLabels"] == "installation electrician\nwirewoman"
    assert row["iscoGroup"] == "7411" and row["vocabularyArea"] == "Electrician"


def test_parse_relations():
    rows = download_esco.parse_relations(OCCUPATION)
    assert [(r["relationType"], r["skillType"]) for r in rows] == [
        ("essential", "skill"), ("optional", "knowledge"),
    ]


def test_parse_skill_handles_missing_fields():
    row = download_esco.parse_skill({"uri": SKILL_URI, "preferredLabel": {"en": "splice cable"}, "_links": {}})
    assert row["preferredLabel"] == "splice cable"
    assert row["skillType"] == "" and row["altLabels"] == "" and row["description"] == ""


def test_isco_groups_cover_every_vocabulary_area():
    areas = {a for group in download_esco.ISCO_GROUPS.values() for a in group}
    assert len(areas) == 20
