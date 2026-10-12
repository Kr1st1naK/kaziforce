"""
Maps the 20 informal-trade areas in data/vocabulary/README.md to ESCO
occupations in the local subset (data/raw/esco/, see scripts/download_esco.py).

Match rule: an occupation matches an area when one of the area's English names
equals the occupation's preferredLabel ("exact_preferred") or one of its
altLabels ("exact_alt"), case-insensitive with hyphens read as spaces. Area
names come from the README table, split on "/"; elliptical names are expanded
via NAME_EXPANSIONS. Occupations whose labels only contain an area keyword are
listed as "related" for context; they are not matches.

No candidate is chosen here: areas with several matches stay "multiple". The
manual columns `shortlisted`, `proposed`, `proposed_reason` and `selected` are
filled outside this script (proposals by Claude, `selected` by the author) and
are carried over from the existing CSV when it is regenerated.

Outputs (committed):
    data/vocabulary/area_esco_map.csv   one row per (area, candidate occupation)

Usage: python scripts/map_vocabulary_areas.py [--print-summary]
"""

from __future__ import annotations

import argparse
import re
from itertools import combinations
from pathlib import Path

import pandas as pd

from kaziforce_api.data.loaders import ESCO_DIR, VOCABULARY_DIR, load_esco_data

README = VOCABULARY_DIR / "README.md"
OUT = VOCABULARY_DIR / "area_esco_map.csv"

# "Mason / bricklayer" reads as two names, but "Cook / catering worker" means
# "cook" and "catering worker"; only areas whose split is not literal are listed.
NAME_EXPANSIONS: dict[str, list[str]] = {
    "Appliance / electronics repairer": ["appliance repairer", "electronics repairer"],
    "Gardener / grounds worker": ["gardener", "grounds worker"],
    "Delivery / courier worker": ["delivery worker", "courier worker"],
    "General construction / maintenance worker": [
        "general construction worker", "general maintenance worker",
    ],
}

# Context only ("related" rows): label substrings per area_id.
RELATED_KEYWORDS: dict[int, str] = {
    1: r"electrician", 2: r"plumb", 3: r"carpent|joiner", 4: r"mason|brick",
    5: r"paint", 6: r"weld", 7: r"mechanic", 8: r"motorcycle|motorbike",
    9: r"applian|electronic", 10: r"mobile phone|mobile device", 11: r"tailor|dressmak|seamst",
    12: r"hairdress|barber|hair stylist", 13: r"beaut", 14: r"domestic|house ?clean|housekeep",
    15: r"laund", 16: r"\bcook|cater", 17: r"garden|groundsman|grounds ",
    18: r"\bdriver|chauffeur", 19: r"deliver|courier", 20: r"construction worker|maintenance worker|builder",
}

COLUMNS = [
    "area_id", "area", "mapping_status", "exact_match_count", "match_type",
    "esco_uri", "esco_label", "isco_code", "esco_vocabulary_area", "matched_label", "selected",
    "shortlisted", "proposed", "proposed_reason",
]
MANUAL_ROW_COLUMNS = ["selected", "proposed", "proposed_reason"]  # keyed on area_id + esco_uri
MANUAL_AREA_COLUMNS = ["shortlisted"]  # keyed on area_id


def _norm(label: str) -> str:
    return re.sub(r"[\s\-]+", " ", str(label).lower()).strip()


def read_areas(readme: Path = README) -> dict[int, str]:
    """Parse `| # | Occupational area | ... |` rows from the vocabulary README."""
    areas = {}
    for line in readme.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0].isdigit():
            areas[int(cells[0])] = cells[1]
    return areas


def area_names(area: str) -> list[str]:
    return NAME_EXPANSIONS.get(area) or [_norm(n) for n in area.split("/")]


def _labels(row) -> list[str]:
    alts = row["altLabels"] if isinstance(row["altLabels"], str) else ""
    return [_norm(row["preferredLabel"])] + [_norm(a) for a in alts.split("\n") if a.strip()]


