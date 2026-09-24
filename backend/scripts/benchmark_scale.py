"""PHASE 6 - measured scalability of the entity-resolution step.

`resolution_agent.compare_pair()` is called once per candidate pair, so resolving a
case with N entities costs N(N-1)/2 comparisons. This script generates N realistic
entity records (same shapes as `app/database/seed.py`: Indian names, vehicle
registrations, MSISDNs, account numbers, Chennai locations, activity dates), runs
the real resolver over every pair, and reports the wall-clock cost.

The point is a MEASURED number to state honestly, not an optimisation. Nothing here
changes the algorithm; a production deployment would add blocking / index keys to
avoid comparing every pair.

Run:  cd backend && python3 scripts/benchmark_scale.py [more sizes...]
"""
from __future__ import annotations

import os
import random
import sys
import time
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import resolution_agent  # noqa: E402
from app.database.seed import LOCATIONS, PERSONS, PHONES, VEHICLES  # noqa: E402

GIVEN = ["Ravi", "Arun", "Suresh", "Karthik", "Mohan", "Vignesh", "Prakash", "Anitha",
         "Divya", "Meena", "Lakshmi", "Sanjay", "Farhan", "Bhuvaneswari", "Vasanthi",
         "Selvaraj", "Ganesan", "Rajan", "Nair", "Iyer", "Menon", "Rao", "Prabhu",
         "Kumar", "Das", "Ali", "Anand", "Raghavan", "Balan", "Selvam"]
FAMILY = ["Kumar", "Selvam", "Rajan", "Das", "Nair", "Iyer", "Menon", "Rao", "Prabhu",
          "Anand", "Raghavan", "Balan", "Ganesan", "Vasanthi", "Bhuvaneswari", "Ali"]


def generate_entities(n: int, seed: int = 20260922) -> list[dict[str, Any]]:
    """N entity records in the shapes the seeded cases use."""
    rng = random.Random(seed)
    plates = [p for _v, p, _c in VEHICLES]
    numbers = [p for _i, p, _c in PHONES]
    places = [name for _l, name, _la, _lo, _c in LOCATIONS]
    base_persons = [(pid, name, attrs) for pid, name, _c, attrs in PERSONS]

    entities: list[dict[str, Any]] = []
    for i in range(n):
        roll = rng.random()
        if roll < 0.70:                                   # people (the common case)
            if i < len(base_persons) and rng.random() < 0.5:
                pid, name, attrs = base_persons[i % len(base_persons)]
                cases = ["CASE-101"]
            else:
                first, last = rng.choice(GIVEN), rng.choice(FAMILY)
                name = f"{first} {last}"
                if rng.random() < 0.35:                   # initials / spacing variants
                    style = rng.random()
                    if style < 0.4:
                        name = f"{first[0]}. {last}"
                    elif style < 0.7:
                        name = f"{first} {last[0]}."
                    else:
                        name = f"{first}  {last}"
                cases = ["CASE-101"]
                attrs = {}
            plate = rng.choice(plates)
            number = rng.choice(numbers)
            place = rng.choice(places)
            attrs = dict(attrs or {})
            attrs.setdefault("vehicles", [plate])
            attrs.setdefault("phones", [number])
            attrs.setdefault("locations", [place])
            attrs.setdefault("activity_dates", [f"2025-08-{rng.randint(10, 28):02d}"])
            entities.append({"label": name, "entity_type": "PERSON", "cases": cases,
                             "attributes": attrs})
        elif roll < 0.80:                                 # vehicles
            entities.append({"label": rng.choice(plates), "entity_type": "VEHICLE",
                             "cases": ["CASE-101"], "attributes": {}})
        elif roll < 0.88:                                 # phones
            entities.append({"label": rng.choice(numbers), "entity_type": "PHONE",
                             "cases": ["CASE-101"], "attributes": {}})
        elif roll < 0.94:                                 # accounts
            entities.append({"label": f"A/C {rng.randint(10000000, 99999999)}",
                             "entity_type": "ACCOUNT", "cases": ["CASE-305"],
                             "attributes": {}})
        else:                                             # locations / organisations
            entities.append({"label": rng.choice(places), "entity_type": "LOCATION",
                             "cases": ["CASE-101"], "attributes": {}})
    return entities


def benchmark(n: int) -> dict[str, Any]:
    entities = generate_entities(n)
    pairs = n * (n - 1) // 2
    started = time.perf_counter()
    proposed = 0
    for i in range(n):
        for j in range(i + 1, n):
            result = resolution_agent.compare_pair(entities[i], entities[j])
            if result["support_level"] in {"HIGH", "MEDIUM"}:
                proposed += 1
    elapsed = time.perf_counter() - started
    return {"n": n, "pairs": pairs, "seconds": elapsed,
            "us_per_pair": (elapsed / pairs * 1e6) if pairs else 0.0,
            "candidates": proposed}


def main() -> int:
    sizes = [int(a) for a in sys.argv[1:]] or [50, 200, 500, 1000]
    print("=" * 92)
    print("PHASE 6 - MEASURED SCALABILITY OF ENTITY RESOLUTION (all-pairs, no blocking)")
    print("=" * 92)
    print("resolution_agent.compare_pair() is called once per candidate pair; the")
    print("algorithm is O(N^2) in the number of entities, exactly as documented.\n")
    print(f"{'N entities':>11} {'comparisons':>13} {'wall clock':>12} {'per pair':>10} "
          f"{'pairs/sec':>10} {'candidates':>11}")
    print("-" * 92)
    rows = []
    for n in sizes:
        row = benchmark(n)
        rows.append(row)
        print(f"{row['n']:>11,} {row['pairs']:>13,} {row['seconds']:>10.2f} s "
              f"{row['us_per_pair']:>8.0f} us {row['pairs'] / row['seconds']:>10,.0f} "
              f"{row['candidates']:>11,}", flush=True)
    print("-" * 92)
    if len(rows) >= 2:
        base, last = rows[0], rows[-1]
        print(f"growth: {last['n'] // base['n']}x the entities costs "
              f"{last['seconds'] / base['seconds']:.1f}x the time (quadratic)")
        print(f"projected for 5,000 entities : {last['us_per_pair'] * 5000 * 4999 / 2 / 1e6 / 60:.1f} minutes"
              f"   (single core, this implementation, no blocking)")
        print(f"projected for 10,000 entities: {last['us_per_pair'] * 10000 * 9999 / 2 / 1e6 / 60:.1f} minutes"
              f"   (single core, this implementation, no blocking)")
    print("\nhonest reading: this is the worst case (every pair compared). A production")
    print("deployment adds blocking keys - exact identifier match first, then name")
    print("phonetics - so only a small candidate set reaches the fuzzy resolver.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
