"""PHASE 6 - extraction and entity-resolution evaluation harness.

Two screenshot-ready reports on stdout:

  REPORT 1  ENTITY EXTRACTION   precision / recall / F1 per entity type and
            overall, measured against `backend/eval/labelled_entities.json`
            (hand-labelled ground truth for the ten evidence documents of the
            five seeded cases), plus the exact misses so a reviewer can see
            what failed instead of trusting a summary number.

  REPORT 2  ENTITY RESOLUTION   the trap set in
            `backend/eval/resolution_pairs.json`: how many same-entity pairs are
            proposed at HIGH confidence, and - the number that matters most -
            how many DIFFERENT entities would be merged. Zero false merges is
            the target; the script exits non-zero if any appears.

Both reports are produced by the same pipeline the API uses: document cleaning
-> `entity_agent.run(text, gazetteer)` with the case vocabulary, and
`resolution_agent.compare_pair()` with the configured HIGH/MEDIUM thresholds.

Run:  cd backend && python3 scripts/eval_extraction.py
"""
from __future__ import annotations

import json
import os
import re
import sys
from itertools import zip_longest
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents import document_agent, entity_agent, graph_ops, resolution_agent  # noqa: E402
from app.config import RESOLUTION_HIGH, RESOLUTION_MEDIUM  # noqa: E402
from app.database.seed import EVIDENCE_DOCS, entity_labels  # noqa: E402

EVAL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "eval")
TYPES = ("PERSON", "ORGANIZATION", "LOCATION", "VEHICLE", "PHONE", "ACCOUNT", "DEVICE",
         "DATE", "ALIAS")
DATASET_PDF = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "datasets", "01_FIR", "FIR_0412-2025_CASE-101_Chennai-Central.pdf")
RULE = "=" * 92
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]


def _case_vocabulary() -> dict[str, list[str]]:
    """The entity vocabulary already known to the case graph (same as the API path)."""
    gaz: dict[str, list[str]] = {}
    for _eid, label, etype in entity_labels():
        key = "PERSON" if etype in {"PERSON", "ALIAS"} else etype
        gaz.setdefault(key, []).append(label)
    return {k: sorted(set(v)) for k, v in gaz.items() if v}


def _fold(value: str) -> str:
    """Comparison key: case, spacing and punctuation insensitive (ASCII path).

    NOTE: this deliberately drops every non-ASCII character, which is correct for the
    Latin-script seeded documents but collapses any Indic string to "". The negative-case
    report therefore uses _fold_any() below instead.
    """
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _fold_any(value: str) -> str:
    """Same idea, but script-agnostic: keeps Devanagari and Tamil letters, so two
    different Indic surfaces cannot both fold to the empty string and match each
    other."""
    return re.sub(r"[\W_]", "", value, flags=re.UNICODE).lower()


def _date_key(value: str) -> str:
    """Canonical day+month key so '10 August', '10 August 2025' and '2025-08-10' agree."""
    v = value.lower().strip()
    m = re.match(r"^(\d{1,2})\s+([a-z]+)", v)
    if m and m.group(2)[:3] in [mo[:3] for mo in MONTHS]:
        return f"{int(m.group(1)):02d}-{m.group(2)[:3]}"
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", v)
    if m:
        return f"{int(m.group(3)):02d}-{MONTHS[int(m.group(2)) - 1][:3]}"
    m = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-]\d{2,4}$", v)
    if m:
        return f"{int(m.group(1)):02d}-{MONTHS[int(m.group(2)) - 1][:3]}"
    return v


