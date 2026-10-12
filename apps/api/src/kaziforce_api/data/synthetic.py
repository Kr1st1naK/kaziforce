"""
Synthetic worker profiles, job postings and ground truth for the shortlisted
informal-trade areas (DR-05, DR-07; sprint plan S2-6 to S2-8).

Inputs (all committed, read-only here):
    data/vocabulary/aliases.csv           accepted aliases; kg_included=yes are "known",
                                          kg_included=no are "held out"
    data/vocabulary/area_esco_map.csv     shortlisted areas and their selected ESCO occupations
    data/raw/synthetic/inputs/area_skill_pools.csv
                                          essential/optional ESCO skills per selected
                                          occupation (built from the ESCO subset by
                                          build_skill_pools)

Pipeline (build_dataset), in this order:
    1. Base workers: one group per base profile (group_id, base occupation,
       4-6 essential + 0-2 optional/shared skills, location, availability,
       rate, experience).
    2. Split groups development/validation/test, stratified by area, and
       write splits.csv before any text variant exists.
    3. Variants per group: formal; known_alias; held_out (only areas with a
       held-out alias); minimal (known alias + location). known_alias and
       held_out share template and slot values; only the alias differs.
    4. Jobs: formal English with ESCO skill labels, one shared candidate pool
       (workers are queries, jobs are ranked); optional Job Skill Set
       distractors tagged source=job_skill_set.
    5. Ground truth: relevance.csv from the editable compatibility_matrix.csv
       (default: relevant iff same area). Area, occupation, ISCO and ESCO
       fields live only in ground_truth/, never in workers.csv or jobs.csv.

Each stage draws from its own seeded random stream, so editing templates
cannot change base profiles or the split. No real personal identifiers (DR-07).
"""

from __future__ import annotations

import csv
import hashlib
import json
import random
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

GENERATOR_VERSION = 2

LOCATIONS = (
    "Nairobi - Kasarani", "Nairobi - Embakasi", "Nairobi - Westlands", "Nairobi - Kibera",
    "Nairobi - Kawangware", "Nairobi - Githurai", "Nairobi - Umoja", "Nairobi - Rongai",
    "Mombasa - Likoni", "Mombasa - Nyali", "Kisumu", "Nakuru", "Eldoret", "Thika", "Machakos",
    "Kitengela", "Ruiru", "Nyeri", "Kakamega", "Meru",
)
AVAILABILITY = ("Full-time", "Part-time", "Weekends")
AVAILABILITY_SW = {"Full-time": "muda wote", "Part-time": "muda fulani", "Weekends": "wikendi"}
SPLITS = (("development", 0.4), ("validation", 0.2), ("test", 0.4))
VARIANTS = ("formal", "known_alias", "held_out", "minimal")

# Daily rate / budget range in KES per area_id (illustrative).
RATE_RANGE_KES = {
    1: (1500, 3500), 2: (1500, 3000), 3: (1200, 3000), 4: (1000, 2500), 7: (1500, 4000),
    10: (800, 2500), 11: (800, 2000), 12: (500, 1500), 15: (500, 1200), 16: (800, 2000),
}

