"""PHASE 3 acceptance - is the resolution score traceable to EVIDENCE TEXT?

For every attribute the seed attaches to a person (vehicles, phones, accounts,
locations, activity dates), this checks whether the value actually appears in the
text of one of that person's case evidence documents. An attribute that appears
nowhere in evidence is an attribute injected only in seed data: it would inflate
identity-match scores without any documentary basis.

Run:  cd backend && python3 scripts/check_evidence_traceability.py
"""
from __future__ import annotations

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.seed import EVIDENCE_DOCS, PERSONS  # noqa: E402

ATTR_KEYS = ("vehicles", "phones", "accounts", "locations")


def _normalise(value: str) -> str:
    return "".join(ch for ch in value.upper() if ch.isalnum())


def main() -> int:
    by_case: dict[str, list[str]] = {}
    for doc in EVIDENCE_DOCS:
        by_case.setdefault(doc["case_id"], []).append(doc["text"])
    corpus = "\n".join(d["text"] for d in EVIDENCE_DOCS)
    corpus_norm = _normalise(corpus)

    total = grounded = 0
    ungrounded: list[str] = []
    print("=" * 92)
    print("PHASE 3 ACCEPTANCE - EVIDENCE TRACEABILITY OF IDENTITY ATTRIBUTES")
    print("=" * 92)
    for pid, name, cases, attrs in PERSONS:
        case_text = "\n".join("\n".join(by_case.get(c, [])) for c in cases if c != "*")
        case_norm = _normalise(case_text)
        for key in ATTR_KEYS:
            for value in attrs.get(key) or []:
                total += 1
                v = _normalise(value)
                in_own_case = v in case_norm
                in_any = v in corpus_norm
                if in_own_case:
                    grounded += 1
                else:
                    ungrounded.append(f"{pid} {name} {key}={value} "
                                      f"({'in other case evidence' if in_any else 'NOT IN ANY EVIDENCE'})")
        # The evidence documents are written in narrative English ("12 August"),
        # so a date claim is grounded if that day/month appears in the text.
        months = ["January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December"]
        stated = set()
        for m in re.finditer(r"\b(\d{1,2})\s+(" + "|".join(months) + r")\b", case_text):
            stated.add((int(m.group(1)), m.group(2)))
        for m in re.finditer(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b", case_text):
            stated.add((int(m.group(1)), months[int(m.group(2)) - 1]))
        for d in attrs.get("activity_dates") or []:
            total += 1
            key = (int(d[8:10]), months[int(d[5:7]) - 1])
            if key in stated:
                grounded += 1
            else:
                ungrounded.append(f"{pid} {name} activity_date={d} (no explicit date in case evidence)")

    print(f"attributes checked                : {total}")
    print(f"traceable to that person's evidence: {grounded}")
    print(f"NOT traceable                      : {len(ungrounded)}")
    if ungrounded:
        print("\nungrounded attributes:")
        for line in ungrounded:
            print("   ", line)
    else:
        print("\nEvery identity attribute is stated in the evidence text for that person's case.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