def evaluate_extraction() -> tuple[dict[str, int], list[str]]:
    labels = json.load(open(os.path.join(EVAL_DIR, "labelled_entities.json")))
    gaz = _case_vocabulary()
    totals = {t: {"tp": 0, "fp": 0, "fn": 0} for t in TYPES}
    group_totals = {g: {t: {"tp": 0, "fp": 0, "fn": 0} for t in TYPES}
                    for g in ("SEEDED", "DATASET_PDF")}
    misses: list[str] = []
    print(RULE)
    print("REPORT 1 - ENTITY EXTRACTION vs LABELLED GROUND TRUTH "
          "(10 seeded documents + the real FIR PDF, 5 cases, 9 entity types)")
    print(RULE)
    print(f"{'document':10} {'case':9} {'type':13} {'precision':>10} {'recall':>8} "
          f"{'F1':>6}  {'tp':>3} {'fp':>3} {'fn':>3}")
    print("-" * 92)

    documents = [(d["evidence_id"], d["case_id"],
                  document_agent.normalize_text(document_agent.clean_text(d["text"])), "SEEDED")
                 for d in EVIDENCE_DOCS]
    if os.path.exists(DATASET_PDF):
        # The real FIR PDF is labelled under its file name and read through the same
        # pypdf text-layer path the API uses. It is the document that exposed the
        # ALIAS false positives, so it is scored here rather than trusted to a manual
        # check.
        raw = open(DATASET_PDF, "rb").read()
        documents.append((os.path.basename(DATASET_PDF), "CASE-101",
                          document_agent.clean_text(document_agent.pdf_extractor.extract(raw)["text"]),
                          "DATASET_PDF"))
    else:
        print("NOTE: dataset FIR PDF not present - scoring the 10 seeded documents only.")

    for doc_id, case_id, text, group in documents:
        expected = labels.get(doc_id, {})
        if doc_id not in labels:
            continue
        found = entity_agent.run(text, gaz)["entities"]
        for etype in TYPES:
            exp = {_date_key(v) if etype == "DATE" else _fold(v) for v in expected.get(etype, [])}
            got_raw = {e["normalized"] for e in found if e["entity_type"] == etype}
            got = {_date_key(v) if etype == "DATE" else _fold(v) for v in got_raw}
            tp = len(exp & got)
            fp = len(got - exp)
            fn = len(exp - got)
            totals[etype]["tp"] += tp
            totals[etype]["fp"] += fp
            totals[etype]["fn"] += fn
            group_totals[group][etype]["tp"] += tp
            group_totals[group][etype]["fp"] += fp
            group_totals[group][etype]["fn"] += fn
            if not (exp or got):
                continue
            prec = tp / (tp + fp) if (tp + fp) else 1.0
            rec = tp / (tp + fn) if (tp + fn) else 1.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
            print(f"{doc_id[:10]:10} {case_id:9} {etype:13} {prec * 100:9.1f}% "
                  f"{rec * 100:7.1f}% {f1 * 100:5.1f}%  {tp:3} {fp:3} {fn:3}")
            for v in sorted(exp - got):
                misses.append(f"{doc_id} {etype}: MISSED   {v}")
            for v in sorted(got - exp):
                misses.append(f"{doc_id} {etype}: SPURIOUS  {v}")

    print("-" * 92)
    print(f"{'TYPE':13} {'precision':>10} {'recall':>8} {'F1':>6}   {'tp':>4} {'fp':>4} {'fn':>4}")
    tot_tp = tot_fp = tot_fn = 0
    for etype in TYPES:
        tp, fp, fn = totals[etype]["tp"], totals[etype]["fp"], totals[etype]["fn"]
        tot_tp += tp
        tot_fp += fp
        tot_fn += fn
        if not (tp or fp or fn):
            continue
        prec = tp / (tp + fp) if (tp + fp) else 1.0
        rec = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        print(f"{etype:13} {prec * 100:9.1f}% {rec * 100:7.1f}% {f1 * 100:5.1f}%   "
              f"{tp:4} {fp:4} {fn:4}")
    prec = tot_tp / (tot_tp + tot_fp) if (tot_tp + tot_fp) else 1.0
    rec = tot_tp / (tot_tp + tot_fn) if (tot_tp + tot_fn) else 1.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
    print("-" * 92)
    print(f"{'MICRO AVERAGE':13} {prec * 100:9.1f}% {rec * 100:7.1f}% {f1 * 100:5.1f}%   "
          f"{tot_tp:4} {tot_fp:4} {tot_fn:4}")
    print(f"\nlabelled mentions: {tot_tp + tot_fn}   correctly found: {tot_tp}   "
          f"spurious: {tot_fp}   missed: {tot_fn}")

    def _agg(scope: str, rows: dict) -> tuple[float, float, float, int, int, int]:
        tp = sum(rows[t]["tp"] for t in TYPES)
        fp = sum(rows[t]["fp"] for t in TYPES)
        fn = sum(rows[t]["fn"] for t in TYPES)
        p_ = tp / (tp + fp) if (tp + fp) else 1.0
        r_ = tp / (tp + fn) if (tp + fn) else 1.0
        f_ = 2 * p_ * r_ / (p_ + r_) if (p_ + r_) else 0.0
        return p_, r_, f_, tp, fp, fn

    print("\nper-type, THE 10 SEEDED DOCUMENTS ONLY (the set the previous pass measured,")
    print("so this table is directly comparable with the pre-hardening run):")
    print(f"{'TYPE':13} {'precision':>10} {'recall':>8} {'F1':>6}   {'tp':>4} {'fp':>4} {'fn':>4}")
    for etype in TYPES:
        tp, fp, fn = (group_totals["SEEDED"][etype][k] for k in ("tp", "fp", "fn"))
        if not (tp or fp or fn):
            continue
        p_ = tp / (tp + fp) if (tp + fp) else 1.0
        r_ = tp / (tp + fn) if (tp + fn) else 1.0
        f_ = 2 * p_ * r_ / (p_ + r_) if (p_ + r_) else 0.0
        mark = "  <- new in this pass" if etype == "ALIAS" else ""
        print(f"{etype:13} {p_ * 100:9.1f}% {r_ * 100:7.1f}% {f_ * 100:5.1f}%   "
              f"{tp:4} {fp:4} {fn:4}{mark}")

    print("\nper-source aggregate:")
    for scope, rows in (("the 10 seeded evidence documents", group_totals["SEEDED"]),
                        ("the real FIR PDF (dataset pack)", group_totals["DATASET_PDF"]),
                        ("ALL documents", totals)):
        p_, r_, f_, tp, fp, fn = _agg(scope, rows)
        print(f"   {scope:34} precision {p_ * 100:5.1f}%   recall {r_ * 100:5.1f}%   "
              f"F1 {f_ * 100:5.1f}%   (tp {tp}, fp {fp}, fn {fn})")

    alias = totals["ALIAS"]
    a_tp, a_fp, a_fn = alias["tp"], alias["fp"], alias["fn"]
    a_p = a_tp / (a_tp + a_fp) if (a_tp + a_fp) else 1.0
    a_r = a_tp / (a_tp + a_fn) if (a_tp + a_fn) else 1.0
    a_f = 2 * a_p * a_r / (a_p + a_r) if (a_p + a_r) else 0.0
    print(f"\nALIAS only (the type the second hardening pass fixed, scored here for the "
          f"first time):\n   precision {a_p * 100:.1f}%   recall {a_r * 100:.1f}%   "
          f"F1 {a_f * 100:.1f}%   tp {a_tp}  fp {a_fp}  fn {a_fn}")
    if misses:
        print("\nper-mention detail (what failed):")
        for line in misses:
            print("   ", line)
    return {"tp": tot_tp, "fp": tot_fp, "fn": tot_fn}, misses


