"""PART A acceptance proofs (A2, A3, A5, A6, A7) against the live API.

Kept in the workspace (not /tmp) so the proofs survive a sandbox recycle:
    python3 scripts/partA_proofs.py            # all sections
    python3 scripts/partA_proofs.py a3 a6      # selected sections
"""
import json, sys, urllib.error, urllib.request

BASE = "http://127.0.0.1:8000"

def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("content-type", "application/json")
    if token: req.add_header("authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    try:
        with urllib.request.urlopen(req, data) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return {"__error__": e.code, "body": e.read().decode()[:300]}

def audit_records(tok, action=None):
    """GET /api/audit returns {count, records, total_records, chain, ...}; unwrap it."""
    q = "/api/audit?limit=500" + (f"&action={action}" if action else "")
    d = call("GET", q, tok)
    if isinstance(d, dict):
        return d.get("records", d.get("items", []))
    return d


def login(uid="SUP-1100", pw="supervise123"):
    return call("POST", "/api/auth/login", body={"user_id": uid, "password": pw})["access_token"]

def rule(t): print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)

# ─────────────────────────────────────────────────────────── A2 ──────────────
def a2(tok):
    rule("A2 — EXPLAINABLE KEY INFLUENCERS   (POST /api/analysis/network)")
    d = call("POST", "/api/analysis/network", tok, {"case_ids": []})
    print(f"engine={d['engine']}  nodes={d['nodes']}  edges={d['edges']}  "
          f"communities={len(d['communities'])}  modularity={d['modularity']}")
    interps = []
    for key in ("degree_centrality", "betweenness_centrality"):
        print(f"\n--- {key.upper()} (full) ---")
        for r in d[key]:
            interps.append(r["interpretation"])
            print(f"#{r['rank']:<2} {r['label']:<26} [{r['entity_type']:<12}] score={r['score']}")
            print(f"     interpretation: {r['interpretation']}")
            print(f"     interpretation_basis: {r.get('interpretation_basis')}")
    print(f"\ninterpretation strings: {len(set(interps))} distinct of {len(interps)} rows")
    print(f"safety_note: {d.get('safety_note')}")
    # every interpretation must name a number
    import re
    non_numeric = [i for i in interps if not re.search(r"\d", i)]
    print(f"interpretations containing no number: {len(non_numeric)}  (must be 0)")

# ─────────────────────────────────────────────────────────── A3 ──────────────
def a3(tok):
    rule("A3 — TWO LABELLED DETECTORS   (POST /api/analysis/anomaly)")
    d = call("POST", "/api/analysis/anomaly", tok, {"case_ids": []})
    print(f"detector_count: {d.get('detector_count')}")
    for det in d.get("detectors", []):
        print(f"  - {det}")
    print()
    findings = d.get("anomalies", []) + d.get("pattern_findings", [])
    for f in findings:
        print(f"[{f.get('detector')}]  kind={f.get('detector_kind')}  model={f.get('model')}")
        for k in ("account_id", "case_id", "window", "observed", "baseline", "anomaly_score",
                  "evidence_ids", "interpretation", "reason", "pattern", "why", "evidence_id"):
            if f.get(k) is not None:
                print(f"   {k:<14}: {f[k]}")
        print()
    kinds = {f.get("detector") for f in findings}
    print(f"distinct detectors represented in findings: {len(kinds)} -> {sorted(kinds)}")

# ─────────────────────────────────────────────────────────── A5 ──────────────
def a5(tok, evidence_id="EV-1024"):
    rule(f"A5 — READ-ACCESS AUDIT   (GET /api/evidence/{evidence_id})")
    n_before = len(audit_records(tok, "EVIDENCE_VIEWED"))
    call("GET", f"/api/evidence/{evidence_id}", tok)
    records = audit_records(tok, "EVIDENCE_VIEWED")
    print(f"EVIDENCE_VIEWED records before this read: {n_before}  -> after: {len(records)}")
    print("newest record:")
    print(json.dumps(records[0], indent=2, ensure_ascii=False))
    # prove the LIST endpoint adds nothing
    n_mid = len(audit_records(tok, "EVIDENCE_VIEWED"))
    call("GET", "/api/evidence", tok)
    n_after_list = len(audit_records(tok, "EVIDENCE_VIEWED"))
    print(f"\nlist endpoint (GET /api/evidence) added records: {n_after_list - n_mid}  (must be 0)")

