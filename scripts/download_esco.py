"""
Fetches the ESCO taxonomy subset needed for this project from ESCO's public
REST API (no key required), rather than committing the full dataset to git
(see data/README.md).

Scope: occupations under the ISCO-08 unit groups that correspond to the 20
informal-trade areas in data/vocabulary/README.md (construction, domestic work,
technical trades, personal services, transport), plus every skill those
occupations list as essential or optional, and each skill's broader skill.

Outputs (data/raw/esco/, gitignored). Column names follow ESCO's bulk-download
CSVs so the files can later be swapped for a full bulk download:
    occupations_en.csv                  one row per occupation (+ vocabularyArea)
    skills_en.csv                       one row per referenced skill/knowledge
    occupationSkillRelations_en.csv     occupation -> skill (essential/optional)
    broaderRelationsSkillPillar_en.csv  skill -> broader skill
    download_manifest.json              date, API, ISCO groups, row counts

Usage: python scripts/download_esco.py [--out DIR] [--groups 7411 7126 ...]
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API_BASE = "https://ec.europa.eu/esco/api"
LANGUAGE = "en"
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "data" / "raw" / "esco"
REQUEST_DELAY_S = 0.2
SKILL_BATCH_SIZE = 40

# ISCO-08 unit group -> vocabulary area(s) from data/vocabulary/README.md
ISCO_GROUPS: dict[str, list[str]] = {
    "7411": ["Electrician"],
    "7126": ["Plumber"],
    "7115": ["Carpenter"],
    "7112": ["Mason / bricklayer"],
    "7131": ["Painter / decorator"],
    "7212": ["Welder"],
    "7231": ["Motor-vehicle mechanic", "Motorcycle mechanic"],
    "7412": ["Appliance / electronics repairer"],
    "7421": ["Appliance / electronics repairer"],
    "7422": ["Mobile-phone repairer"],
    "7531": ["Tailor / dressmaker"],
    "5141": ["Hairdresser / barber"],
    "5142": ["Beauty worker"],
    "9111": ["Domestic cleaner"],
    "9121": ["Laundry worker"],
    "8157": ["Laundry worker"],  # ESCO files "launderer" here, not under 9121
    "5120": ["Cook / catering worker"],
    "6113": ["Gardener / grounds worker"],
    "9214": ["Gardener / grounds worker"],
    "8322": ["Driver"],
    "8321": ["Delivery / courier worker"],
    "9621": ["Delivery / courier worker"],
    "7111": ["General construction / maintenance worker"],
    "9313": ["General construction / maintenance worker"],
}


def get_json(path: str, params: list[tuple[str, str]], retries: int = 4) -> dict:
    url = f"{API_BASE}/{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=60) as resp:
                data = json.load(resp)
            time.sleep(REQUEST_DELAY_S)
            return data
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt == retries - 1:
                raise RuntimeError(f"ESCO API request failed: {url}") from exc
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def _label(resource: dict, key: str) -> str:
    return (resource.get(key) or {}).get(LANGUAGE, "") or ""


def _description(resource: dict) -> str:
    return ((resource.get("description") or {}).get(LANGUAGE) or {}).get("literal", "")


def _alt_labels(resource: dict) -> str:
    # ESCO bulk CSVs store alternative labels newline-separated in one cell
    return "\n".join((resource.get("alternativeLabel") or {}).get(LANGUAGE, []))


def _link_uri(resource: dict, rel: str) -> str:
    links = resource.get("_links", {}).get(rel) or []
    if isinstance(links, dict):
        links = [links]
    return links[0]["uri"] if links else ""


def parse_occupation(resource: dict, isco_code: str, areas: list[str]) -> dict:
    return {
        "conceptType": "Occupation",
        "conceptUri": resource["uri"],
        "iscoGroup": isco_code,
        "code": resource.get("code", ""),
        "preferredLabel": _label(resource, "preferredLabel"),
        "altLabels": _alt_labels(resource),
        "description": _description(resource),
        "vocabularyArea": "; ".join(areas),
    }


def parse_skill(resource: dict) -> dict:
    return {
        "conceptType": "KnowledgeSkillCompetence",
        "conceptUri": resource["uri"],
        "skillType": _link_uri(resource, "hasSkillType").rsplit("/", 1)[-1],
        "reuseLevel": _link_uri(resource, "hasReuseLevel").rsplit("/", 1)[-1],
        "preferredLabel": _label(resource, "preferredLabel"),
        "altLabels": _alt_labels(resource),
        "description": _description(resource),
    }


def parse_relations(resource: dict) -> list[dict]:
    rows = []
    for rel, relation_type in (("hasEssentialSkill", "essential"), ("hasOptionalSkill", "optional")):
        for link in resource.get("_links", {}).get(rel, []) or []:
            rows.append({
                "occupationUri": resource["uri"],
                "relationType": relation_type,
                "skillType": link.get("skillType", "").rsplit("/", 1)[-1],
                "skillUri": link["uri"],
            })
    return rows


def collect_occupations(isco_code: str) -> list[dict]:
    """Return every occupation resource under an ISCO unit group, recursively."""
    group = get_json("resource/concept", [
        ("uri", f"http://data.europa.eu/esco/isco/C{isco_code}"), ("language", LANGUAGE),
    ])
    pending = [link["uri"] for link in group.get("_links", {}).get("narrowerOccupation", []) or []]
    seen: dict[str, dict] = {}
    while pending:
        uri = pending.pop()
        if uri in seen:
            continue
        occ = get_json("resource/occupation", [("uri", uri), ("language", LANGUAGE)])
        seen[uri] = occ
        pending += [link["uri"] for link in occ.get("_links", {}).get("narrowerOccupation", []) or []]
    return list(seen.values())


def _fetch_skill_batch(batch: list[str], skills: dict[str, dict], failed: list[str]) -> None:
    """Fetch a batch; if the API errors, bisect so one bad URI can't sink the rest."""
    try:
        data = get_json("resource/skill", [("uris", u) for u in batch] + [("language", LANGUAGE)],
                        retries=2 if len(batch) > 1 else 4)
        skills.update(data.get("_embedded", {}))
    except RuntimeError:
        if len(batch) == 1:
            failed.append(batch[0])
            return
        mid = len(batch) // 2
        _fetch_skill_batch(batch[:mid], skills, failed)
        _fetch_skill_batch(batch[mid:], skills, failed)


