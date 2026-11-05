"""
Three demo worker accounts in one trade, each with a name and consent, so a client's job-posted
screen has named cards to open.

These are made up: the names, and numbers in the 0700 000 00x range. Kenya has no range reserved
for fiction, so a number here is *probably* unassigned and not guaranteed to be; do not ring them.
The PIN is the same for all three and is public (it is in this file), which is fine for a demo and
is the reason none of this belongs on a deployed database.

A trade list shows the first five workers in the trade by worker_id, which is random for anyone
who signs up. A demo worker would usually fall outside those five, so these three are given
worker_ids that sort ahead of every random one. That is a demo accommodation, not a feature: it
changes which workers are in the sample, which is arbitrary anyway, and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass

from kaziforce_api.auth import AuthError
from kaziforce_api.data.accounts import AccountStore, Contact
from kaziforce_api.data.models import WorkerProfile
from kaziforce_api.data.seed import SkillDescriber
from kaziforce_api.data.store import PostgresProfileStore

DEMO_PIN = "4821"
TRADE = "plumber"


@dataclass(frozen=True)
class DemoWorker:
    phone: str
    first_name: str
    last_name: str
    worker_id: str
    skills: tuple[str, ...]
    biography: str
    location: str
    availability: str
    rate: float


DEMO_WORKERS = (
    DemoWorker("700000001", "Amina", "Wanjiru", "00000000-0000-4000-8000-00000000d001",
               ("fundi bomba", "replace faucets", "plumbing tools"),
               "Fundi bomba mwenye uzoefu wa miaka sita. Bathroom and kitchen repairs, leaking joints.",
               "Nairobi - Kasarani", "Full-time", 2400),
    DemoWorker("700000002", "Joseph", "Otieno", "00000000-0000-4000-8000-00000000d002",
               ("fundi bomba", "install pipes"),
               "Nafanya kazi ya mabomba na water tanks. Residential plumbing and new connections.",
               "Nairobi - Umoja", "Part-time", 2000),
    DemoWorker("700000003", "Grace", "Achieng", "00000000-0000-4000-8000-00000000d003",
               ("fundi bomba", "check water pressure"),
               "Plumber with four years in rental flats. Naweza kuanza wikendi.",
               "Meru", "Weekends", 1800),
)


def seed_demo_workers(accounts: AccountStore, store: PostgresProfileStore, describer: SkillDescriber) -> list[str]:
    """Create the demo workers that do not exist yet. Returns the phone numbers it created."""
    created = []
    for demo in DEMO_WORKERS:
        try:
            account = accounts.create(demo.phone, DEMO_PIN, "worker", Contact(demo.first_name, demo.last_name, True))
        except AuthError:
            continue  # already there: running this twice is harmless
        stored = store.save_worker(
            WorkerProfile(demo.worker_id, demo.biography, demo.skills, demo.location, demo.availability, demo.rate),
            describer.describe(demo.skills))
        accounts.claim_worker_profile(account.account_id, stored.worker_id)
        created.append(demo.phone)
    return created
