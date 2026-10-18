"""The committed ESCO subset in data/kg/ (rebuild with scripts/build_kg_inputs.py; offline unless --refetch)."""

import csv
import importlib.util
import json
from pathlib import Path

import pytest

from kaziforce_api.data.synthetic import sha256_file

ROOT = Path(__file__).resolve().parents[1]
KG = ROOT / "data" / "kg"
AREA_MAP = ROOT / "data" / "vocabulary" / "area_esco_map.csv"
POOLS = ROOT / "data" / "raw" / "synthetic" / "inputs" / "area_skill_pools.csv"


def _read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


@pytest.fixture(scope="module")
def kg():
    return {p.stem: _read(p) for p in KG.glob("*.csv")} | {"manifest": json.loads((KG / "manifest.json").read_text())}


def test_files_match_the_manifest(kg):
    m = kg["manifest"]
    assert m["outputs_sha256"] == {f"{name}": sha256_file(KG / name) for name in m["outputs_sha256"]}
    assert m["inputs_sha256"] == {"area_esco_map.csv": sha256_file(AREA_MAP), "area_skill_pools.csv": sha256_file(POOLS)}
    assert {f"{k}.csv": len(v) for k, v in kg.items() if k != "manifest"} == m["counts"]


def test_no_area_information_reaches_the_kg_inputs():
    for path in KG.glob("*.csv"):
        with open(path, newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))
        assert not [c for c in header if "area" in c], path.name


def test_occupations_are_the_selected_shortlist(kg):
    selected = {r["esco_uri"] for r in _read(AREA_MAP) if r["selected"] == "yes" and r["shortlisted"] == "yes"}
    assert {o["uri"] for o in kg["occupations"]} == selected and len(selected) == 11


def test_skills_and_relations_match_the_pools(kg):
    pools = _read(POOLS)
    assert {(p["esco_uri"], p["relation"], p["skill_uri"]) for p in pools} == {
        (r["occupation_uri"], r["relation"], r["skill_uri"]) for r in kg["occupation_skills"]}
    assert {p["skill_uri"]: p["skill_label"] for p in pools} == {s["uri"]: s["label"] for s in kg["skills"]}
    assert {s["skill_type"] for s in kg["skills"]} == {"skill", "knowledge"}


def test_hierarchy_is_one_hop_and_fully_labelled(kg):
    skills = {s["uri"] for s in kg["skills"]}
    groups = {g["uri"]: g for g in kg["skill_groups"]}
    assert {r["skill_uri"] for r in kg["skill_broader"]} == skills
    assert {r["broader_uri"] for r in kg["skill_broader"]} == set(groups)
    assert all(g["label"] and g["scheme"] in {"esco_skill_group", "isced_f"} for g in groups.values())
    assert not skills & set(groups)


def test_barber_is_narrower_than_hairdresser(kg):
    label = {o["uri"]: o["label"] for o in kg["occupations"]}
    assert [(label[r["occupation_uri"]], label[r["broader_uri"]]) for r in kg["occupation_broader"]] == [
        ("barber", "hairdresser")]


def test_occupation_broader_uses_the_nearest_dotted_prefix():
    spec = importlib.util.spec_from_file_location("build_kg_inputs", ROOT / "scripts" / "build_kg_inputs.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    occ = [{"uri": "a", "isco_code": "5141.1"}, {"uri": "b", "isco_code": "5141.1.1"},
           {"uri": "c", "isco_code": "5141.11"}, {"uri": "d", "isco_code": "5141"}]
    assert module.occupation_broader(occ) == [{"occupation_uri": "a", "broader_uri": "d"},
                                              {"occupation_uri": "b", "broader_uri": "a"},
                                              {"occupation_uri": "c", "broader_uri": "d"}]
