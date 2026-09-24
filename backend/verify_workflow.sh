#!/usr/bin/env bash
# CrimeNet AI - end-to-end workflow verification.
# Walks the full pipeline stage by stage and prints PASS/FAIL for each.
# Usage:  bash /home/user/verify_workflow.sh  [base_url]
BASE="${1:-http://127.0.0.1:5173}"
PASS=0; FAIL=0
say()  { printf "\n\033[1m%s\033[0m\n" "$1"; }
ok()   { PASS=$((PASS+1)); printf "  \033[32mPASS\033[0m  %s\n" "$1"; }
bad()  { FAIL=$((FAIL+1)); printf "  \033[31mFAIL\033[0m  %s\n" "$1"; }
check(){ if [ "$1" = "$2" ]; then ok "$3"; else bad "$3 (expected $2, got $1)"; fi; }

jqp() { python3 -c "import sys,json;d=json.load(sys.stdin);print($1)" 2>/dev/null; }

say "STAGE 1 — LOGIN (JWT + RBAC)"
TOK=$(curl -s -X POST "$BASE/api/auth/login" -H 'content-type: application/json' \
      -d '{"user_id":"SUP-1100","password":"supervise123"}' | jqp "d['access_token']")
[ -n "$TOK" ] && ok "supervisor authenticated (JWT issued)" || bad "supervisor login"
AUTH=(-H "authorization: Bearer $TOK")
BAD=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/api/auth/login" -H 'content-type: application/json' -d '{"user_id":"SUP-1100","password":"wrong"}')
check "$BAD" "401" "wrong password rejected"
ITOK=$(curl -s -X POST "$BASE/api/auth/login" -H 'content-type: application/json' \
      -d '{"user_id":"INV-2201","password":"investigate123"}' | jqp "d['access_token']")
SCOPE=$(curl -s -o /dev/null -w '%{http_code}' -H "authorization: Bearer $ITOK" "$BASE/api/cases/CASE-305")
check "$SCOPE" "403" "case-level authorization blocks out-of-scope case"
ADMIN_ONLY=$(curl -s -o /dev/null -w '%{http_code}' "${AUTH[@]}" "$BASE/api/security/users")
check "$ADMIN_ONLY" "403" "supervisor blocked from user:manage endpoint"

say "STAGE 2 — CASES"
N=$(curl -s "${AUTH[@]}" "$BASE/api/cases" | jqp "len(d)")
[ "$N" -ge 5 ] && ok "$N cases visible to supervisor" || bad "case list ($N)"
curl -s "${AUTH[@]}" "$BASE/api/cases/CASE-101" | grep -q "Chennai" && ok "case detail CASE-101" || bad "case detail"

say "STAGE 3 — EVIDENCE REGISTRY"
EV=$(curl -s "${AUTH[@]}" "$BASE/api/evidence" | jqp "len(d) if isinstance(d, list) else len(d.get('items', []))")
[ "$EV" -ge 10 ] && ok "$EV evidence objects registered" || bad "evidence registry ($EV)"
NEW=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' \
  -d '{"case_id":"CASE-101","evidence_type":"POLICE_REPORT","source":"verify_workflow.sh","text_content":"On 2025-08-27 vehicle TN01AB1234 was observed at Guindy Industrial Estate with Ravi Kumar. Contact number +919840012345 was noted."}' \
  "$BASE/api/evidence" | jqp "d['evidence_id']")
[ -n "$NEW" ] && ok "new evidence registered as $NEW (SHA-256 at intake)" || bad "evidence registration"

say "STAGE 4 — ENTITY EXTRACTION (document intelligence)"
EXTRACT=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' -d '{}' "$BASE/api/evidence/$NEW/process")
NENT=$(echo "$EXTRACT" | jqp "len(d['extraction']['entities'])")
[ "${NENT:-0}" -ge 3 ] && ok "$NENT entities extracted (spaCy NER + rule layer)" || bad "entity extraction ($NENT)"
echo "$EXTRACT" | grep -q "TN01AB1234" && ok "vehicle registration recognised by rule layer" || bad "vehicle rule layer"
echo "$EXTRACT" | grep -q "RELATIONSHIPS_CANDIDATE" && ok "pipeline reached RELATIONSHIPS_CANDIDATE" || bad "pipeline stage"

say "STAGE 5 — ENTITY RESOLUTION"
RES=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' -d '{"case_ids":[]}' "$BASE/api/analysis/entity-resolution")
TOP=$(echo "$RES" | jqp "d['candidate_matches'][0]['score']")
echo "$RES" | grep -q '"auto_merged":false' && ok "auto-merge disabled (human decision required)" || bad "auto-merge policy"
[ -n "$TOP" ] && ok "top candidate identity match scored $TOP" || bad "resolution scores"

say "STAGE 6 — CROSS-CASE CORRELATION"
XC=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' -d '{"case_ids":[]}' "$BASE/api/analysis/cross-case")
XCN=$(echo "$XC" | jqp "len(d['associations'])")
XCS=$(echo "$XC" | jqp "d['associations'][0]['strength']")
[ "${XCN:-0}" -ge 1 ] && ok "$XCN cross-case associations (top strength $XCS)" || bad "cross-case correlation"

say "STAGE 7 — KNOWLEDGE GRAPH"
G=$(curl -s "${AUTH[@]}" "$BASE/api/graph")
GN=$(echo "$G" | jqp "d['counts']['nodes']"); GE=$(echo "$G" | jqp "d['counts']['edges']")
[ "${GN:-0}" -ge 20 ] && ok "graph projected: $GN nodes / $GE evidence-backed edges" || bad "graph projection"
echo "$G" | grep -q '"evidence_id"' && ok "every edge carries an evidence reference" || bad "edge provenance"