# Job titles per selected ESCO occupation (formal English).
JOB_TASKS = {
    "electrician": ("House wiring for new rental units", "Repair faulty sockets and lighting",
                    "Install security lights in a compound", "Electrical fault-finding in an office",
                    "Rewire an old shop", "Install a new distribution board"),
    "plumber": ("Repair leaking pipes in an apartment", "Install a water tank and piping",
                "Unblock kitchen and bathroom drains", "Fit new taps and a shower",
                "Connect a borehole pump to a house", "Plumbing for a new bathroom"),
    "carpenter": ("Build kitchen cabinets", "Repair wooden doors and frames", "Make school desks",
                  "Fit wardrobes in a new flat", "Roof timber work for a bungalow", "Build a wooden gate"),
    "bricklayer": ("Build a perimeter wall", "Lay foundation blocks for a house", "Build a septic tank chamber",
                   "Repair a cracked boundary wall", "Build a brick fence", "Extend a single-room house"),
    "vehicle technician": ("Service and repair a saloon car", "Diagnose an engine fault",
                           "Replace brake pads and discs", "Repair a matatu gearbox",
                           "Routine servicing for a fleet of pickups", "Fix vehicle electrical faults"),
    "mobile phone repair technician": ("Replace a cracked smartphone screen", "Repair a phone charging port",
                                       "Fix a phone that will not power on", "Replace a phone battery",
                                       "Repair handsets for a retail shop", "Software repair of handsets"),
    "tailor": ("Tailor school uniforms", "Alter and repair clothing", "Make suits for a wedding party",
               "Sew curtains for a new house", "Make African print outfits", "Produce staff uniforms for a hotel"),
    "barber": ("Haircuts for a staff event", "Home visits for haircuts and shaves", "Barber for a new barbershop",
               "Weekend barber for a busy salon", "Beard trimming and grooming service", "Haircuts for a school"),
    "hairdresser": ("Braiding for a bridal party", "Weekend hairdresser for a salon", "Hair styling for a photo shoot",
                    "Hair treatment and styling at home", "Hairdresser for a new beauty salon", "Hair colouring service"),
    "laundry worker": ("Weekly laundry and ironing", "Laundry for a family of five", "Ironing for a guest house",
                       "Wash and fold service for students", "Laundry for a small hotel", "Hand-wash delicate garments"),
    "cook": ("Cook for a family", "Cook for a school kitchen", "Catering for a wedding",
             "Cook for a small restaurant", "Meal preparation for an office", "Cook for a children's home"),
}

# Worker text templates. Informal templates are shared by known_alias and held_out.
FORMAL_TEMPLATES = (
    "{Title} with {years} years of experience. Skilled in {skills}. Based in {location} and available {avail}.",
    "Experienced {title} ({years} years). Key skills: {skills}. Located in {location}; available {avail}. Day rate KES {rate}.",
    "I am a qualified {title} with {years} years in the trade. My skills include {skills}. I work from {location}, {avail}.",
    "{Title} based in {location}. {years} years of experience in {skills}. Available {avail} at KES {rate} per day.",
    "Professional {title} offering {skills}. {years} years of experience, based in {location}, available {avail}.",
    "{Title}, {years} years of experience. Competent in {skills}. Available {avail} in {location}.",
    "Reliable {title} with {years} years of hands-on experience in {skills}. Based in {location}. Rate KES {rate} per day.",
    "Skilled {title} available {avail} in {location}. Experience: {years} years. Skills: {skills}.",
)
INFORMAL_TEMPLATES = (
    "Mimi ni {alias}, nina uzoefu wa miaka {years}. Napatikana {location}, {avail_sw}.",
    "Habari! Ni {alias} mwenye experience ya miaka {years}. Niko {location}, available {avail_en}. Rate KSh {rate} kwa siku.",
    "{Alias} hapa, {location}. Miaka {years} kazini. Bei yangu KSh {rate} per day, {avail_en}.",
    "Natafuta kazi ya {alias}. Nimefanya kazi miaka {years}, niko {location} {avail_sw}.",
    "Experienced {alias}, {years} yrs. Based {location}. {Avail_en}, KSh {rate} per day.",
    "{Alias} mwaminifu, {location}. Miaka {years} ya kazi, ninapatikana {avail_sw}. KSh {rate} kwa siku.",
    "Niko {location}, ni {alias}. Experience miaka {years}, rates from KSh {rate}.",
    "Hello, {alias} mwenye uzoefu wa {years} years, {location} area. Available {avail_en}.",
    "Kazi zote za {alias}. Uzoefu miaka {years}. Napatikana {location}, {avail_sw}.",
    "Am a {alias} from {location}, {years} years kazini. Available {avail_en}, KSh {rate}.",
)
MINIMAL_TEMPLATES = (
    "{alias}, {location}",
    "{Alias} - {location}",
    "{alias} ({location})",
    "{location}: {alias}",
    "Mimi ni {alias}, {location}",
    "{Alias} hapa {location}",
    "{alias} around {location}",
    "{Alias} niko {location}",
    "{alias} karibu na {location}",
    "{Alias}. {location}",
)
JOB_TEMPLATES = (
    "{task} in {location}. Looking for {article} {title} who can {skills}. {Avail} work; budget KES {budget} per day.",
    "{task}. We need an experienced {title} in {location} to {skills}. Budget: KES {budget} per day ({avail}).",
    "{Article} {title} is required in {location}: {task_lower}. Required skills: {skills}. {Avail}, KES {budget} per day.",
    "Job: {task_lower}, {location}. The {title} should be able to {skills}. Pay KES {budget} per day, {avail}.",
)
TEMPLATE_COUNTS = {"formal": len(FORMAL_TEMPLATES), "known_alias": len(INFORMAL_TEMPLATES),
                   "held_out": len(INFORMAL_TEMPLATES), "minimal": len(MINIMAL_TEMPLATES),
                   "job": len(JOB_TEMPLATES)}


