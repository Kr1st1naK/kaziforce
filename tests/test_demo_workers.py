"""The demo workers: made up, in the 700 000 0xx range, and at least two each in carpenter, electrician and cook."""

import collections

from kaziforce_api.data.demo import DEMO_PIN, DEMO_WORKERS


def test_every_demo_number_is_in_the_made_up_range_and_unique():
    phones = [w.phone for w in DEMO_WORKERS]
    assert len(set(phones)) == len(phones)
    assert all(p.startswith("7000000") and len(p) == 9 for p in phones)
    assert len({w.worker_id for w in DEMO_WORKERS}) == len(DEMO_WORKERS)
    assert DEMO_PIN == "4821"


def test_the_first_three_are_the_plumbers_the_end_to_end_tests_rely_on():
    assert [w.phone for w in DEMO_WORKERS[:3]] == ["700000001", "700000002", "700000003"]
    assert {w.trade for w in DEMO_WORKERS[:3]} == {"plumber"}


def test_carpenter_electrician_and_cook_each_have_at_least_two():
    per_trade = collections.Counter(w.trade for w in DEMO_WORKERS)
    for trade in ("plumber", "carpenter", "electrician", "cook"):
        assert per_trade[trade] >= 2, trade


def test_each_demo_worker_names_their_trade_in_a_word_the_vocabulary_maps():
    words = {"plumber": "fundi bomba", "carpenter": "fundi wa mbao", "electrician": "fundi wa umeme", "cook": "mpishi"}
    for w in DEMO_WORKERS:
        assert words[w.trade] in w.skills, w
