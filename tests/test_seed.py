"""skill_rows(): how listed skills are described in the database (no database needed)."""

from kaziforce_api.data.data_loader import DataLoader
from kaziforce_api.data.models import JobPosting, WorkerProfile
from kaziforce_api.data.seed import SkillRow, skill_rows

ELECTRICIAN = "http://data.europa.eu/esco/occupation/4910419f-b4af-4f59-b544-9dbebc8a74f0"


def _rows(worker_skills, job_skills=()):
    w = WorkerProfile("w", "bio", tuple(worker_skills), None, None, None)
    j = JobPosting("j", "", "", tuple(job_skills), None, None, None)
    return {r.skill_name: r for r in skill_rows([w], [j])}


def test_esco_labels_informal_terms_and_text_are_described():
    rows = _rows(["fundi wa umeme", "install electricity sockets", "fundi wa stima", "mshonaji"], ["Excel", "excel"])
    assert rows["fundi wa umeme"] == SkillRow("fundi wa umeme", ELECTRICIAN, True)
    assert rows["install electricity sockets"].esco_code.startswith("http://data.europa.eu/esco/skill/")
    assert rows["install electricity sockets"].is_informal_term is False
    assert rows["Excel"] == SkillRow("Excel", None, False) and "excel" in rows  # case kept: exact round trip


def test_withheld_aliases_are_informal_but_map_to_nothing():
    rows = _rows(["fundi wa stima", "mshonaji"])
    assert all(r.is_informal_term and r.esco_code is None for r in rows.values())


def test_each_distinct_string_once_in_first_seen_order():
    names = [r.skill_name for r in skill_rows(
        [WorkerProfile("a", "", ("b", "a"), None, None, None), WorkerProfile("c", "", ("a",), None, None, None)],
        [JobPosting("j", "", "", ("c", "b"), None, None, None)])]
    assert names == ["b", "a", "c"]


def test_the_development_dataset_needs_one_row_per_distinct_string():
    loader = DataLoader()
    workers, jobs = loader.workers("development"), loader.jobs()
    rows = skill_rows(workers, jobs)
    distinct = {s for w in workers for s in w.skills} | {s for j in jobs for s in j.required_skills}
    assert {r.skill_name for r in rows} == distinct and len(rows) == len(distinct)
    assert max(len(r.skill_name) for r in rows) <= 255