@dataclass
class Occupation:
    uri: str
    label: str
    isco_code: str
    essential: list[str]
    optional: list[str]
    shared: set[str] = field(default_factory=set)  # labels also in another area's pool
    known_aliases: list[str] = field(default_factory=list)
    held_out_aliases: list[str] = field(default_factory=list)


@dataclass
class Area:
    area_id: int
    name: str
    occupations: list[Occupation]


# Inputs

def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_skill_pools(esco: dict, area_map: list[dict]) -> pd.DataFrame:
    """Essential and optional ESCO skills for every selected occupation of a shortlisted area."""
    labels = esco["skills"].set_index("conceptUri")["preferredLabel"].to_dict()
    rel = esco["occupation_skill_relations"]
    rows = []
    for r in area_map:
        if r["selected"] != "yes" or r["shortlisted"] != "yes":
            continue
        for _, s in rel[rel["occupationUri"] == r["esco_uri"]].iterrows():
            if s["skillUri"] in labels:  # a few relations point to skills missing from the subset
                rows.append({"area_id": int(r["area_id"]), "esco_uri": r["esco_uri"], "esco_label": r["esco_label"],
                             "relation": s["relationType"], "skill_uri": s["skillUri"],
                             "skill_label": labels[s["skillUri"]]})
    return (pd.DataFrame(rows).drop_duplicates(["esco_uri", "skill_uri"])
            .sort_values(["area_id", "esco_label", "relation", "skill_label"]).reset_index(drop=True))


def load_inputs(vocab_dir: Path, pools_path: Path) -> dict[int, Area]:
    """Shortlisted areas with their selected occupations, skill pools and accepted aliases."""
    area_map = _read_csv(Path(vocab_dir) / "area_esco_map.csv")
    aliases = [a for a in _read_csv(Path(vocab_dir) / "aliases.csv") if a["status"] == "accepted"]
    pools = _read_csv(pools_path)

    areas: dict[int, Area] = {}
    for r in area_map:
        if r["selected"] == "yes" and r["shortlisted"] == "yes":
            area = areas.setdefault(int(r["area_id"]), Area(int(r["area_id"]), r["area"], []))
            ess = sorted({p["skill_label"] for p in pools if p["esco_uri"] == r["esco_uri"] and p["relation"] == "essential"})
            opt = sorted({p["skill_label"] for p in pools if p["esco_uri"] == r["esco_uri"] and p["relation"] == "optional"})
            area.occupations.append(Occupation(r["esco_uri"], r["esco_label"], r["isco_code"], ess, opt))

    for area in areas.values():
        area.occupations.sort(key=lambda o: o.label)
        other = {p["skill_label"] for p in pools if int(p["area_id"]) != area.area_id}
        for occ in area.occupations:
            occ.shared = (set(occ.essential) | set(occ.optional)) & other
            for a in aliases:
                if a["esco_uri"] == occ.uri:
                    target = occ.known_aliases if a["kg_included"] == "yes" else occ.held_out_aliases
                    if a["kg_included"] in {"yes", "no"}:
                        target.append(a["alias"])
            occ.known_aliases.sort()
            occ.held_out_aliases.sort()
            if len(occ.essential) < 6:
                raise ValueError(f"{occ.label}: fewer than 6 essential skills in {pools_path}")
            if not occ.known_aliases:
                raise ValueError(f"{occ.label} (area {area.area_id}): no accepted kg_included=yes alias; "
                                 "the frozen vocabulary needs a change")
    return dict(sorted(areas.items()))


