"""
Builds the committed ESCO subset that the knowledge graph is built from
(data/kg/), so the graph can be rebuilt from a fresh clone and in CI without
the gitignored ESCO download.

Scope: the 11 ESCO occupations selected for the 10 shortlisted areas
(data/vocabulary/area_esco_map.csv), their essential and optional skills
(data/raw/synthetic/inputs/area_skill_pools.csv), and one hop of the ESCO
skill hierarchy (each skill's broader skill group or ISCED-F knowledge field).

Inputs (read-only):
    data/vocabulary/area_esco_map.csv
    data/raw/synthetic/inputs/area_skill_pools.csv
    data/raw/esco/ (from scripts/download_esco.py): occupations, skills, broader relations
Outputs (committed), with no area columns: area is the evaluation label space
and must not reach the graph.
    data/kg/occupations.csv          uri, label, isco_code
    data/kg/occupation_broader.csv   occupation_uri, broader_uri (from ESCO code prefixes)
    data/kg/skills.csv               uri, label, skill_type, reuse_level
    data/kg/occupation_skills.csv    occupation_uri, relation (essential/optional), skill_uri
    data/kg/skill_broader.csv        skill_uri, broader_uri
    data/kg/skill_groups.csv         uri, label, scheme (esco_skill_group / isced_f), label_source
    data/kg/manifest.json            sources, dates, counts, sha256 of inputs and outputs

The ESCO subset download does not include the broader concepts themselves, so
their labels come from a one-time ESCO API fetch (resource/concept). Once
skill_groups.csv exists it is reused; pass --refetch to call the API again.

Usage: python scripts/build_kg_inputs.py [--refetch]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
AREA_MAP = REPO_ROOT / "data/vocabulary/area_esco_map.csv"
POOLS = REPO_ROOT / "data/raw/synthetic/inputs/area_skill_pools.csv"
ESCO_DIR = REPO_ROOT / "data/raw/esco"
OUT = REPO_ROOT / "data/kg"
FALLBACK_VERSION = "v1.2.1"


def read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scheme_of(uri: str) -> str:
    return "isced_f" if "/isced-f/" in uri else "esco_skill_group"


def occupation_broader(occupations: list[dict]) -> list[dict]:
    """Nearest selected occupation whose ESCO code is a proper dotted prefix (barber 5141.1.1 -> hairdresser 5141.1)."""
    rows = []
    for o in occupations:
        parents = [p for p in occupations if o["isco_code"].startswith(p["isco_code"] + ".")]
        if parents:
            parent = max(parents, key=lambda p: len(p["isco_code"]))
            rows.append({"occupation_uri": o["uri"], "broader_uri": parent["uri"]})
    return rows


def fetch_group_labels(uris: list[str]) -> list[dict]:
    """English labels from the API's default version. Some skill groups make the default version
    fail with HTTP 500 ("More than one value found for field 'hasSkillType'"); those fall back to
    the pinned FALLBACK_VERSION, and label_source records which one answered."""
    from download_esco import get_json  # scripts/ is on sys.path when run as a script

    rows = []
    for n, uri in enumerate(uris, start=1):
        params = [("uri", uri), ("language", "en")]
        try:
            concept, source = get_json("resource/concept", params, retries=2), "default"
        except RuntimeError:
            concept = get_json("resource/concept", params + [("selectedVersion", FALLBACK_VERSION)])
            source = FALLBACK_VERSION
        label = (concept.get("preferredLabel") or {}).get("en") or concept.get("title") or ""
        if not label:
            raise RuntimeError(f"ESCO API returned no English label for {uri}")
        rows.append({"uri": uri, "label": label, "scheme": scheme_of(uri), "label_source": source})
        if n % 20 == 0 or n == len(uris):
            print(f"  labels {n}/{len(uris)}")
    return rows


def main(refetch: bool) -> dict:
    selected = [r for r in read_csv(AREA_MAP) if r["selected"] == "yes" and r["shortlisted"] == "yes"]
    selected_uris = {r["esco_uri"] for r in selected}
    esco_occ = {r["conceptUri"]: r for r in read_csv(ESCO_DIR / "occupations_en.csv")}
    occupations = sorted(({"uri": u, "label": esco_occ[u]["preferredLabel"], "isco_code": esco_occ[u]["code"]}
                          for u in selected_uris), key=lambda o: o["isco_code"])

    pools = [p for p in read_csv(POOLS) if p["esco_uri"] in selected_uris]
    occ_skills = sorted(({"occupation_uri": p["esco_uri"], "relation": p["relation"], "skill_uri": p["skill_uri"]}
                         for p in pools), key=lambda r: (r["occupation_uri"], r["relation"], r["skill_uri"]))

    esco_skills = {r["conceptUri"]: r for r in read_csv(ESCO_DIR / "skills_en.csv")}
    pool_labels = {p["skill_uri"]: p["skill_label"] for p in pools}
    skills = []
    for uri in sorted(pool_labels):
        s = esco_skills[uri]
        if s["preferredLabel"] != pool_labels[uri]:
            raise ValueError(f"label mismatch for {uri}: pools {pool_labels[uri]!r} vs ESCO {s['preferredLabel']!r}")
        skills.append({"uri": uri, "label": s["preferredLabel"], "skill_type": s["skillType"],
                       "reuse_level": s["reuseLevel"]})

    broader = sorted(({"skill_uri": r["conceptUri"], "broader_uri": r["broaderUri"]}
                      for r in read_csv(ESCO_DIR / "broaderRelationsSkillPillar_en.csv") if r["conceptUri"] in pool_labels),
                     key=lambda r: (r["skill_uri"], r["broader_uri"]))
    group_uris = sorted({r["broader_uri"] for r in broader})

    OUT.mkdir(parents=True, exist_ok=True)
    groups_path = OUT / "skill_groups.csv"
    fetched_at = None
    if refetch or not groups_path.exists():
        print(f"Fetching labels for {len(group_uris)} broader concepts from the ESCO API")
        groups = fetch_group_labels(group_uris)
        fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    else:
        groups = read_csv(groups_path)
        missing = set(group_uris) - {g["uri"] for g in groups}
        if missing:
            raise ValueError(f"{len(missing)} broader concepts lack labels; run with --refetch")
        groups = [g for g in groups if g["uri"] in set(group_uris)]

    outputs = {
        "occupations.csv": (occupations, ["uri", "label", "isco_code"]),
        "occupation_broader.csv": (occupation_broader(occupations), ["occupation_uri", "broader_uri"]),
        "skills.csv": (skills, ["uri", "label", "skill_type", "reuse_level"]),
        "occupation_skills.csv": (occ_skills, ["occupation_uri", "relation", "skill_uri"]),
        "skill_broader.csv": (broader, ["skill_uri", "broader_uri"]),
        "skill_groups.csv": (sorted(groups, key=lambda g: g["uri"]), ["uri", "label", "scheme", "label_source"]),
    }
    for name, (rows, columns) in outputs.items():
        write_csv(OUT / name, rows, columns)

    manifest_path = OUT / "manifest.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    esco_download = json.loads((ESCO_DIR / "download_manifest.json").read_text())
    manifest = {
        "builder": "scripts/build_kg_inputs.py",
        "esco": {"source": esco_download["source"], "language": esco_download["language"],
                 "subset_downloaded_at": esco_download["downloaded_at"],
                 "broader_labels_source": f"{esco_download['source']}/resource/concept",
                 "broader_labels_fetched_at": fetched_at or previous.get("esco", {}).get("broader_labels_fetched_at"),
                 "broader_labels_fallback_version": FALLBACK_VERSION,
                 "broader_labels_from_fallback": sum(g["label_source"] != "default" for g in groups)},
        "counts": {name: len(rows) for name, (rows, _) in outputs.items()},
        "inputs_sha256": {"area_esco_map.csv": sha256(AREA_MAP), "area_skill_pools.csv": sha256(POOLS)},
        "outputs_sha256": {name: sha256(OUT / name) for name in outputs},
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--refetch", action="store_true", help="fetch broader-concept labels from the ESCO API again")
    print(json.dumps(main(parser.parse_args().refetch)["counts"], indent=2))
