"""
Proposes a review outcome for every alias in data/vocabulary/aliases.csv. It
never sets `status`, `sense_ok`, `kg_included` or `selected`; those are the
author's (see scripts/apply_vocabulary_decisions.py).

Columns written: proposed_sense_ok, proposed_status, confidence, proposed_reason,
and a "[sense basis: ...]" note appended to `notes` (replaced on re-run).

proposed_sense_ok, judged only from a dictionary entry for the WHOLE alias
(the phrase, or the word for single-word aliases) in either source:
    yes      an English gloss names the area's occupation (AREA_OCCUPATION)
    no       the entry exists and has glosses, but none names that occupation
    unclear  no whole-alias entry, or an entry without English glosses

Effective sense = sense_ok if the author set yes/no, else proposed_sense_ok.

Rules, applied in order (first match wins):
  1. recommend_reject (high)
       status = rejected (author decision); or dictionary_check = not_found and
       no component is found; or effective sense = no.
  2. needs_human
       register is not trade_name; or the area is not shortlisted; or the alias
       has no single ESCO occupation (area has no selected/proposed occupation,
       or several and the alias's glosses do not pick one); or the whole-alias
       glosses also name another area's occupation (e.g. mama fua).
  3. recommend_accept (high)
       trade_name, found_exact and effective sense = yes.
  4. recommend_accept (medium)
       trade_name, found_components, and every complement's glosses match the
       area's domain keywords (AREA_DOMAIN).
  5. needs_human: everything else.
Accept proposals that rely on Claude's proposed (not author-selected) ESCO
occupation say so in proposed_reason.

Needs the local dictionary caches (see check_vocabulary_dictionary.py).

Usage: python scripts/propose_vocabulary_status.py [--sheet]
"""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from check_vocabulary_dictionary import Sources, gather  # scripts/ is on sys.path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALIASES = REPO_ROOT / "data/vocabulary/aliases.csv"
AREA_MAP = REPO_ROOT / "data/vocabulary/area_esco_map.csv"
SHEET = REPO_ROOT / "docs/vocabulary-review-sheet.md"

HELD_OUT_CANDIDATES = {"fundi wa stima", "fundi seremala"}  # author decision 2026-10-05
HELD_OUT_CAVEATS = {  # quality of the usage evidence in data/vocabulary/usage_evidence.csv
    "fundi wa stima": "video and social-media titles only, origin not stated",
    "fundi seremala": "both sources are Tanzanian, not Kenyan",
}

# English gloss naming the area's occupation (used for proposed_sense_ok and cross-area checks).
AREA_OCCUPATION = {
    1: r"electrician", 2: r"plumber", 3: r"carpenter|joiner", 4: r"mason|bricklayer",
    5: r"\bpainter", 6: r"welder", 7: r"mechanic", 8: r"motorcycle mechanic",
    9: r"repairer|repairman", 10: r"phone repair", 11: r"tailor|dressmaker|seamstress|sewer\b",
    12: r"barber|hair ?dresser|braider", 13: r"beautician", 14: r"(?<!dry )cleaner|cleaning lady|maid|housekeeper",
    15: r"laundr|launderer|washer(wo)?man|dry cleaner", 16: r"\bcook\b|\bchef\b",
    17: r"gardener", 18: r"driver|chauffeur", 19: r"courier|messenger|delivery (man|person|rider)",
    20: r"builder|construction worker|labourer",
}
# Domain words a complement's gloss should contain, e.g. fundi wa umeme -> "electricity".
AREA_DOMAIN = {
    1: r"electric", 2: r"pipe|plumb", 3: r"wood|plank|board|timber|carpent", 4: r"stone|brick|build|mason",
    5: r"paint|colou?r", 6: r"weld|iron|metal", 7: r"\bcar|vehicle|automobile|mechanic",
    8: r"motorcycle", 9: r"device|equipment|appliance|electronic", 10: r"phone",
    11: r"cloth|fabric|garment|sew|tailor", 12: r"hair|barber", 13: r"beaut|ornament|decorat",
    14: r"clean|home|house", 15: r"laund|wash", 16: r"cook|food", 17: r"garden|farm|field",
    18: r"driv", 19: r"deliver|courier", 20: r"build|construct|repair|mainten",
}
SENSE_BASIS_RE = re.compile(r"\s*\[sense basis: [^\]]*\]")