# Generation

def _uuid(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def make_base_workers(areas: dict[int, Area], seed: int, workers_per_area: int = 12,
                      area_overrides: dict[int, int] | None = None) -> list[dict]:
    """One base profile per group; occupations alternate within multi-occupation areas."""
    rng = random.Random(f"{seed}:base")
    overrides = area_overrides or {}
    base = []
    for area in areas.values():
        lo, hi = RATE_RANGE_KES.get(area.area_id, (800, 2500))
        for i in range(overrides.get(area.area_id, workers_per_area)):
            occ = area.occupations[i % len(area.occupations)]
            essential = rng.sample(occ.essential, rng.randint(4, 6))
            extra_pool = sorted((set(occ.optional) | occ.shared) - set(essential))
            extra = rng.sample(extra_pool, min(rng.randint(0, 2), len(extra_pool)))
            skills = essential + extra
            rng.shuffle(skills)
            base.append({"area_id": area.area_id, "occupation": occ, "skills": skills,
                         "location": rng.choice(LOCATIONS), "availability": rng.choice(AVAILABILITY),
                         "years": rng.randint(1, 20), "rate": rng.randrange(lo, hi + 1, 100)})
    rng.shuffle(base)  # group ids must not reveal the area
    for n, b in enumerate(base, start=1):
        b["group_id"] = f"G{n:04d}"
    return base


def _allocate(n: int, ratios: tuple[tuple[str, float], ...]) -> dict[str, int]:
    """Largest-remainder allocation of n items to named ratios."""
    raw = {name: n * r for name, r in ratios}
    counts = {name: int(v) for name, v in raw.items()}
    for name in sorted(raw, key=lambda k: (counts[k] - raw[k], list(raw).index(k)))[: n - sum(counts.values())]:
        counts[name] += 1
    return counts


def split_groups(base: list[dict], seed: int, ratios=SPLITS) -> dict[str, str]:
    """group_id -> split, stratified by area; groups are never divided."""
    rng = random.Random(f"{seed}:split")
    split_of = {}
    for area_id in sorted({b["area_id"] for b in base}):
        groups = sorted(b["group_id"] for b in base if b["area_id"] == area_id)
        rng.shuffle(groups)
        start = 0
        for name, count in _allocate(len(groups), ratios).items():
            for g in groups[start:start + count]:
                split_of[g] = name
            start += count
    return split_of


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def _render_unique(templates: tuple[str, ...], start: int, slots: list[dict], used: set[str]) -> list[str]:
    """Render with the first template (from `start`) whose output is new for every slot set."""
    for k in range(len(templates)):
        t = templates[(start + k) % len(templates)]
        texts = [t.format(**s) for s in slots]
        if not any(x in used for x in texts) and len(set(texts)) == len(texts):
            used.update(texts)
            return texts
    raise ValueError(f"no unique rendering for {slots[0]}; add templates or slot values")


def make_variants(base: list[dict], seed: int) -> list[dict]:
    """Text variants per base worker. Variants of one group share group_id and slot values."""
    rng = random.Random(f"{seed}:variants")
    used: set[str] = set()
    rows = []
    for b in sorted(base, key=lambda x: x["group_id"]):
        occ, avail = b["occupation"], b["availability"]
        common = {"location": b["location"], "years": b["years"], "rate": b["rate"]}

        formal_slot = {**common, "title": occ.label, "Title": _cap(occ.label),
                       "skills": _join(b["skills"][:4]), "avail": avail.lower()}
        formal = _render_unique(FORMAL_TEMPLATES, rng.randrange(len(FORMAL_TEMPLATES)), [formal_slot], used)[0]
        rows.append({**_row(b, "formal", None), "biography": formal, "skills": list(b["skills"]),
                     "availability": avail, "rate_expectation": b["rate"]})

        known = rng.choice(occ.known_aliases)
        aliases = [known] + ([rng.choice(occ.held_out_aliases)] if occ.held_out_aliases else [])
        informal_slots = [{**common, "alias": a, "Alias": _cap(a), "avail_sw": AVAILABILITY_SW[avail],
                           "avail_en": avail.lower(), "Avail_en": avail} for a in aliases]
        texts = _render_unique(INFORMAL_TEMPLATES, rng.randrange(len(INFORMAL_TEMPLATES)), informal_slots, used)
        for variant, alias, text in zip(("known_alias", "held_out"), aliases, texts):
            rows.append({**_row(b, variant, alias), "biography": text, "skills": [alias],
                         "availability": avail, "rate_expectation": b["rate"]})

        minimal_slot = {"alias": known, "Alias": _cap(known), "location": b["location"]}
        minimal = _render_unique(MINIMAL_TEMPLATES, rng.randrange(len(MINIMAL_TEMPLATES)), [minimal_slot], used)[0]
        rows.append({**_row(b, "minimal", known), "biography": minimal, "skills": [known],
                     "availability": "", "rate_expectation": ""})

    rng.shuffle(rows)
    for r in rows:
        r["worker_id"] = _uuid(rng)
    return rows


def _row(b: dict, variant: str, alias: str | None) -> dict:
    return {"group_id": b["group_id"], "variant": variant, "location": b["location"],
            "_area_id": b["area_id"], "_occupation": b["occupation"], "_alias": alias}


def make_jobs(areas: dict[int, Area], seed: int, jobs_per_area: int = 8) -> list[dict]:
    rng = random.Random(f"{seed}:jobs")
    jobs = []
    for area in areas.values():
        lo, hi = RATE_RANGE_KES.get(area.area_id, (800, 2500))
        for j in range(jobs_per_area):
            occ = area.occupations[j % len(area.occupations)]
            task = rng.choice(JOB_TASKS[occ.label])
            required = rng.sample(occ.essential, rng.randint(3, 5))
            avail, location = rng.choice(AVAILABILITY), rng.choice(LOCATIONS)
            budget = rng.randrange(lo, int(hi * 1.5) + 1, 100)
            article = "an" if occ.label[0] in "aeiou" else "a"
            text = rng.choice(JOB_TEMPLATES).format(
                task=task, task_lower=task[0].lower() + task[1:], location=location, title=occ.label,
                article=article, Article=_cap(article), skills=_join(required[:3]),
                avail=avail.lower(), Avail=avail, budget=budget)
            jobs.append({"title": task, "description": text, "required_skills": required, "budget": budget,
                         "location": location, "availability": avail, "source": "synthetic",
                         "_area_id": area.area_id, "_occupation": occ})
    return jobs


def make_distractors(job_corpus: pd.DataFrame, seed: int, n: int = 200) -> list[dict]:
    """Cleaned Job Skill Set postings: never relevant to any worker."""
    from kaziforce_api.data.loaders import clean_profile_text, clean_text, parse_skill_set

    rng = random.Random(f"{seed}:distractors")
    usable = [r for _, r in job_corpus.iterrows()
              if parse_skill_set(r["job_skill_set"]) and clean_profile_text(r["job_description"])]
    usable.sort(key=lambda r: str(r["job_id"]))
    return [{"title": clean_text(r["job_title"]) or "", "description": clean_profile_text(r["job_description"]),
             "required_skills": parse_skill_set(r["job_skill_set"]), "budget": "", "location": "",
             "availability": "", "source": "job_skill_set", "_area_id": None, "_occupation": None}
            for r in rng.sample(usable, min(n, len(usable)))]


def finalise_jobs(jobs: list[dict], seed: int) -> list[dict]:
    rng = random.Random(f"{seed}:job_ids")
    jobs = list(jobs)
    rng.shuffle(jobs)  # order must not reveal area or source
    for j in jobs:
        j["posting_id"] = _uuid(rng)
    return jobs


# Ground truth

def default_compatibility(areas: dict[int, Area]) -> list[dict]:
    """Relevant iff same area. Hairdresser and barber share area 12, so they are one area."""
    return [{"worker_area_id": a.area_id, "worker_area": a.name, "job_area_id": b.area_id, "job_area": b.name,
             "relevant": int(a.area_id == b.area_id)} for a in areas.values() for b in areas.values()]


def relevance_pairs(workers: list[dict], jobs: list[dict], compatibility: list[dict]) -> list[dict]:
    ok = {(int(c["worker_area_id"]), int(c["job_area_id"])) for c in compatibility if int(c["relevant"]) == 1}
    return [{"worker_id": w["worker_id"], "posting_id": j["posting_id"], "relevance": 1}
            for w in workers for j in jobs
            if j["_area_id"] is not None and (w["_area_id"], j["_area_id"]) in ok]


# Writing

WORKER_COLUMNS = ["worker_id", "group_id", "variant", "biography", "skills", "location", "availability",
                  "rate_expectation"]
JOB_COLUMNS = ["posting_id", "title", "description", "required_skills", "location", "availability", "budget",
               "source"]


def _write(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: json.dumps(r[c], ensure_ascii=False) if isinstance(r[c], list) else r[c] for c in columns})


