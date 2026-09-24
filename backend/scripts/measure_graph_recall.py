"""PHASE 3.1 - measure how much of the seeded relationship set the REAL pipeline
reproduces from the evidence document text.

For every relationship in `seed.RELATIONSHIPS`, this runs the live extraction
pipeline (document cleaning -> entity extraction -> event extraction) against that
relationship's own evidence document and asks two independent questions:

  ENDPOINTS  - did extraction recover both endpoint entities from the document?
  CO-EVENT   - did at least one extracted EVENT contain both endpoints together,
               i.e. is the pair actually derivable from a co-occurrence, not just
               two names that happen to appear in the same file?

A relationship is REPRODUCED only when both hold. Anything else is a relationship
that was hand-authored into the seed and is *not* supported by its own document.

Run:  cd backend && python3 scripts/measure_graph_recall.py [--verbose]
"""
from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import document_agent, entity_agent  # noqa: E402
from app.database.seed import EVIDENCE_DOCS, RELATIONSHIPS, entity_labels  # noqa: E402


def _gazetteer() -> dict[str, list[str]]:
    """Vocabulary used by the live pipeline: labels of the seeded entities."""
    labels = entity_labels()
    gaz: dict[str, list[str]] = {}
    for entity_id, label, entity_type in labels:
        key = "PERSON" if entity_type in {"PERSON", "ALIAS"} else entity_type
        gaz.setdefault(key, []).append(label)
    return gaz


def measure(verbose: bool = False) -> dict[str, Any]:
    docs = {d["evidence_id"]: d for d in EVIDENCE_DOCS}
    labels = {entity_id: (label, etype) for entity_id, label, etype in entity_labels()}
    gaz = _gazetteer()

    rows: list[dict[str, Any]] = []
    for rel_id, source, target, rel_type, ts, evid, case_id, support, verification in RELATIONSHIPS:
        doc = docs.get(evid)
        if doc is None:
            rows.append({"rel_id": rel_id, "verdict": "NO_DOCUMENT", "evidence": evid})
            continue
        text = document_agent.normalize_text(document_agent.clean_text(doc["text"]))
        extraction = entity_agent.run(text, gaz)
        found = {e["normalized"].upper() for e in extraction["entities"]}

        def recovered(entity_id: str) -> bool:
            label, _ = labels.get(entity_id, ("", ""))
            if not label:
                return False
            up = label.upper()
            if up in found:
                return True
            # also accept a normalized variant (digits/spacing differences)
            key = "".join(ch for ch in up if ch.isalnum())
            return any("".join(ch for ch in f if ch.isalnum()) == key for f in found)

        src_ok, tgt_ok = recovered(source), recovered(target)
        co_event = False
        for event in extraction["events"]:
            actors = {a.upper() for a in event["actors"]}
            actors |= {l.upper() for l in event["locations"]}
            if recovered(source) and recovered(target) and any(
                    "".join(ch for ch in a if ch.isalnum()) in
                    {"".join(ch for ch in labels.get(source, ("", ""))[0].upper() if ch.isalnum()),
                     "".join(ch for ch in labels.get(target, ("", ""))[0].upper() if ch.isalnum())}
                    for a in actors):
                both = 0
                for entity_id in (source, target):
                    label = labels.get(entity_id, ("", ""))[0].upper()
                    if any("".join(ch for ch in a if ch.isalnum()) ==
                           "".join(ch for ch in label if ch.isalnum()) for a in actors):
                        both += 1
                if both == 2:
                    co_event = True
                    break

        verdict = ("REPRODUCED" if (src_ok and tgt_ok and co_event)
                   else "ENDPOINTS_ONLY" if (src_ok and tgt_ok)
                   else "NOT_DERIVED")
        rows.append({
            "rel_id": rel_id, "source": source, "target": target, "rel_type": rel_type,
            "evidence": evid, "case_id": case_id, "support": support,
            "src_recovered": src_ok, "tgt_recovered": tgt_ok, "co_event": co_event,
            "verdict": verdict,
        })

    reproduced = [r for r in rows if r["verdict"] == "REPRODUCED"]
    endpoints_only = [r for r in rows if r["verdict"] == "ENDPOINTS_ONLY"]
    missing = [r for r in rows if r["verdict"] in {"NOT_DERIVED", "NO_DOCUMENT"}]
    return {
        "total": len(rows), "reproduced": len(reproduced),
        "endpoints_only": len(endpoints_only), "not_derived": len(missing),
        "recall_pct": round(100.0 * len(reproduced) / max(1, len(rows)), 1),
        "rows": rows, "verbose": verbose,
    }


def main() -> int:
    verbose = "--verbose" in sys.argv
    result = measure(verbose)
    print("=" * 96)
    print("PHASE 3.1 - SEEDED RELATIONSHIP RECALL: is the demo graph DERIVED or AUTHORED?")
    print("=" * 96)
    print(f"{'rel':9} {'source':9} {'rel_type':16} {'target':9} {'evidence':9} "
          f"{'src':5} {'tgt':5} {'co-event':9} verdict")
    print("-" * 96)
    for r in result["rows"]:
        if r["verdict"] == "NO_DOCUMENT":
            print(f"{r['rel_id']:9} {'':9} {'':16} {'':9} {r['evidence']:9} "
                  f"{'-':5} {'-':5} {'-':9} {r['verdict']}")
            continue
        print(f"{r['rel_id']:9} {r['source']:9} {r['rel_type']:16} {r['target']:9} "
              f"{r['evidence']:9} {'yes' if r['src_recovered'] else 'NO':5} "
              f"{'yes' if r['tgt_recovered'] else 'NO':5} "
              f"{'yes' if r['co_event'] else 'NO':9} {r['verdict']}")
    print("-" * 96)
    print(f"REPRODUCED by the pipeline : {result['reproduced']}/{result['total']} "
          f"({result['recall_pct']}%)")
    print(f"Endpoints only (no co-event): {result['endpoints_only']}")
    print(f"Not derivable at all       : {result['not_derived']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
