"""scripts/apply_vocabulary_decisions.py on temporary copies (never the committed CSVs)."""

import csv
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "apply_vocabulary_decisions.py"
_spec = importlib.util.spec_from_file_location("apply_vocabulary_decisions", SCRIPT)
apply_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(apply_mod)

ALIAS_COLS = ["area_id", "esco_uri", "esco_label", "alias", "register", "status", "sense_ok",
              "validated_by", "notes", "proposed_sense_ok", "decision_date"]
AREA_COLS = ["area_id", "esco_uri", "esco_label", "selected", "proposed"]


def _aliases():
    return [
        {"area_id": "2", "alias": "fundi bomba", "register": "trade_name", "status": "pending_review",
         "sense_ok": "unclear", "proposed_sense_ok": "yes", "notes": ""},
        {"area_id": "12", "alias": "kinyozi", "register": "trade_name", "status": "pending_review",
         "sense_ok": "unclear", "proposed_sense_ok": "yes", "notes": ""},
        {"area_id": "2", "alias": "plumber", "register": "english_label", "status": "pending_review",
         "sense_ok": "unclear", "proposed_sense_ok": "unclear", "notes": ""},
    ]


def _area_map():
    return [
        {"area_id": "2", "esco_uri": "u:plumber", "esco_label": "plumber", "selected": "", "proposed": "yes"},
        {"area_id": "2", "esco_uri": "u:pipe", "esco_label": "pipe welder", "selected": "", "proposed": ""},
        {"area_id": "12", "esco_uri": "u:barber", "esco_label": "barber", "selected": "", "proposed": "yes"},
        {"area_id": "12", "esco_uri": "u:hair", "esco_label": "hairdresser", "selected": "", "proposed": "yes"},
    ]


def _apply(decisions, aliases=None, area_map=None):
    aliases, area_map = aliases or _aliases(), area_map or _area_map()
    apply_mod.apply_decisions(decisions, aliases, area_map, "author", "2026-10-07")
    return aliases, area_map


def test_area_approval_then_alias_acceptance_in_one_file():
    aliases, area_map = _apply([
        {"scope": "area", "area_id": "2", "decision": "approve_proposed"},
        {"scope": "alias", "area_id": "2", "alias": "Fundi Bomba", "decision": "accepted"},
    ])
    assert [r["selected"] for r in area_map[:2]] == ["yes", ""]
    row = aliases[0]
    assert (row["status"], row["validated_by"], row["decision_date"]) == ("accepted", "author", "2026-10-07")
    assert row["sense_ok"] == "yes"  # copied from proposed_sense_ok
    assert (row["esco_uri"], row["esco_label"]) == ("u:plumber", "plumber")


def test_accept_refused_without_selected_esco():
    aliases = _aliases()
    with pytest.raises(apply_mod.DecisionError, match="no selected ESCO occupation"):
        _apply([{"scope": "alias", "area_id": "2", "alias": "fundi bomba", "decision": "accepted"}], aliases)
    assert aliases[0]["status"] == "pending_review"


def test_several_selected_occupations_need_an_esco_uri():
    decisions = [{"scope": "area", "area_id": "12", "decision": "approve_proposed"},
                 {"scope": "alias", "area_id": "12", "alias": "kinyozi", "decision": "accepted"}]
    with pytest.raises(apply_mod.DecisionError, match="give one of them in esco_uri"):
        _apply(decisions)
    decisions[1]["esco_uri"] = "u:barber"
    aliases, _ = _apply(decisions)
    assert aliases[1]["esco_label"] == "barber"


def test_rejection_sets_register_and_keeps_reason():
    aliases, _ = _apply([{"scope": "alias", "area_id": "2", "alias": "plumber", "decision": "rejected",
                          "notes": "English label, not needed"}])
    row = aliases[2]
    assert (row["status"], row["register"]) == ("rejected", "rejected")
    assert "English label, not needed" in row["notes"] and "Previous register: english_label" in row["notes"]


def test_rejection_without_any_reason_is_refused():
    with pytest.raises(apply_mod.DecisionError, match="needs a reason"):
        _apply([{"scope": "alias", "area_id": "2", "alias": "plumber", "decision": "rejected"}])