@dataclass
class Evidence:
    """What the rules need about one alias (built from the dictionaries, or by hand in tests)."""
    whole_found: bool = False
    whole_glosses: list[str] = field(default_factory=list)
    any_component_found: bool = False
    complement_glosses: list[list[str]] = field(default_factory=list)  # one list per complement
    shortlisted: bool = False
    esco: list[tuple[str, str, str]] = field(default_factory=list)  # (label, isco_code, source) candidates
    esco_selected_by_author: bool = False


def _matches(pattern: str, glosses: list[str]) -> bool:
    return any(re.search(pattern, g, re.I) for g in glosses)


def proposed_sense(area_id: int | None, ev: Evidence) -> tuple[str, str]:
    if not ev.whole_found or not ev.whole_glosses or area_id is None:
        return "unclear", "no whole-alias dictionary entry with English glosses"
    if _matches(AREA_OCCUPATION[area_id], ev.whole_glosses):
        return "yes", "whole-alias gloss names the area's occupation"
    return "no", "whole-alias entry exists but no gloss names the area's occupation"


def alias_esco(ev: Evidence) -> tuple[str, str, str] | None:
    """The single ESCO candidate for this alias, disambiguating by gloss if the area has several."""
    if len(ev.esco) == 1:
        return ev.esco[0]
    squashed = [g.lower().replace(" ", "") for g in ev.whole_glosses]
    hits = [c for c in ev.esco if any(c[0].replace(" ", "") in g for g in squashed)]
    return hits[0] if len(hits) == 1 else None


def propose(row: dict, ev: Evidence) -> dict:
    """proposed_status, confidence, proposed_reason, proposed_sense_ok for one alias row."""
    area_id = int(row["area_id"]) if row["area_id"] else None
    sense, sense_basis = proposed_sense(area_id, ev)
    effective = row["sense_ok"] if row["sense_ok"] in {"yes", "no"} else sense

    def out(status, confidence, reason):
        return {"proposed_status": status, "confidence": confidence, "proposed_reason": reason,
                "proposed_sense_ok": sense, "_sense_basis": sense_basis}

    # 1. reject
    if row["status"] == "rejected":
        return out("recommend_reject", "high", "Already rejected by author decision")
    if row["dictionary_check"] == "not_found" and not ev.any_component_found:
        return out("recommend_reject", "high", "Not found in either dictionary, nor any component")
    if effective == "no":
        return out("recommend_reject", "high", f"Sense: {sense_basis}")

    # 2. needs_human
    if row["register"] != "trade_name":
        return out("needs_human", "", f"Register is {row['register']}; descriptive and English labels need your judgement")
    if not ev.shortlisted:
        return out("needs_human", "", f"Area {row['area_id']} is not shortlisted")
    esco = alias_esco(ev)
    if esco is None:
        return out("needs_human", "", "No single ESCO occupation for this alias")
    others = [a for a, pat in AREA_OCCUPATION.items() if a != area_id and _matches(pat, ev.whole_glosses)]
    if others:
        return out("needs_human", "", f"Gloss also fits area(s) {', '.join(map(str, others))}")

    esco_note = f"ESCO: {esco[0]} {esco[1]}" + ("" if ev.esco_selected_by_author
                                                 else " (Claude's proposal; needs your confirmation)")
    # 3. accept, high
    if row["dictionary_check"] == "found_exact" and effective == "yes":
        return out("recommend_accept", "high", f"Trade name; whole-alias entry names the occupation. {esco_note}")
    # 4. accept, medium
    if (row["dictionary_check"] == "found_components" and ev.complement_glosses
            and all(_matches(AREA_DOMAIN[area_id], gl) for gl in ev.complement_glosses)):
        return out("recommend_accept", "medium",
                   f"Trade name; all components found and complement glosses fit the area. {esco_note}")
    # 5. everything else
    if row["dictionary_check"] == "found_exact":
        return out("needs_human", "", "Entry found but its sense for this area is unclear")
    return out("needs_human", "", "Components found but their glosses do not clearly fit the area")


# Building evidence from the dictionaries and the area map

def _glosses(results: dict) -> list[str]:
    return [g for r in results.values() if r["result"] != "not_found" for g in r["glosses"]]


