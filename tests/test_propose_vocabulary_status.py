"""Proposal rules in scripts/propose_vocabulary_status.py (offline, hand-built evidence)."""

import csv
import importlib.util
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))  # the script imports check_vocabulary_dictionary
_spec = importlib.util.spec_from_file_location("propose_vocabulary_status", SCRIPTS / "propose_vocabulary_status.py")
propose_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = propose_mod  # dataclasses resolve annotations through sys.modules
_spec.loader.exec_module(propose_mod)
Evidence, propose = propose_mod.Evidence, propose_mod.propose

ELECTRICIAN = [("electrician", "7411.1", "uri:e")]
HAIR = [("hairdresser", "5141.1", "uri:h"), ("barber", "5141.1.1", "uri:b")]


def _row(alias="fundi wa umeme", area="1", register="trade_name", status="pending_review",
         check="found_components", sense_ok="unclear"):
    return {"alias": alias, "area_id": area, "register": register, "status": status,
            "dictionary_check": check, "sense_ok": sense_ok}


def _ev(**kw):
    base = {"shortlisted": True, "esco": ELECTRICIAN, "any_component_found": True}
    return Evidence(**{**base, **kw})


def test_author_rejection_wins_even_with_a_perfect_entry():
    out = propose(_row(status="rejected", check="found_exact"),
                  _ev(whole_found=True, whole_glosses=["electrician"]))
    assert (out["proposed_status"], out["confidence"]) == ("recommend_reject", "high")


def test_not_found_with_no_component_is_rejected():
    out = propose(_row(check="not_found"), _ev(any_component_found=False))
    assert out["proposed_status"] == "recommend_reject"


def test_author_sense_no_is_rejected():
    out = propose(_row(check="found_exact", sense_ok="no"), _ev(whole_found=True, whole_glosses=["electrician"]))
    assert out["proposed_status"] == "recommend_reject"


def test_entry_that_names_no_worker_is_rejected():
    out = propose(_row(alias="utoaji", check="found_exact"), _ev(whole_found=True, whole_glosses=["withdrawal"]))
    assert out["proposed_status"] == "recommend_reject" and out["proposed_sense_ok"] == "no"


def test_trade_name_with_matching_whole_entry_is_high():
    out = propose(_row(alias="fundi bomba", area="2", check="found_exact"),
                  _ev(whole_found=True, whole_glosses=["plumber"], esco=[("plumber", "7126.8", "u")]))
    assert (out["proposed_status"], out["confidence"], out["proposed_sense_ok"]) == ("recommend_accept", "high", "yes")
    assert "needs your confirmation" in out["proposed_reason"]


def test_author_selected_esco_drops_the_confirmation_note():
    out = propose(_row(alias="fundi bomba", area="2", check="found_exact"),
                  _ev(whole_found=True, whole_glosses=["plumber"], esco=[("plumber", "7126.8", "u")],
                      esco_selected_by_author=True))
    assert "needs your confirmation" not in out["proposed_reason"]


def test_compositional_trade_name_with_fitting_complement_is_medium():
    out = propose(_row(), _ev(complement_glosses=[["lightning", "electricity"]]))
    assert (out["proposed_status"], out["confidence"]) == ("recommend_accept", "medium")


def test_complement_that_does_not_fit_needs_human():
    out = propose(_row(alias="fundi wa nguo"), _ev(complement_glosses=[["cloth"]]))
    assert out["proposed_status"] == "needs_human" and out["confidence"] == ""


def test_descriptive_register_needs_human():
    out = propose(_row(register="descriptive"), _ev(complement_glosses=[["electricity"]]))
    assert out["proposed_status"] == "needs_human"


def test_area_not_shortlisted_needs_human():
    out = propose(_row(alias="dereva", area="18", check="found_exact"),
                  _ev(shortlisted=False, whole_found=True, whole_glosses=["driver"]))
    assert out["proposed_status"] == "needs_human" and "not shortlisted" in out["proposed_reason"]


def test_gloss_fitting_two_areas_needs_human():
    out = propose(_row(alias="mama fua", area="15", check="found_exact"),
                  _ev(whole_found=True, whole_glosses=["cleaning lady, laundry lady"],
                      esco=[("laundry worker", "8157.1", "u")]))
    assert out["proposed_status"] == "needs_human" and "14" in out["proposed_reason"]


def test_several_esco_candidates_are_disambiguated_by_gloss():
    barber = propose(_row(alias="kinyozi", area="12", check="found_exact"),
                     _ev(whole_found=True, whole_glosses=["barber (haircutting profession)"], esco=HAIR))
    hairdresser = propose(_row(alias="msusi", area="12", check="found_exact"),
                          _ev(whole_found=True, whole_glosses=["hair dresser"], esco=HAIR))
    assert "barber 5141.1.1" in barber["proposed_reason"]
    assert "hairdresser 5141.1" in hairdresser["proposed_reason"]


def test_no_esco_candidate_needs_human():
    out = propose(_row(), _ev(esco=[], complement_glosses=[["electricity"]]))
    assert out["proposed_status"] == "needs_human" and "ESCO" in out["proposed_reason"]


def test_committed_proposals_respect_author_rejections():
    with open(SCRIPTS.parent / "data/vocabulary/aliases.csv", newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert all(r["proposed_status"] == "recommend_reject" for r in rows if r["status"] == "rejected")
    assert all(r["status"] != "accepted" for r in rows)
    assert all(r["confidence"] == "" for r in rows if r["proposed_status"] == "needs_human")
