"""
Demo worker accounts, each with a name and consent, so a client's job-posted screen has named cards to
open: three plumbers (700 000 001 to 003, the ones the end-to-end tests rely on) and two each in
carpenter, electrician and cook (004 to 009), so a demonstration of those trades also has someone to open.

These are made up: the names, and numbers in the 0700 000 0xx range. Kenya has no range reserved
for fiction, so a number here is *probably* unassigned and not guaranteed to be; do not ring them.
The PIN is the same for all three and is public (it is in this file), which is fine for a demo and
is the reason none of this belongs on a deployed database.

A trade list shows the first five workers in the trade by worker_id, which is random for anyone
who signs up. A demo worker would usually fall outside those five, so these are given
worker_ids that sort ahead of every random one. That is a demo accommodation, not a feature: it
changes which workers are in the sample, which is arbitrary anyway, and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass

from kaziforce_api.auth import AuthError, normalise_phone
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
    trade: str = "plumber"


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
    # Each uses the accepted Kiswahili term for the trade (fundi wa mbao, fundi wa umeme, mpishi), which the
    # knowledge graph maps to the occupation, so each reaches its trade in a client's list.
    DemoWorker("700000004", "Peter", "Kamau", "00000000-0000-4000-8000-00000000d004",
               ("fundi wa mbao", "wood cuts", "apply wood finishes"),
               "Fundi wa mbao, kitchen cabinets and doors. Furniture repairs in Nairobi.",
               "Nairobi - Embakasi", "Full-time", 2600, "carpenter"),
    DemoWorker("700000005", "Esther", "Njeri", "00000000-0000-4000-8000-00000000d005",
               ("fundi wa mbao", "use measurement instruments"),
               "Carpenter for roof trusses and shelving. Naweza kufanya kazi wikendi.",
               "Nakuru", "Weekends", 2200, "carpenter"),
    DemoWorker("700000006", "David", "Mwangi", "00000000-0000-4000-8000-00000000d006",
               ("fundi wa umeme", "install electricity sockets", "splice cable"),
               "Fundi wa umeme, house wiring and distribution boards. Five years on rental flats.",
               "Nairobi - Kasarani", "Full-time", 3000, "electrician"),
    DemoWorker("700000007", "Faith", "Wambui", "00000000-0000-4000-8000-00000000d007",
               ("fundi wa umeme", "install electricity sockets"),
               "Electrician for sockets, lighting and fault-finding in shops. Part-time.",
               "Nyeri", "Part-time", 2400, "electrician"),
    DemoWorker("700000008", "Hassan", "Ali", "00000000-0000-4000-8000-00000000d008",
               ("mpishi", "prepare dishes"),
               "Mpishi wa harusi na sherehe. Cook for events, from fifty to two hundred guests.",
               "Mombasa", "Weekends", 2800, "cook"),
    DemoWorker("700000009", "Mary", "Atieno", "00000000-0000-4000-8000-00000000d009",
               ("mpishi", "cook meals"),
               "Mpishi wa mgahawa mdogo. Cook for a small restaurant, breakfast and lunch.",
               "Kisumu", "Full-time", 1800, "cook"),
)


def seed_demo_workers(accounts: AccountStore, store: PostgresProfileStore, describer: SkillDescriber) -> list[str]:
    """Create the demo workers that do not exist yet, and make sure all of them are consenting.

    Returns the phone numbers it created. A demo worker who already exists is left as they are
    except that consent is switched back on, so a test that withdrew it cannot leave the demo
    without its named cards. (If someone has changed a demo account's PIN, it is left alone.)
    """
    created = []
    for demo in DEMO_WORKERS:
        contact = Contact(demo.first_name, demo.last_name, True)
        phone = normalise_phone(demo.phone)  # the form the API stores and looks up: 254700000001
        try:
            account = accounts.create(phone, DEMO_PIN, "worker", contact)
        except AuthError:
            try:
                accounts.update_contact(accounts.authenticate(phone, DEMO_PIN).account_id, contact)
            except AuthError:
                pass
            continue
        stored = store.save_worker(
            WorkerProfile(demo.worker_id, demo.biography, demo.skills, demo.location, demo.availability, demo.rate),
            describer.describe(demo.skills))
        accounts.claim_worker_profile(account.account_id, stored.worker_id)
        created.append(demo.phone)
    return created
