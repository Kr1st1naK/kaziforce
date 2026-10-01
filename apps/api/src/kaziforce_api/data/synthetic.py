"""
Synthetic worker profile and job posting generator (DR-05, DR-07).

First working version: generates a small, reproducible set of worker profiles
and job postings from predefined occupational specifications. Each spec is
grounded in:
  - a KNBS occupational category (KNOCS, which follows the ISCO-08 structure),
  - an ESCO occupation and a subset of its essential ESCO skill labels
    (taken from the subset fetched by scripts/download_esco.py),
  - candidate Kenya-specific informal trade terms from data/vocabulary/README.md
    (not yet validated; see kaziforce_kg.vocabulary).

Records contain no real personal identifiers (DR-07). The occupation fields are
generation metadata, kept so relevance labels can later be derived
independently of the recommender's own scores (proposal Section 3.2.4).
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class OccupationSpec:
    area: str                      # vocabulary area, data/vocabulary/README.md
    knbs_major_group: str          # KNOCS / ISCO-08 major group
    isco_code: str
    esco_occupation: str           # ESCO preferred label
    informal_terms: tuple[str, ...]
    esco_skills: tuple[str, ...]   # ESCO preferred labels (essential skills)
    job_titles: tuple[str, ...]
    rate_range_kes: tuple[int, int]  # illustrative daily rate, KES


CRAFT = "Craft and Related Trades Workers"
SERVICE = "Service and Sales Workers"
ELEMENTARY = "Elementary Occupations"

OCCUPATION_SPECS: tuple[OccupationSpec, ...] = (
    OccupationSpec(
        "Electrician", CRAFT, "7411", "electrician", ("fundi wa stima", "fundi wa umeme"),
        ("install electricity sockets", "maintain electrical equipment", "splice cable",
         "inspect electrical supplies", "resolve equipment malfunctions"),
        ("House wiring for new rental units", "Fix faulty sockets and lighting"),
        (1500, 3500),
    ),
    OccupationSpec(
        "Plumber", CRAFT, "7126", "plumber", ("fundi wa mabomba",),
        ("install plumbing systems", "install PVC piping", "check water pressure",
         "use measurement instruments"),
        ("Repair leaking pipes in apartment", "Install water tank and piping"),
        (1500, 3000),
    ),
    OccupationSpec(
        "Carpenter", CRAFT, "7115", "carpenter", ("fundi wa mbao",),
        ("join wood elements", "create wood joints", "apply wood finishes",
         "install wood hardware"),
        ("Build kitchen cabinets", "Repair wooden doors and frames"),
        (1200, 3000),
    ),
    OccupationSpec(
        "Tailor / dressmaker", CRAFT, "7531", "dressmaker", ("fundi wa nguo",),
        ("measure the human body for wearing apparel", "sew pieces of fabric",
         "alter wearing apparel", "cut fabrics"),
        ("Tailor school uniforms", "Alter and repair clothing"),
        (800, 2000),
    ),
    OccupationSpec(
        "Hairdresser / barber", SERVICE, "5141", "barber", ("kinyozi",),
        ("style hair", "treat facial hair", "use equipment for hair care",
         "maintain customer service"),
        ("Barber for mobile home visits", "Haircuts for staff event"),
        (500, 1500),
    ),
    OccupationSpec(
        "Domestic cleaner", ELEMENTARY, "9111", "domestic cleaner", ("house cleaner",),
        ("clean rooms", "handle chemical cleaning agents", "wash the dishes", "vacuum surfaces"),
        ("Weekly house cleaning", "Move-out deep cleaning"),
        (800, 1500),
    ),
    OccupationSpec(
        "Laundry worker", ELEMENTARY, "8157", "laundry worker", ("mama fua",),
        ("clean household linens", "iron textiles", "distinguish fabrics",
         "collect items for laundry service"),
        ("Weekly laundry and ironing", "Laundry for family of five"),
        (500, 1200),
    ),
    OccupationSpec(
        "Motor-vehicle mechanic", CRAFT, "7231", "vehicle technician", ("fundi wa magari",),
        ("carry out repair of vehicles", "repair vehicle electrical systems",
         "position vehicles for maintenance and repair", "maintain vehicle records"),
        ("Service and repair a saloon car", "Diagnose engine electrical fault"),
        (1500, 4000),
    ),
)

LOCATIONS = (
    "Nairobi - Kasarani", "Nairobi - Embakasi", "Nairobi - Westlands", "Nairobi - Kibera",
    "Mombasa", "Kisumu", "Nakuru", "Eldoret", "Thika",
)
AVAILABILITY = ("Full-time", "Part-time", "Weekends")

_BIO_TEMPLATES = {
    "formal": "{occupation_title} with {years} years of experience. Skilled in {skills}. "
              "Based in {location} and available {availability_lower}.",
    "informal": "Mimi ni {term}, nina uzoefu wa miaka {years}. Nafanya kazi {location}.",
    "mixed": "Experienced {term} ({years} yrs) around {location}. I do {skills}.",
}


def _uuid(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def _pick_skills(rng: random.Random, spec: OccupationSpec, k_min: int = 2) -> list[str]:
    k = rng.randint(k_min, len(spec.esco_skills))
    return sorted(rng.sample(spec.esco_skills, k))


def generate_synthetic_data(n_workers: int = 12, n_jobs: int = 12, seed: int = 42) -> dict[str, pd.DataFrame]:
    """Generate reproducible synthetic worker profiles and job postings.

    Returns {"workers": DataFrame, "jobs": DataFrame}. Skill columns hold lists
    of ESCO skill labels; worker skills may also include an informal term,
    exercising the vocabulary-mapping path (FR-03, FR-10).
    """
    rng = random.Random(seed)
    workers, jobs = [], []

    for i in range(n_workers):
        spec = OCCUPATION_SPECS[i % len(OCCUPATION_SPECS)]
        style = ("formal", "informal", "mixed")[i % 3]
        skills = _pick_skills(rng, spec)
        term = rng.choice(spec.informal_terms)
        availability = rng.choice(AVAILABILITY)
        location = rng.choice(LOCATIONS)
        years = rng.randint(1, 15)
        biography = _BIO_TEMPLATES[style].format(
            occupation_title=spec.esco_occupation.capitalize(), term=term, years=years,
            skills=", ".join(skills[:3]), location=location, availability_lower=availability.lower(),
        )
        workers.append({
            "worker_id": _uuid(rng),
            "display_name": f"Synthetic Worker {i + 1:02d}",
            "skills": skills + ([term] if style != "formal" else []),
            "biography": biography,
            "location": location,
            "availability": availability,
            "rate_expectation": rng.randrange(*spec.rate_range_kes, 100),
            "bio_style": style,
            "occupation_area": spec.area,
            "esco_occupation": spec.esco_occupation,
            "isco_code": spec.isco_code,
            "knbs_major_group": spec.knbs_major_group,
        })

    for i in range(n_jobs):
        spec = OCCUPATION_SPECS[(i * 3) % len(OCCUPATION_SPECS)]
        required = _pick_skills(rng, spec)
        title = rng.choice(spec.job_titles)
        location = rng.choice(LOCATIONS)
        low, high = spec.rate_range_kes
        jobs.append({
            "posting_id": _uuid(rng),
            "title": title,
            "category": spec.area,
            "required_skills": required,
            "description": f"{title} in {location}. Looking for someone who can "
                           f"{' and '.join(required[:2])}.",
            "budget": rng.randrange(low, high * 2, 100),
            "location": location,
            "esco_occupation": spec.esco_occupation,
            "isco_code": spec.isco_code,
            "knbs_major_group": spec.knbs_major_group,
        })

    return {"workers": pd.DataFrame(workers), "jobs": pd.DataFrame(jobs)}