def build_map(occupations: pd.DataFrame, areas: dict[int, str]) -> pd.DataFrame:
    occ = occupations.assign(labels=occupations.apply(_labels, axis=1))
    rows = []
    for area_id, area in areas.items():
        names = area_names(area)
        exact, related = [], []
        for _, o in occ.iterrows():
            hit = [n for n in names if n in o["labels"]]
            if hit:
                pref = _norm(o["preferredLabel"])
                kind = "exact_preferred" if pref in names else "exact_alt"
                exact.append((kind, o, pref if pref in names else hit[0]))
            else:
                rel = [lab for lab in o["labels"] if re.search(RELATED_KEYWORDS[area_id], lab)]
                if rel:
                    related.append(("related", o, rel[0]))
        n = len(exact)
        status = "none" if n == 0 else "single" if n == 1 else "multiple"
        for kind, o, matched in exact + related:
            rows.append({
                "area_id": area_id, "area": area, "mapping_status": status,
                "exact_match_count": n, "match_type": kind,
                "esco_uri": o["conceptUri"], "esco_label": o["preferredLabel"],
                "isco_code": o["code"], "esco_vocabulary_area": o["vocabularyArea"],
                "matched_label": matched, "selected": "",
            })
        if not exact and not related:
            rows.append({"area_id": area_id, "area": area, "mapping_status": status,
                         "exact_match_count": 0, "match_type": "", "selected": ""})
    order = {"exact_preferred": 0, "exact_alt": 1, "related": 2, "": 3}
    df = pd.DataFrame(rows, columns=COLUMNS)
    return df.sort_values(
        ["area_id", "match_type", "isco_code"], key=lambda s: s.map(order) if s.name == "match_type" else s
    ).reset_index(drop=True)


def carry_over_manual_columns(new: pd.DataFrame, old: pd.DataFrame) -> pd.DataFrame:
    """Copy manual columns from a previous area_esco_map.csv into a regenerated one."""
    new = new.copy()
    new[MANUAL_ROW_COLUMNS + MANUAL_AREA_COLUMNS] = ""
    old = old.astype(str).replace("nan", "")
    row_key = list(zip(new["area_id"].astype(str), new["esco_uri"].fillna("").astype(str)))
    for col in MANUAL_ROW_COLUMNS:
        if col in old:
            values = dict(zip(zip(old["area_id"], old["esco_uri"]), old[col]))
            new[col] = [values.get(k, "") for k in row_key]
    for col in MANUAL_AREA_COLUMNS:
        if col in old:
            values = old.drop_duplicates("area_id").set_index("area_id")[col].to_dict()
            new[col] = new["area_id"].astype(str).map(values).fillna("")
    return new


def skill_summary(area_map: pd.DataFrame, relations: pd.DataFrame) -> pd.DataFrame:
    """Essential-skill overlap between areas, for the shortlist (not a mapping decision).

    Each area uses its exact_preferred matches, else all exact matches; areas
    with no exact match are skipped.
    """
    essential = relations[relations["relationType"] == "essential"]
    skills_of = essential.groupby("occupationUri")["skillUri"].apply(set).to_dict()
    area_skills = {}
    for area_id, g in area_map[area_map["match_type"].str.startswith("exact")].groupby("area_id"):
        pref = g[g["match_type"] == "exact_preferred"]
        uris = (pref if len(pref) else g)["esco_uri"]
        area_skills[area_id] = set().union(*(skills_of.get(u, set()) for u in uris))
    rows = {a: {"area_id": a, "essential_skills": len(s), "max_jaccard": 0.0,
                "nearest_area": None, "shared_with_nearest": 0} for a, s in area_skills.items()}
    for a, b in combinations(area_skills, 2):
        sa, sb = area_skills[a], area_skills[b]
        j = len(sa & sb) / len(sa | sb) if sa | sb else 0.0
        for x, y in ((a, b), (b, a)):
            if j > rows[x]["max_jaccard"]:
                rows[x].update(max_jaccard=round(j, 3), nearest_area=y, shared_with_nearest=len(sa & sb))
    return pd.DataFrame(rows.values()).sort_values("area_id")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--esco-dir", type=Path, default=ESCO_DIR)
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--print-summary", action="store_true")
    args = parser.parse_args()

    esco = load_esco_data(args.esco_dir)
    area_map = build_map(esco["occupations"], read_areas())
    old = pd.read_csv(args.out, dtype=str) if args.out.exists() else pd.DataFrame(columns=COLUMNS)
    area_map = carry_over_manual_columns(area_map, old)
    area_map.to_csv(args.out, index=False)
    status = area_map.drop_duplicates("area_id")[["area_id", "area", "mapping_status", "exact_match_count"]]
    print(status.to_string(index=False))
    if args.print_summary:
        print(skill_summary(area_map, esco["occupation_skill_relations"]).to_string(index=False))


if __name__ == "__main__":
    main()
