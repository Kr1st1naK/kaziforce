"""Swahili Wiktionary parsing and combined dictionary_check in scripts/check_vocabulary_dictionary.py."""

import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "check_vocabulary_dictionary",
    Path(__file__).resolve().parents[1] / "scripts" / "check_vocabulary_dictionary.py",
)
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

SW_PAGE = """=={{sw}}==

===Nomino===
{{infl|sw|nomino||wingi|madobi}}

# [[mtu]] anayeosha nguo

==Tafsiri==
*{{tafs|en}}: {{t|en|dry cleaner}}, [[launderer]]

=={{en}}==
===Nomino===
*{{tafs|en}}: {{t|en|not swahili}}
"""


def test_parse_sw_page_keeps_level2_tafsiri_inside_swahili_section():
    parsed = check.parse_sw_page(SW_PAGE)
    assert parsed == {"pos": ["nomino"], "english": ["dry cleaner", "launderer"]}


def test_parse_sw_page_accepts_header_variants():
    assert check.parse_sw_page("=={{-|sw}}==\n===nomino===\n") == {"pos": ["nomino"], "english": []}
    assert check.parse_sw_page("===Kiswahili===\n===Nomino===\n")["pos"] == ["nomino"]


def test_parse_sw_page_rejects_pages_without_swahili_section():
    assert check.parse_sw_page("==Kiyoruba==\n=== Kitenzi ===\n* {{en}}: [[locate]]\n") is None
    assert check.parse_sw_page("=={{en}}==\n===Nomino===\n# mtu\n") is None


def _res(found, url=""):
    return {**check.NOT_FOUND, "result": "headword" if found else "not_found", "url": url}


def _both(kaikki, sw):
    return {"kaikki_en": kaikki, "sw_wiktionary": sw}


def test_summarise_combines_sources():
    g = {"english_only": False, "multiword": True,
         "phrase": _both(_res(False), _res(False)),
         "components": [("fundi", "head", _both(_res(True, "k/fundi"), _res(True, "s/fundi"))),
                        ("wa", "function_word", _both(_res(False), _res(False))),
                        ("kuchomelea", "complement", _both(_res(False), _res(True, "s/kuchomelea")))]}
    out = check.summarise(g)
    assert out["dictionary_check"] == "found_components"
    assert out["entry_url"] == "k/fundi ; s/fundi ; s/kuchomelea"


def test_summarise_phrase_in_one_source_is_found_exact():
    g = {"english_only": False, "multiword": True,
         "phrase": _both(_res(False), _res(True, "s/fundi_wa_nguo")), "components": []}
    assert check.summarise(g)["dictionary_check"] == "found_exact"


def test_summarise_missing_component_is_not_found():
    g = {"english_only": False, "multiword": False, "phrase": _both(_res(False), _res(False)),
         "components": [("mtambuzaji", "head", _both(_res(False), _res(False)))]}
    assert check.summarise(g)["dictionary_check"] == "not_found"