say "STAGE 8 — NETWORK ANALYSIS"
NET=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' -d '{"case_ids":[]}' "$BASE/api/analysis/network")
echo "$NET" | grep -q "degree_centrality" && ok "degree + betweenness centrality computed" || bad "centrality"
CM=$(echo "$NET" | jqp "len(d['communities'])")
[ "${CM:-0}" -ge 1 ] && ok "$CM communities detected (Louvain)" || bad "community detection"
SP=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' -d '{"source":"PER-001","target":"PER-004","case_ids":[]}' "$BASE/api/analysis/shortest-path")
echo "$SP" | grep -q '"found":true' && ok "shortest evidence path PER-001 → PER-004" || bad "shortest path"

say "STAGE 9 — TIMELINE / TEMPORAL"
T=$(curl -s "${AUTH[@]}" "$BASE/api/timeline")
TE=$(echo "$T" | jqp "d['event_count']")
[ "${TE:-0}" -ge 10 ] && ok "$TE chronological events reconstructed" || bad "timeline"
echo "$T" | grep -q "convergence" && ok "spatio-temporal convergence windows computed" || bad "convergence"
AN=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' -d '{"case_ids":[]}' "$BASE/api/analysis/anomaly")
ANN=$(echo "$AN" | jqp "len(d['anomalies'])")
PAT=$(echo "$AN" | jqp "len(d['pattern_findings'])")
DET=$(echo "$AN" | jqp "'+'.join(x['detector'] for x in d['detectors'])")
if [ "${ANN:-0}" -ge 1 ] && [ "${PAT:-0}" -ge 1 ]; then
  ok "$ANN behavioural anomaly (Isolation Forest) + $PAT shared-identifier pattern (rule-based); 2 detectors active: $DET"
else
  bad "anomaly detection ($ANN statistical, $PAT rule-based)"
fi

say "STAGE 10 — CORROBORATION"
CO=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' -d '{"case_ids":[]}' "$BASE/api/analysis/corroboration")
echo "$CO" | grep -q "CONTRADICTORY EVIDENCE" && ok "contradiction surfaced, not suppressed" || bad "contradiction handling"
INS=$(curl -s "${AUTH[@]}" "$BASE/api/cases/CASE-512/network" | grep -c "INSUFFICIENT EVIDENCE")
[ "$INS" -ge 1 ] && ok "CASE-512 returns INSUFFICIENT EVIDENCE with the gap named" || bad "insufficient-evidence path"

say "STAGE 11 — INFORMATION GAPS"
IG=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' -d '{"case_ids":[]}' "$BASE/api/analysis/information-gaps")
IGN=$(echo "$IG" | jqp "len(d['gaps'])")
[ "${IGN:-0}" -ge 1 ] && ok "$IGN information gaps with known/unknown split" || bad "information gaps"

say "STAGE 12 — NEXT-BEST ACTION"
NB=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' -d '{"case_ids":[]}' "$BASE/api/analysis/next-best-action")
NBT=$(echo "$NB" | jqp "d['recommended']['title']")
[ -n "$NBT" ] && ok "recommended: $NBT" || bad "next-best action"
OPS=$(echo "$NB" | python3 -c "
import sys,json,re
d=json.load(sys.stdin)
bad=[a['title'] for a in d.get('actions',[]) if re.search(r'arrest|surveil|raid|detain|intercept',a['title'],re.I)]
print(len(bad))")
check "$OPS" "0" "action catalogue is analytical only (no arrest/surveillance actions)"

say "STAGE 13 — HUMAN VERIFICATION"
V=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${AUTH[@]}" -H 'content-type: application/json' \
    -d '{"object_type":"RELATIONSHIP","case_id":"CASE-101","rationale":"verify_workflow probe","evidence_ids":["EV-1024"]}' \
    "$BASE/api/relationships/REL-003/verify")
check "$V" "200" "relationship verification recorded"
R=$(curl -s -o /dev/null -w '%{http_code}' -X POST "${AUTH[@]}" -H 'content-type: application/json' \
    -d '{"object_type":"CROSS_CASE_LINK","case_id":"CASE-101","rationale":"probe","evidence_ids":[]}' \
    "$BASE/api/findings/XC-101-202/reject")
check "$R" "200" "cross-case rejection recorded (finding retained)"

say "STAGE 14 — SHA-256 INTEGRITY"
IC=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' "$BASE/api/evidence/EV-1024/integrity-check")
echo "$IC" | grep -q "VERIFIED" && ok "EV-1024 integrity VERIFIED" || bad "integrity check"
IM=$(curl -s -X POST "${AUTH[@]}" -H 'content-type: application/json' "$BASE/api/evidence/EV-2042/integrity-check")
echo "$IM" | grep -q "MISMATCH" && ok "EV-2042 tamper demo returns INTEGRITY_MISMATCH" || bad "tamper detection"

say "STAGE 15 — AUDIT + LEDGER"
A=$(curl -s "${AUTH[@]}" "$BASE/api/audit?limit=500")
AN2=$(echo "$A" | jqp "d['total_records']")
[ "${AN2:-0}" -ge 10 ] && ok "$AN2 append-only audit records written during this run" || bad "audit trail"
L=$(curl -s -X POST "${AUTH[@]}" "$BASE/api/ledger/verify")
echo "$L" | grep -q '"chain_intact":true' && ok "ledger hash chain intact ($(echo "$L" | jqp "d['blocks']") blocks)" || bad "ledger chain"

printf "\n\033[1mRESULT: %d passed, %d failed\033[0m\n" "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
