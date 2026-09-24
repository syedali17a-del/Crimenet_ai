"""A1 acceptance test - the brief's EXACT reproduction, through the live API.

POST /api/evidence (case CASE-101, type FIR, the Hindi sentence from the report)
POST /api/evidence/{id}/process
=> "फोन" must not appear as PERSON or any other type.
Then the same for the exact Tamil sentence, where "ரவி குமார்" must STILL be PERSON.
"""
import json, urllib.request

BASE = "http://127.0.0.1:8000"

def call(method, path, token=None, body=None):
    req = urllib.request.Request(BASE + path, method=method)
    req.add_header("content-type", "application/json")
    if token: req.add_header("authorization", f"Bearer {token}")
    data = json.dumps(body).encode() if body is not None else None
    with urllib.request.urlopen(req, data) as r:
        return json.loads(r.read().decode())

TOK = call("POST", "/api/auth/login", body={"user_id": "SUP-1100", "password": "supervise123"})["access_token"]

CASES = [
    ("HINDI", "रवि कुमार को 12 अगस्त को वाहन TN01AB1234 के साथ चेन्नई सेंट्रल में देखा गया। "
              "फोन +919840012345 दर्ज किया गया।"),
    ("TAMIL", "ரவி குமார் 12 ஆகஸ்ட் அன்று TN01AB1234 வாகனத்துடன் சென்னை சென்ட்ரலில் காணப்பட்டார்."),
]
FORBIDDEN = ["फोन", "फ़ोन", "मोबाइल", "செல்போன்", "போன்"]

results = {}
for label, text in CASES:
    ev = call("POST", "/api/evidence", TOK, {
        "case_id": "CASE-101", "evidence_type": "FIR", "text_content": text,
        "source": f"A1 acceptance test ({label})", "source_trust": "OFFICER_UPLOAD",
    })
    eid = ev["evidence_id"]
    proc = call("POST", f"/api/evidence/{eid}/process", TOK)
    detail = call("GET", f"/api/evidence/{eid}", TOK)
    ents = (detail.get("extraction") or {}).get("entities") or []
    counts = (detail.get("extraction") or {}).get("counts") or {}
    rows = [(e.get("entity_type"), e.get("surface"), e.get("normalized"), e.get("confidence"),
             e.get("methods") or e.get("extraction_methods")) for e in ents]
    results[label] = {"evidence_id": eid, "text": text, "rows": rows,
                      "pipeline": proc.get("status") or proc.get("pipeline_state")}
    print(f"=== {label}   evidence_id={eid}   case=CASE-101")
    print(f"    POST /api/evidence -> {eid}   POST /api/evidence/{eid}/process -> "
          f"{detail['evidence']['processing_status']}")
    print(f"    extraction counts: {counts}")
    for t, s, n, c, m in sorted(rows):
        print(f"      {t:<10} surface={s!r:<34} normalized={n!r:<24} conf={c}  {m}")
    banned = [r for r in rows if r[0] == "PERSON" and r[1].strip() in FORBIDDEN]
    anybanned = [r for r in rows if r[1].strip() in FORBIDDEN]
    persons = [r[1] for r in rows if r[0] == "PERSON"]
    print(f"    ASSERT 'फोन' as PERSON/any type        : {bool(banned or anybanned)}   (must be False)")
    print(f"    ASSERT PERSON surfaces                  : {persons}")
    print()

hi, ta = results["HINDI"], results["TAMIL"]
def lines(r):
    return [f"   {t:<10} {s!r:<34} -> {n!r:<22} conf={c}" for t, s, n, c, m in sorted(r["rows"])]

print("=" * 100)
print("SIDE-BY-SIDE (rendered as a unified diff of the extracted-set, both languages)")
print("=" * 100)
import difflib
diff = list(difflib.unified_diff(lines(hi), lines(ta),
                                 fromfile="HINDI  (the reported false positive)",
                                 tofile="TAMIL  (the regression guard)", lineterm=""))
for d in diff: print(d)

ok = (not [r for r in hi["rows"] if r[1].strip() in FORBIDDEN]
      and not [r for r in ta["rows"] if r[1].strip() in FORBIDDEN]
      and any(r[0] == "PERSON" and r[2] == "Ravi Kumar" for r in ta["rows"]))
print()
print(f"RESULT: {'PASS' if ok else 'FAIL'} — 'फोन' extracted as any type: "
      f"{bool([r for r in hi['rows'] if r[1].strip() in FORBIDDEN])}; "
      f"Tamil PERSON 'ரவி குமார்' -> Ravi Kumar: "
      f"{any(r[0]=='PERSON' and r[2]=='Ravi Kumar' for r in ta['rows'])}")