def evaluate_negative_cases() -> dict[str, Any]:
    """Assertions of the form "this entity must NOT appear in this text".

    Precision measured only over the seeded documents can be passed by an extractor
    that invents confident nonsense in the same style; the negative set is the half
    of the harness that catches that. Each case also asserts something that MUST
    appear, so a fix that simply switches the heuristic off cannot pass.
    """
    data = json.load(open(os.path.join(EVAL_DIR, "labelled_entities.json")))
    cases = data.get("_negative_cases", [])
    gaz = _case_vocabulary()
    print()
    print(RULE)
    print("REPORT 1b - NEGATIVE CASES (text where an entity must NOT be extracted)")
    print(RULE)
    print(f"{'id':11} {'language':9} {'must NOT appear':30} {'':10} "
          f"{'must still appear':30} outcome")
    print("-" * 92)

    result: dict[str, Any] = {"total": 0, "ok": 0, "violations": [], "regressions": []}

    def _key(entry: dict[str, Any]) -> tuple[str, str]:
        """(type, folded value) - dates compared by day+month."""
        value = _date_key(entry["value"]) if entry["entity_type"] == "DATE" else entry["value"]
        return entry["entity_type"], _fold_any(value)

    def _indexes(entities: list[dict[str, Any]]) -> tuple[set, set]:
        """Match against the normalised value AND the raw surface span. A forbidden
        span therefore cannot be hidden behind a different normalisation, and a
        required entity counts as present whichever of the two carries it."""
        norm, surf = set(), set()
        for e in entities:
            date = e["entity_type"] == "DATE"
            norm.add((e["entity_type"], _fold_any(_date_key(e["normalized"]) if date
                                                  else e["normalized"])))
            surf.add((e["entity_type"], _fold_any(_date_key(e["surface"]) if date
                                                  else e["surface"])))
        return norm, surf

    for case in cases:
        text = document_agent.normalize_text(document_agent.clean_text(case["text"]))
        found = entity_agent.run(text, gaz)["entities"]
        by_norm, by_surface = _indexes(found)

        negatives = case["must_not_appear"]
        positives = case["must_appear"]
        rows = zip_longest(negatives, positives)
        for row, (negative, positive) in enumerate(rows):
            left, left_out = "", ""
            if negative is not None:
                bad = _key(negative) in by_norm or _key(negative) in by_surface
                result["total"] += 1
                result["ok"] += int(not bad)
                left_out = "FALSE POSITIVE" if bad else "not present"
                left = f"{negative['entity_type']} {negative['value']!r}"
                if bad:
                    result["violations"].append(
                        f"{case['id']}: {negative['entity_type']} {negative['value']!r} "
                        f"WAS extracted - {case['why']}")
            right, right_out = "", ""
            if positive is not None:
                key = _key(positive)
                ok = key in by_norm or key in by_surface
                result["total"] += 1
                result["ok"] += int(ok)
                right_out = "present" if ok else "MISSING"
                right = f"{positive['entity_type']} {positive['value']!r}"
                if not ok:
                    result["regressions"].append(
                        f"{case['id']}: {positive['entity_type']} {positive['value']!r} is "
                        f"MISSING - a negative assertion must not be passed by breaking "
                        f"the extractor")
            print(f"{(case['id'] if row == 0 else ''):11} "
                  f"{(case['language'] if row == 0 else ''):9} {left:30} {left_out:10} "
                  f"{right:30} {right_out}")

    print("-" * 92)
    print(f"assertions held ({len(cases)} cases, both halves of every assertion): "
          f"{result['ok']}/{result['total']}")
    for line in result["violations"]:
        print("    !! FALSE POSITIVE:", line)
    for line in result["regressions"]:
        print("    --  REGRESSION   :", line)
    return result