def build_dataset(out_dir: Path, vocab_dir: Path, pools_path: Path, seed: int = 42, workers_per_area: int = 12,
                  area_overrides: dict[int, int] | None = None, jobs_per_area: int = 8,
                  job_corpus: pd.DataFrame | None = None, n_distractors: int = 200) -> dict:
    """Run the pipeline and write every file under out_dir. Returns the manifest."""
    out_dir = Path(out_dir)
    truth_dir = out_dir / "ground_truth"
    areas = load_inputs(vocab_dir, pools_path)
    overrides = {1: 30, 11: 30} if area_overrides is None else area_overrides

    # 1-2. Base workers and split; splits.csv is written before any variant exists.
    base = make_base_workers(areas, seed, workers_per_area, overrides)
    split_of = split_groups(base, seed)
    _write(out_dir / "splits.csv", [{"group_id": g, "split": split_of[g]} for g in sorted(split_of)],
           ["group_id", "split"])

    # 3. Variants.
    workers = make_variants(base, seed)

    # 4. Jobs (one shared pool) and optional distractors.
    jobs = make_jobs(areas, seed, jobs_per_area)
    if job_corpus is not None and n_distractors:
        jobs += make_distractors(job_corpus, seed, n_distractors)
    jobs = finalise_jobs(jobs, seed)

    # 5. Ground truth from the (editable) compatibility matrix.
    matrix_path = truth_dir / "compatibility_matrix.csv"
    if matrix_path.exists():
        compatibility = _read_csv(matrix_path)
    else:
        compatibility = default_compatibility(areas)
        _write(matrix_path, compatibility, ["worker_area_id", "worker_area", "job_area_id", "job_area", "relevant"])
    relevance = relevance_pairs(workers, jobs, compatibility)

    _write(out_dir / "workers.csv", workers, WORKER_COLUMNS)
    _write(out_dir / "jobs.csv", jobs, JOB_COLUMNS)
    area_name = {a.area_id: a.name for a in areas.values()}
    _write(truth_dir / "worker_truth.csv", [
        {"worker_id": w["worker_id"], "group_id": w["group_id"], "variant": w["variant"],
         "split": split_of[w["group_id"]], "area_id": w["_area_id"], "area": area_name[w["_area_id"]],
         "esco_uri": w["_occupation"].uri, "esco_label": w["_occupation"].label,
         "isco_code": w["_occupation"].isco_code, "alias": w["_alias"] or ""} for w in workers],
        ["worker_id", "group_id", "variant", "split", "area_id", "area", "esco_uri", "esco_label", "isco_code", "alias"])
    _write(truth_dir / "job_truth.csv", [
        {"posting_id": j["posting_id"], "source": j["source"], "area_id": j["_area_id"] or "",
         "area": area_name.get(j["_area_id"], ""), "esco_uri": j["_occupation"].uri if j["_occupation"] else "",
         "esco_label": j["_occupation"].label if j["_occupation"] else "",
         "isco_code": j["_occupation"].isco_code if j["_occupation"] else ""} for j in jobs],
        ["posting_id", "source", "area_id", "area", "esco_uri", "esco_label", "isco_code"])
    _write(truth_dir / "relevance.csv", relevance, ["worker_id", "posting_id", "relevance"])

    manifest = _manifest(seed, areas, base, split_of, workers, jobs, relevance, workers_per_area, overrides,
                         jobs_per_area, n_distractors if job_corpus is not None else 0,
                         {"aliases.csv": Path(vocab_dir) / "aliases.csv",
                          "area_esco_map.csv": Path(vocab_dir) / "area_esco_map.csv",
                          "area_skill_pools.csv": Path(pools_path), "compatibility_matrix.csv": matrix_path})
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def _count(items, key) -> dict:
    out: dict = {}
    for i in items:
        k = key(i)
        out[k] = out.get(k, 0) + 1
    return dict(sorted(out.items()))