# ─────────────────────────────────────────────────────────── A6 ──────────────
RAW = "9840012345"
def a6(tok):
    rule("A6 — MASKED IDENTIFIER LABELS + AUDITED REVEAL   (policy (a))")
    g = call("GET", "/api/graph", tok)
    # /api/graph returns Cytoscape-shaped nodes: the attributes live under .data
    nodes = [n.get("data", n) for n in g.get("nodes", [])]
    masked = [n for n in nodes if n.get("identifier_masked")]
    print(f"nodes with identifier_masked: {len(masked)} / {len(nodes)}")
    for n in masked:
        print(f"  {n['id']:<9} {n.get('entity_type'):<8} label={n.get('label'):<22} "
              f"reveal_endpoint={n.get('reveal_endpoint')}")
    print(f"\ngraph pii_policy: {g.get('pii_policy')}")

    rev = call("GET", "/api/entities/PHN-001/reveal", tok)
    print("\nreveal (GET /api/entities/PHN-001/reveal):")
    print(json.dumps(rev, indent=2, ensure_ascii=False))

    recs = audit_records(tok, "IDENTIFIER_REVEALED")
    if recs:
        print("\nnewest IDENTIFIER_REVEALED audit record:")
        print(json.dumps(recs[0], indent=2, ensure_ascii=False))

    print("\nleak scan — raw digits", RAW, "in every entity-bearing response:")
    endpoints = [
        ("GET", "/api/graph", None), ("GET", "/api/entities?entity_type=PHONE", None),
        ("GET", "/api/entities/PHN-001", None), ("POST", "/api/analysis/network", {"case_ids": []}),
        ("POST", "/api/analysis/cross-case", {"case_ids": []}),
        ("POST", "/api/analysis/corroboration", {"case_ids": []}),
        ("GET", "/api/timeline", None), ("GET", "/api/map", None),
        ("GET", f"/api/search?q={RAW}", None),
        ("POST", "/api/analysis/entity-resolution", {"case_ids": []}),
    ]
    leaked = 0
    for method, path, body in endpoints:
        got = call(method, path, tok, body)
        body_text = json.dumps(got, ensure_ascii=False)
        n = body_text.count(RAW)
        leaked += n
        print(f"  {'LEAK' if n else 'clean'} {method:<4} {path:<45} raw occurrences: {n}")
    print(f"\nRESULT: {'PASS - no endpoint leaks the raw identifier' if leaked == 0 else 'FAIL - raw identifier leaked'}")