@pytest.mark.parametrize("decision, message", [
    ({"scope": "alias", "area_id": "2", "alias": "fundi wa ghost", "decision": "accepted"}, "matches 0 rows"),
    ({"scope": "alias", "area_id": "2", "alias": "plumber", "decision": "approved"}, "decision must be one of"),
    ({"scope": "area", "area_id": "99", "decision": "approve_proposed"}, "not in area_esco_map"),
    ({"scope": "everything", "area_id": "2"}, "unknown scope"),
])
def test_invalid_decisions_are_refused(decision, message):
    with pytest.raises(apply_mod.DecisionError, match=message):
        _apply([decision])


def test_duplicate_alias_decisions_are_refused():
    row = {"scope": "alias", "area_id": "2", "alias": "plumber", "decision": "pending_review"}
    with pytest.raises(apply_mod.DecisionError, match="more than one decision"):
        _apply([row, dict(row)])


def _write(path, cols, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=cols)
        writer.writeheader()
        writer.writerows([{c: r.get(c, "") for c in cols} for r in rows])
    return path


def test_cli_writes_nothing_on_error_and_never_changes_row_counts(tmp_path):
    aliases = _write(tmp_path / "aliases.csv", ALIAS_COLS, _aliases())
    area_map = _write(tmp_path / "area_esco_map.csv", AREA_COLS, _area_map())
    before = aliases.read_text(), area_map.read_text()
    bad = _write(tmp_path / "bad.csv", ["scope", "area_id", "alias", "decision"], [
        {"scope": "area", "area_id": "2", "decision": "approve_proposed"},
        {"scope": "alias", "area_id": "2", "alias": "fundi wa ghost", "decision": "accepted"},
    ])
    cmd = [sys.executable, str(SCRIPT), "--aliases", str(aliases), "--area-map", str(area_map), "--date", "2026-10-07"]
    assert subprocess.run(cmd + ["--decisions", str(bad)], capture_output=True).returncode != 0
    assert (aliases.read_text(), area_map.read_text()) == before

    good = _write(tmp_path / "good.csv", ["scope", "area_id", "alias", "decision"], [
        {"scope": "area", "area_id": "2", "decision": "approve_proposed"},
        {"scope": "alias", "area_id": "2", "alias": "fundi bomba", "decision": "accepted"},
    ])
    subprocess.run(cmd + ["--decisions", str(good)], check=True, capture_output=True)
    with open(aliases, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 3 and rows[0]["status"] == "accepted"


def test_kg_included_is_set_only_with_acceptance():
    aliases, _ = _apply([
        {"scope": "area", "area_id": "2", "decision": "approve_proposed"},
        {"scope": "alias", "area_id": "2", "alias": "fundi bomba", "decision": "accepted", "kg_included": "no"},
        {"scope": "alias", "area_id": "2", "alias": "plumber", "decision": "pending_review"},
    ])
    assert aliases[0]["kg_included"] == "no"
    assert "kg_included" not in aliases[2] or aliases[2]["kg_included"] in {"", "undecided"}
    with pytest.raises(apply_mod.DecisionError, match="needs decision accepted"):
        _apply([{"scope": "alias", "area_id": "2", "alias": "plumber", "decision": "rejected",
                 "notes": "x", "kg_included": "yes"}])
    with pytest.raises(apply_mod.DecisionError, match="kg_included must be"):
        _apply([{"scope": "alias", "area_id": "2", "alias": "plumber", "decision": "pending_review",
                 "kg_included": "maybe"}])


def test_only_final_decisions_are_stamped():
    aliases = _aliases()
    aliases[2].update(validated_by="author", decision_date="2026-10-01")
    aliases, _ = _apply([{"scope": "alias", "area_id": "2", "alias": "plumber", "decision": "pending_review",
                          "notes": "keep for now"}], aliases)
    row = aliases[2]
    assert (row["status"], row["validated_by"], row["decision_date"]) == ("pending_review", "", "")
    assert "keep for now" in row["notes"]
