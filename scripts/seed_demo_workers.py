"""
Creates three demo worker accounts in one trade (plumber), each named and consenting.

    python scripts/seed_demo_workers.py

Safe to run twice. They sign in with the phone numbers 700 000 001, 002 and 003 and PIN 4821, and
they appear first in the "Workers in this trade" list for a plumbing job. Demo data only: see
kaziforce_api/data/demo.py for why, and python scripts/seed_database.py --reset to clear it.

Needs the migrations applied and, outside development, the field keys (docs/privacy-and-keys.md).
"""

from kaziforce_api.data.accounts import AccountStore
from kaziforce_api.data.demo import DEMO_PIN, DEMO_WORKERS, TRADE, seed_demo_workers
from kaziforce_api.data.seed import SkillDescriber
from kaziforce_api.data.store import PostgresProfileStore


def main() -> None:
    created = seed_demo_workers(AccountStore(), PostgresProfileStore(), SkillDescriber())
    print(f"Created {len(created)} of {len(DEMO_WORKERS)} demo {TRADE}s" + (f": {', '.join(created)}" if created else " (already there)"))
    print(f"Sign in with any of {', '.join(w.phone for w in DEMO_WORKERS)} and PIN {DEMO_PIN}")


if __name__ == "__main__":
    main()
