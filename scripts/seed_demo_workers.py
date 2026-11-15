"""
Creates nine demo worker accounts, each named and consenting: three plumbers, and two each of carpenter,
electrician and cook.

    python scripts/seed_demo_workers.py

Safe to run twice. They sign in with the phone numbers 700 000 001 to 009 and PIN 4821, and
they appear first in the "Workers in this trade" list for a job in their trade. Demo data only: see
kaziforce_api/data/demo.py for why, and python scripts/seed_database.py --reset to clear it.

Needs the migrations applied and, outside development, the field keys (docs/privacy-and-keys.md).
"""

from kaziforce_api.data.accounts import AccountStore
from kaziforce_api.data.demo import DEMO_PIN, DEMO_WORKERS, seed_demo_workers
from kaziforce_api.data.seed import SkillDescriber
from kaziforce_api.data.store import PostgresProfileStore


def main() -> None:
    created = seed_demo_workers(AccountStore(), PostgresProfileStore(), SkillDescriber())
    print(f"Created {len(created)} of {len(DEMO_WORKERS)} demo workers" + (f": {', '.join(created)}" if created else " (already there)"))
    print(f"Sign in with any of {', '.join(w.phone for w in DEMO_WORKERS)} and PIN {DEMO_PIN}")


if __name__ == "__main__":
    main()