def fetch_skills(uris: list[str]) -> tuple[dict[str, dict], list[str]]:
    skills: dict[str, dict] = {}
    failed: list[str] = []
    for i in range(0, len(uris), SKILL_BATCH_SIZE):
        _fetch_skill_batch(uris[i:i + SKILL_BATCH_SIZE], skills, failed)
        print(f"  skills {min(i + SKILL_BATCH_SIZE, len(uris))}/{len(uris)}")
    return skills, failed


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main(out_dir: Path, groups: list[str]) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    occupations: dict[str, dict] = {}
    relations: list[dict] = []

    for code in groups:
        areas = ISCO_GROUPS[code]
        found = collect_occupations(code)
        print(f"ISCO {code} ({', '.join(areas)}): {len(found)} occupations")
        for occ in found:
            if occ["uri"] not in occupations:
                occupations[occ["uri"]] = parse_occupation(occ, code, areas)
                relations += parse_relations(occ)

    skill_uris = sorted({r["skillUri"] for r in relations})
    print(f"Fetching {len(skill_uris)} skills")
    skill_resources, failed = fetch_skills(skill_uris)
    skills = [parse_skill(skill_resources[u]) for u in skill_uris if u in skill_resources]
    broader = [
        {"conceptType": "KnowledgeSkillCompetence", "conceptUri": uri,
         "broaderType": "SkillOrSkillGroup", "broaderUri": link["uri"]}
        for uri, res in skill_resources.items()
        for link in (res.get("_links", {}).get("broaderHierarchyConcept") or [])
    ]

    write_csv(out_dir / "occupations_en.csv", list(occupations.values()))
    write_csv(out_dir / "skills_en.csv", skills)
    write_csv(out_dir / "occupationSkillRelations_en.csv", relations)
    write_csv(out_dir / "broaderRelationsSkillPillar_en.csv", broader)

    manifest = {
        "downloaded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": API_BASE,
        "language": LANGUAGE,
        "isco_groups": {code: ISCO_GROUPS[code] for code in groups},
        "counts": {
            "occupations": len(occupations),
            "skills": len(skills),
            "occupation_skill_relations": len(relations),
            "broader_skill_relations": len(broader),
            "skills_missing_from_api": len(failed),
        },
        "skills_missing_from_api": failed,
    }
    (out_dir / "download_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--groups", nargs="+", default=list(ISCO_GROUPS), choices=list(ISCO_GROUPS))
    args = parser.parse_args()
    result = main(args.out, args.groups)
    print(json.dumps(result["counts"], indent=2))