def _entity(label: str, attributes: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"label": label, "entity_type": "PERSON", "cases": ["CASE-101"],
            "attributes": attributes or {}}


def evaluate_resolution() -> dict[str, Any]:
    data = json.load(open(os.path.join(EVAL_DIR, "resolution_pairs.json")))
    print()
    print(RULE)
    print("REPORT 2 - ENTITY RESOLUTION TRAPS")
    print(RULE)
    print(f"candidate band (human review): score >= {RESOLUTION_MEDIUM}   "
          f"confident band (a HIGH proposal is what an officer is most likely to accept): "
          f"score >= {RESOLUTION_HIGH}")
    print("auto-merge is disabled in every case: the resolver proposes, a human decides.\n")

    results: dict[str, Any] = {"propose_total": 0, "propose_ok": 0, "nomatch_total": 0,
                               "nomatch_ok": 0, "false_merges": [], "missed_proposals": [],
                               "reviewable_traps": [], "unexpected_high": [],
                               "ident_total": 0, "ident_ok": 0, "ident_bad": []}

    print("--- (A) SAME ENTITY: must be surfaced as a reviewable candidate ---")
    print(f"{'a':20} {'b':22} {'score':>7} {'band':12} {'outcome':9} note")
    print("-" * 92)
    for pair in data["must_propose"]:
        a = _entity(pair["a"], pair.get("a_attributes"))
        b = _entity(pair["b"], pair.get("b_attributes"))
        result = resolution_agent.compare_pair(a, b)
        score = float(result["score"])
        ok = score >= RESOLUTION_MEDIUM
        results["propose_total"] += 1
        results["propose_ok"] += int(ok)
        if not ok:
            results["missed_proposals"].append(
                f"{pair['a']} <-> {pair['b']} scored {score} ({result['support_level']}) - "
                f"below the review threshold: {pair['note']}")
        if ok and score >= RESOLUTION_HIGH:
            pass
        print(f"{pair['a'][:20]:20} {pair['b'][:22]:22} {score:7.1f} "
              f"{result['support_level']:12} {'shown' if ok else 'MISSED':9} {pair['note'][:34]}")

    print()
    print("--- (B) DIFFERENT ENTITIES: must never reach the confident band ---")
    print(f"{'a':20} {'b':22} {'score':>7} {'band':12} {'outcome':9} note")
    print("-" * 92)
    for pair in data["must_not_merge"]:
        a = _entity(pair["a"], pair.get("a_attributes"))
        b = _entity(pair["b"], pair.get("b_attributes"))
        result = resolution_agent.compare_pair(a, b)
        score = float(result["score"])
        safe = score < RESOLUTION_HIGH
        results["nomatch_total"] += 1
        results["nomatch_ok"] += int(safe)
        if not safe:
            results["false_merges"].append(
                f"{pair['a']} vs {pair['b']} reached {score} ({result['support_level']}) - "
                f"{pair['note']}")
        elif score >= RESOLUTION_MEDIUM:
            results["reviewable_traps"].append(f"{pair['a']} vs {pair['b']} ({score})")
        print(f"{pair['a'][:20]:20} {pair['b'][:22]:22} {score:7.1f} "
              f"{result['support_level']:12} {'safe' if safe else 'FALSE MERGE':9} {pair['note'][:34]}")

    print()
    print("--- (C) IDENTIFIER OBJECTS: same object must fold to one graph key ---")
    print(f"{'type':8} {'a':18} {'b':18} {'keys':22} {'outcome':9} note")
    print("-" * 92)
    for pair in data["identifier_pairs"]:
        ka, kb = graph_ops.match_key(pair["type"], pair["a"]), graph_ops.match_key(pair["type"], pair["b"])
        collapsed = ka == kb
        ok = collapsed == bool(pair["same"])
        results["ident_total"] += 1
        results["ident_ok"] += int(ok)
        if not ok:
            results["ident_bad"].append(f"{pair['type']} {pair['a']} vs {pair['b']} "
                                        f"(collapsed={collapsed}) - {pair['note']}")
        verdict_keys = "same graph key" if collapsed else "different keys"
        print(f"{pair['type']:8} {pair['a'][:18]:18} {pair['b'][:18]:18} "
              f"{verdict_keys:22} {'ok' if ok else 'WRONG':9} {pair['note'][:30]}")

    propose_recall = results["propose_ok"] / results["propose_total"] * 100
    safety = results["nomatch_ok"] / results["nomatch_total"] * 100
    ident_acc = results["ident_ok"] / results["ident_total"] * 100
    print()
    print("-" * 92)
    print(f"(A) same-entity pairs shown for review   : {results['propose_ok']}/{results['propose_total']}"
          f"  ({propose_recall:.1f}% recall)")
    print(f"(B) different-entity pairs kept apart    : {results['nomatch_ok']}/{results['nomatch_total']}"
          f"  ({safety:.1f}%)")
    print(f"    FALSE MERGES (the number to protect) : {len(results['false_merges'])}")
    print(f"    of the traps, {len(results['reviewable_traps'])} reach the candidate band and "
          f"therefore need an explicit human rejection, never an automatic merge")
    print(f"(C) identifier objects folded correctly  : {results['ident_ok']}/{results['ident_total']}"
          f"  ({ident_acc:.1f}%)")
    for line in results["false_merges"]:
        print("    !!", line)
    for line in results["missed_proposals"]:
        print("    -- ", line)
    for line in results["ident_bad"]:
        print("    -- ", line)
    return results


def main() -> int:
    extraction, _ = evaluate_extraction()
    negative = evaluate_negative_cases()
    resolution = evaluate_resolution()
    print()
    print(RULE)
    ok = (not resolution["false_merges"] and extraction["tp"] > 0
          and not negative["violations"] and not negative["regressions"])
    print("PHASE 6 HARNESS: " + ("PASS" if ok else "FAIL") +
          f"   |  extraction micro-F1 sample size {extraction['tp'] + extraction['fn']} mentions"
          f"   |  negative assertions {negative['ok']}/{negative['total']}"
          f"   |  false merges {len(resolution['false_merges'])}")
    print(RULE)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