# ─────────────────────────────────────────────────────────── A7 ──────────────
def a7(tok):
    rule("A7 — SOURCE-TRUST WEIGHTING   (POST /api/analysis/evidence-support / corroboration)")
    import random, time

    # ---- 1. the ladder, read straight off the API -------------------------
    # unique identifiers per run: reusing one would (correctly) make the engine link every
    # A7 run into a single lead and muddy the comparison.
    reg = f"TN{random.randint(10, 99)}{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{random.randint(1000, 9999)}"
    ph = f"+9198{random.randint(10000000, 99999999)}"
    ext = call("POST", "/api/evidence", tok, {
        "case_id": "CASE-101", "evidence_type": "INTELLIGENCE_REPORT",
        "source": "External partner feed (A7 ladder)",
        "source_trust": "EXTERNAL_SUBMISSION",
        "text_content": f"Partner feed note: vehicle {reg} and contact {ph} recorded.",
    })
    ext_id = ext.get("evidence_id")
    call("POST", f"/api/evidence/{ext_id}/process", tok)

    print("the ladder (POST /api/analysis/evidence-support):\n")
    rows = [(["EV-1024", "EV-1025"], "2 x OFFICER_UPLOAD"),
            (["EV-1024", ext_id], "1 x OFFICER_UPLOAD + 1 x EXTERNAL_SUBMISSION")]
    for ids, label in rows:
        r = call("POST", "/api/analysis/evidence-support", tok, {"evidence_ids": ids})
        if "__error__" in r:
            print(f"  {label}: {ids} unavailable ({r['__error__']})"); continue
        print(f"  {label:<38} ({' + '.join(ids)})")
        print(f"     weighted_support       : {r.get('weighted_support')}")
        print(f"     independent_sources    : {r.get('independent_sources')}")
        print(f"     support_level_reachable: {r.get('support_level_reachable')}")
        print(f"     sources                : {[(x.get('source'), x.get('source_trust'), x.get('weight')) for x in r.get('sources', [])]}")
        print(f"     explanation            : {r.get('explanation')}\n")

    # ---- 2. controlled A/B: same documents, same relationship, only trust differs

    def pair(tag, trust):
        """Two fresh cases with the SAME document, uploaded under `trust`."""
        # a fresh identifier + name per ARM, so the two arms cannot be linked to each other.
        # (shared vehicle + shared phone + shared name = three supporting signals, which is
        #  what the correlation engine needs before it will call a pair HIGH at all)
        reg2 = f"TN{random.randint(10, 99)}{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{random.randint(1000, 9999)}"
        ph2 = f"+9197{random.randint(10000000, 99999999)}"
        given = random.choice(["Arun", "Vignesh", "Prakash", "Karthik", "Suresh", "Mahesh", "Dinesh", "Naveen"])
        surname = random.choice(["Prakash", "Krishnan", "Balaji", "Raghavan", "Sundaram", "Verma", "Nair", "Pillai"])
        person = f"{given} {surname}"
        TEXT = (f"{person} was observed at the scene with vehicle {reg2} on 2025-09-01; "
                f"contact {ph2} was recorded in the same note.")
        # a fresh identifier + name per ARM, so the two arms cannot be linked to each other.
        # (shared vehicle + shared phone + shared name = three supporting signals, which is
        #  what the correlation engine needs before it will call a pair HIGH at all)
        reg2 = f"TN{random.randint(10, 99)}{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{random.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}{random.randint(1000, 9999)}"
        ph2 = f"+9197{random.randint(10000000, 99999999)}"
        given = random.choice(["Arun", "Vignesh", "Prakash", "Karthik", "Suresh", "Mahesh", "Dinesh", "Naveen"])
        surname = random.choice(["Prakash", "Krishnan", "Balaji", "Raghavan", "Sundaram", "Verma", "Nair", "Pillai"])
        person = f"{given} {surname}"
        TEXT = (f"{person} was observed at the scene with vehicle {reg2} on 2025-09-01; "
                f"contact {ph2} was recorded in the same note.")
        n = random.randint(100, 899)
        ids = []
        for k in (1, 2):
            cid = f"CASE-{n}{k}"
            while call("GET", f"/api/cases/{cid}", tok).get("__error__") != 404:
                n = random.randint(100, 899); cid = f"CASE-{n}{k}"
            call("POST", "/api/cases", tok, {"case_id": cid, "title": f"A7 proof {cid} ({tag})",
                                             "case_type": "TEST", "status": "OPEN", "priority": "LOW",
                                             "classification": "SYNTHETIC DEMONSTRATION DATA"})
            ev = call("POST", "/api/evidence", tok, {"case_id": cid, "evidence_type": "INTELLIGENCE_REPORT",
                                                     "source": f"A7 {tag} feed {cid}",
                                                     "source_trust": trust, "text_content": TEXT})
            eid = ev["evidence_id"]
            call("POST", f"/api/evidence/{eid}/process", tok)
            ids.append((cid, eid))
        return ids, TEXT

    print("controlled A/B — identical document, identical candidate relationship;")
    print("only the DECLARED source trust of the two uploads differs:\n")
    for tag, trust in (("EXTERNAL", "EXTERNAL_SUBMISSION"), ("OFFICER", "OFFICER_UPLOAD")):
        ids, doc = pair(tag, trust)
        for cid, eid in ids:
            print(f"  [{tag}] {cid} <- {eid}  source_trust={trust}")
        pair_ids = [c for c, _ in ids]
        corr = call("POST", "/api/analysis/corroboration", tok, {"case_ids": pair_ids})
        lead = next((l for l in corr.get("leads", [])
                     if set(l.get("case_ids", [])) == set(pair_ids)), {})
        tb = lead.get("source_trust_breakdown") or {}
        print(f"    document shared by both cases: {doc}")
        print(f"    lead {lead.get('lead_id')}: status={lead.get('status')}")
        print(f"    support_level={lead.get('support_level')}  raw={lead.get('support_level_raw')}  "
              f"capped_by_source_trust={lead.get('support_level_capped_by_source_trust')}  "
              f"weighted={lead.get('weighted_support')}  sources={lead.get('independent_sources')}")
        if lead.get("support_level_cap_reason"):
            print(f"    cap reason: {lead['support_level_cap_reason']}")
        if isinstance(tb, dict):
            print(f"    weights used: {tb.get('weights')}")
        print()


SECTIONS = {"a2": a2, "a3": a3, "a5": a5, "a6": a6, "a7": a7}
if __name__ == "__main__":
    wanted = [a for a in sys.argv[1:] if a in SECTIONS] or list(SECTIONS)
    tok = login()
    for name in wanted:
        SECTIONS[name](tok)