def build_evidence(row: dict, sources: Sources, areas: dict) -> Evidence:
    g = gather(row["alias"], sources)
    area = areas.get(row["area_id"], {"shortlisted": False, "esco": [], "by_author": False})
    ev = Evidence(shortlisted=area["shortlisted"], esco=area["esco"], esco_selected_by_author=area["by_author"])
    if g["english_only"]:
        return ev
    ev.whole_found = any(r["result"] != "not_found" for r in g["phrase"].values())
    ev.whole_glosses = _glosses(g["phrase"])
    content = [(role, res) for _, role, res in g["components"] if role in {"head", "complement"}]
    ev.any_component_found = any(r["result"] != "not_found" for _, res in content for r in res.values())
    ev.complement_glosses = [_glosses(res) for role, res in content if role == "complement"]
    return ev


def read_areas(path: Path = AREA_MAP) -> dict[str, dict]:
    """area_id -> {shortlisted, esco: [(label, code, uri)], by_author}; author's `selected` wins over `proposed`."""
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    areas = {}
    for r in rows:
        a = areas.setdefault(r["area_id"], {"shortlisted": r["shortlisted"] == "yes",
                                            "selected": [], "proposed": []})
        cand = (r["esco_label"], r["isco_code"], r["esco_uri"])
        if r["selected"] == "yes":
            a["selected"].append(cand)
        if r["proposed"] == "yes":
            a["proposed"].append(cand)
    return {k: {"shortlisted": v["shortlisted"], "esco": v["selected"] or v["proposed"],
                "by_author": bool(v["selected"])} for k, v in areas.items()}


# Review sheet

GROUPS = [
    ("Accept (high confidence)", lambda r: r["proposed_status"] == "recommend_accept" and r["confidence"] == "high"),
    ("Accept (medium confidence)", lambda r: r["proposed_status"] == "recommend_accept" and r["confidence"] == "medium"),
    ("Needs my judgement", lambda r: r["proposed_status"] == "needs_human"),
    ("Reject", lambda r: r["proposed_status"] == "recommend_reject"),
]


def sheet_line(r: dict) -> str:
    held = ""
    if r["alias"] in HELD_OUT_CANDIDATES:
        eligible = r["usage_evidence_url"] not in {"", "none"}
        caveat = f"; {HELD_OUT_CAVEATS[r['alias']]}" if eligible and r["alias"] in HELD_OUT_CAVEATS else ""
        held = (f" **Held-out candidate: {'eligible' if eligible else 'not eligible'}"
                f" (usage evidence {'found' if eligible else 'none'}{caveat}).**")
    urls = " ".join(f"<{u}>" for u in r["entry_url"].split(" ; ") if u)
    gloss = f"“{r['gloss_note']}”" if r["gloss_note"] else "no gloss (English label)"
    return (f"- **{r['alias']}** (area {r['area_id'] or '–'}; {r['register']}; {r['dictionary_check']}; "
            f"sense {r['proposed_sense_ok']}): {gloss}. {r['proposed_reason']}.{held} {urls}").rstrip()


def write_sheet(rows: list[dict], path: Path = SHEET) -> None:
    lines = [
        "# Vocabulary review sheet",
        "",
        "Generated by `scripts/propose_vocabulary_status.py --sheet` from `data/vocabulary/aliases.csv`.",
        "Every outcome below is a proposal; nothing has been accepted. Glosses are my own short notes;",
        "the links are the dictionary entries behind them. Rules: `docs/vocabulary-report.md` §8.",
        "Record your decisions in a decisions file and apply them with",
        "`scripts/apply_vocabulary_decisions.py`.",
    ]
    for title, keep in GROUPS:
        chosen = sorted((r for r in rows if keep(r)), key=lambda r: (int(r["area_id"] or 99), r["alias"]))
        lines += ["", f"## {title} ({len(chosen)})", ""] + [sheet_line(r) for r in chosen]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--aliases", type=Path, default=ALIASES)
    parser.add_argument("--sheet", action="store_true", help=f"also write {SHEET.relative_to(REPO_ROOT)}")
    args = parser.parse_args()

    sources, areas = Sources(), read_areas()
    with open(args.aliases, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        columns, rows = reader.fieldnames, list(reader)
    for row in rows:
        result = propose(row, build_evidence(row, sources, areas))
        basis = result.pop("_sense_basis")
        row.update(result)
        row["notes"] = (SENSE_BASIS_RE.sub("", row["notes"]) +
                        f" [sense basis: {result['proposed_sense_ok']}, {basis}]").strip()
    with open(args.aliases, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    if args.sheet:
        write_sheet(rows)
    for title, keep in GROUPS:
        print(f"{title}: {sorted(r['alias'] for r in rows if keep(r))}")


if __name__ == "__main__":
    main()