def _manifest(seed, areas, base, split_of, workers, jobs, relevance, workers_per_area, overrides, jobs_per_area,
              n_distractors, inputs) -> dict:
    synthetic_jobs = [j for j in jobs if j["source"] == "synthetic"]
    return {
        "generator": f"kaziforce_api.data.synthetic v{GENERATOR_VERSION}",
        "seed": seed,
        "parameters": {"workers_per_area": workers_per_area, "area_overrides": {str(k): v for k, v in overrides.items()},
                       "jobs_per_area": jobs_per_area, "split_ratios": dict(SPLITS), "n_distractors": n_distractors},
        "areas": {str(a.area_id): {"name": a.name, "occupations": [o.label for o in a.occupations]}
                  for a in areas.values()},
        "counts": {
            "base_workers_per_area": {str(k): v for k, v in _count(base, lambda b: b["area_id"]).items()},
            "groups_per_split": _count(base, lambda b: split_of[b["group_id"]]),
            "groups_per_area_split": {f"{a}/{s}": n for (a, s), n in
                                      _count(base, lambda b: (b["area_id"], split_of[b["group_id"]])).items()},
            "worker_rows": len(workers),
            "worker_rows_per_variant": _count(workers, lambda w: w["variant"]),
            "worker_rows_per_split": _count(workers, lambda w: split_of[w["group_id"]]),
            "worker_rows_per_area_variant": {f"{a}/{v}": n for (a, v), n in
                                             _count(workers, lambda w: (w["_area_id"], w["variant"])).items()},
            "jobs": len(jobs),
            "jobs_per_source": _count(jobs, lambda j: j["source"]),
            "synthetic_jobs_per_area": {str(k): v for k, v in _count(synthetic_jobs, lambda j: j["_area_id"]).items()},
            "relevance_pairs": len(relevance),
        },
        "templates": TEMPLATE_COUNTS,
        "inputs_sha256": {name: sha256_file(p) for name, p in inputs.items()},
    }
