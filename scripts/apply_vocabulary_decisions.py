"""
Applies the author's review decisions to data/vocabulary/aliases.csv and
data/vocabulary/area_esco_map.csv. This is the only script that sets
`status = accepted` or fills `selected`.

Decisions file (CSV) columns:
    scope      "area" or "alias"
    area_id    area number
    alias      alias text (alias rows only; matched case-insensitively)
    decision   area rows:  approve_proposed | select
               alias rows: accepted | rejected | pending_review
    esco_uri   optional; for "select", the occupation to select; for "accepted"
               in an area with several selected occupations, which one applies
    notes      optional; appended to the alias row's notes
    kg_included  optional; yes | no | undecided. yes/no only with decision
               = accepted (no = held out of the KG); blank leaves it unchanged

Area rows are applied first and replace the area's selection: approve_proposed
copies `proposed` into `selected`; select marks one candidate row.

Alias rows set status and (if given) kg_included. Accepted and rejected rows
are stamped with validated_by and decision_date; pending_review clears both.
On accepted, the script also copies proposed_sense_ok into sense_ok and sets
esco_uri/esco_label from
the area's selected occupation; it refuses if the area has no selected
occupation, or several and the row names none of them. On rejected, register
becomes "rejected" (the old register is kept in notes) and a reason is needed,
in the row's notes or already in the alias notes.

Every row is validated before anything is written; on any error nothing changes.
Rows are never added or deleted.

Usage: python scripts/apply_vocabulary_decisions.py --decisions FILE
                 [--validated-by author] [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ALIASES = REPO_ROOT / "data/vocabulary/aliases.csv"
AREA_MAP = REPO_ROOT / "data/vocabulary/area_esco_map.csv"

AREA_DECISIONS = {"approve_proposed", "select"}
ALIAS_DECISIONS = {"accepted", "rejected", "pending_review"}
KG_VALUES = {"yes", "no", "undecided", ""}


class DecisionError(ValueError):
    pass


def _read(path: Path) -> tuple[list[str], list[dict]]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader.fieldnames), list(reader)


def _write(path: Path, columns: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _key(text: str) -> str:
    return " ".join(str(text).lower().split())


def apply_decisions(decisions: list[dict], aliases: list[dict], area_map: list[dict],
                    validated_by: str, decision_date: str) -> list[str]:
    """Apply decisions in place to the alias and area-map rows; return a change log.

    Raises DecisionError listing every problem; callers should only write
    files if this returns.
    """
    errors, log = [], []
    area_rows = [d for d in decisions if d.get("scope") == "area"]
    alias_rows = [d for d in decisions if d.get("scope") == "alias"]
    errors += [f"row {i + 2}: unknown scope {d.get('scope')!r}" for i, d in enumerate(decisions)
               if d.get("scope") not in {"area", "alias"}]

    # Area decisions
    seen_areas = set()
    for d in area_rows:
        area, decision = str(d.get("area_id", "")).strip(), d.get("decision", "").strip()
        rows = [r for r in area_map if r["area_id"] == area]
        if not rows:
            errors.append(f"area {area!r}: not in area_esco_map.csv")
            continue
        if area in seen_areas:
            errors.append(f"area {area}: more than one area decision")
            continue
        seen_areas.add(area)
        if decision == "approve_proposed":
            chosen = [r for r in rows if r.get("proposed") == "yes"]
        elif decision == "select":
            chosen = [r for r in rows if r["esco_uri"] == d.get("esco_uri", "").strip() and r["esco_uri"]]
        else:
            errors.append(f"area {area}: decision must be one of {sorted(AREA_DECISIONS)}, got {decision!r}")
            continue
        if not chosen:
            errors.append(f"area {area}: nothing to select for {decision!r}")
            continue
        for r in rows:
            r["selected"] = "yes" if r in chosen else ""
        log.append(f"area {area}: selected {', '.join(r['esco_label'] for r in chosen)}")

    # Alias decisions
    seen_aliases = set()
    for d in alias_rows:
        area, alias, decision = str(d.get("area_id", "")).strip(), _key(d.get("alias", "")), d.get("decision", "").strip()
        label = f"alias {d.get('alias', '')!r} (area {area})"
        if decision not in ALIAS_DECISIONS:
            errors.append(f"{label}: decision must be one of {sorted(ALIAS_DECISIONS)}, got {decision!r}")
            continue
        if (area, alias) in seen_aliases:
            errors.append(f"{label}: more than one decision")
            continue
        seen_aliases.add((area, alias))
        matches = [r for r in aliases if r["area_id"] == area and _key(r["alias"]) == alias]
        if len(matches) != 1:
            errors.append(f"{label}: matches {len(matches)} rows in aliases.csv")
            continue
        row, note = matches[0], d.get("notes", "").strip()
        kg = (d.get("kg_included") or "").strip()
        if kg not in KG_VALUES:
            errors.append(f"{label}: kg_included must be yes, no or undecided, got {kg!r}")
            continue
        if kg in {"yes", "no"} and decision != "accepted":
            errors.append(f"{label}: kg_included={kg} needs decision accepted")
            continue

        if decision == "accepted":
            selected = [r for r in area_map if r["area_id"] == area and r.get("selected") == "yes"]
            if not selected:
                errors.append(f"{label}: area {area} has no selected ESCO occupation")
                continue
            if len(selected) > 1:
                wanted = d.get("esco_uri", "").strip()
                selected = [r for r in selected if r["esco_uri"] == wanted]
                if len(selected) != 1:
                    errors.append(f"{label}: area {area} has several selected occupations; "
                                  "give one of them in esco_uri")
                    continue
            if row.get("proposed_sense_ok", "") not in {"yes", "no", "unclear"}:
                errors.append(f"{label}: no proposed_sense_ok; run scripts/propose_vocabulary_status.py first")
                continue
            row["sense_ok"] = row["proposed_sense_ok"]
            row["esco_uri"], row["esco_label"] = selected[0]["esco_uri"], selected[0]["esco_label"]
        elif decision == "rejected":
            if not note and not row["notes"]:
                errors.append(f"{label}: rejecting needs a reason in notes")
                continue
            if row["register"] != "rejected":
                note = f"{note} Previous register: {row['register']}.".strip()
                row["register"] = "rejected"

        # Only final decisions are stamped; returning an alias to pending clears the stamp.
        stamped = decision in {"accepted", "rejected"}
        row["status"] = decision
        row["validated_by"] = validated_by if stamped else ""
        row["decision_date"] = decision_date if stamped else ""
        if kg:
            row["kg_included"] = kg
        if note:
            row["notes"] = f"{row['notes']} Decision note ({decision_date}): {note}".strip()
        log.append(f"{label}: {decision}")

    if errors:
        raise DecisionError("\n".join(errors))
    return log


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--decisions", type=Path, required=True)
    parser.add_argument("--aliases", type=Path, default=ALIASES)
    parser.add_argument("--area-map", type=Path, default=AREA_MAP)
    parser.add_argument("--validated-by", default="author")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args()

    _, decisions = _read(args.decisions)
    alias_cols, aliases = _read(args.aliases)
    area_cols, area_map = _read(args.area_map)
    counts = (len(aliases), len(area_map))
    log = apply_decisions(decisions, aliases, area_map, args.validated_by, args.date)
    assert (len(aliases), len(area_map)) == counts, "rows must never be added or deleted"
    _write(args.area_map, area_cols, area_map)
    _write(args.aliases, alias_cols, aliases)
    print("\n".join(log))


if __name__ == "__main__":
    main()
