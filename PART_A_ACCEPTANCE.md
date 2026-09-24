# PART A acceptance record — SIH26189 remaining gaps

Everything below is a real paste from this workspace, produced against the running API on the
seeded 5-case dataset. Re-running any line is enough to reproduce it — commands are given per
section, and the raw logs are kept in `artifacts/`.

**Environment note.** `backend/verify_workflow.sh` defaults to the Vite dev server on port 5173
(which proxies `/api` to :8000); pass a base URL to hit the API directly. A restart reseeds the
synthetic dataset, so proofs that create their own cases (`scripts/partA_proofs.py a7`) are
self-contained and use fresh identifiers each run.

---

## A1 — Hindi false positive (the exact sentence, through the real API)

`scripts/a1_api_repro.py` posts the brief's exact sentence to `POST /api/evidence` as an FIR on
CASE-101, runs `POST /api/evidence/{id}/process`, and reads back the extraction. Both halves of
the requirement are asserted, and the two languages are printed as a diff of the extracted set:

```text
=== HINDI   evidence_id=EV-5127   case=CASE-101
    POST /api/evidence -> EV-5127   POST /api/evidence/EV-5127/process -> RELATIONSHIPS_CANDIDATE
    extraction counts: {'DATE': 1, 'LOCATION': 1, 'PERSON': 1, 'PHONE': 1, 'VEHICLE': 1}
      DATE       surface='12 अगस्त'                         normalized='12 August'              conf=0.85  ['indic-date-vocabulary']
      LOCATION   surface='चेन्नई सेंट्रल'                   normalized='Chennai Central'        conf=0.82  ['indic-transliteration+vocabulary']
      PERSON     surface='रवि कुमार'                        normalized='Ravi Kumar'             conf=0.82  ['indic-transliteration+vocabulary']
      PHONE      surface='+919840012345'                    normalized='+919840012345'          conf=0.9  ['regex']
      VEHICLE    surface='TN01AB1234'                       normalized='TN01AB1234'             conf=0.98  ['regex', 'gazetteer']
    ASSERT 'फोन' as PERSON/any type        : False   (must be False)
    ASSERT PERSON surfaces                  : ['रवि कुमार']

=== TAMIL   evidence_id=EV-5128   case=CASE-101
    POST /api/evidence -> EV-5128   POST /api/evidence/EV-5128/process -> RELATIONSHIPS_CANDIDATE
    extraction counts: {'DATE': 1, 'LOCATION': 1, 'PERSON': 1, 'VEHICLE': 1}
      DATE       surface='12 ஆகஸ்ட்'                        normalized='12 August'              conf=0.85  ['indic-date-vocabulary']
      LOCATION   surface='சென்னை சென்ட்ரலில்'               normalized='Chennai Central'        conf=0.82  ['indic-transliteration+vocabulary']
      PERSON     surface='ரவி குமார்'                       normalized='Ravi Kumar'             conf=0.82  ['indic-transliteration+vocabulary']
      VEHICLE    surface='TN01AB1234'                       normalized='TN01AB1234'             conf=0.98  ['regex', 'gazetteer']
    ASSERT 'फोन' as PERSON/any type        : False   (must be False)
    ASSERT PERSON surfaces                  : ['ரவி குமார்']

====================================================================================================
SIDE-BY-SIDE (rendered as a unified diff of the extracted-set, both languages)
====================================================================================================
--- HINDI  (the reported false positive)
+++ TAMIL  (the regression guard)
@@ -1,5 +1,4 @@
-   DATE       '12 अगस्त'                         -> '12 August'            conf=0.85
-   LOCATION   'चेन्नई सेंट्रल'                   -> 'Chennai Central'      conf=0.82
-   PERSON     'रवि कुमार'                        -> 'Ravi Kumar'           conf=0.82
-   PHONE      '+919840012345'                    -> '+919840012345'        conf=0.9
+   DATE       '12 ஆகஸ்ட்'                        -> '12 August'            conf=0.85
+   LOCATION   'சென்னை சென்ட்ரலில்'               -> 'Chennai Central'      conf=0.82
+   PERSON     'ரவி குமார்'                       -> 'Ravi Kumar'           conf=0.82
    VEHICLE    'TN01AB1234'                       -> 'TN01AB1234'           conf=0.98

RESULT: PASS — 'फोन' extracted as any type: False; Tamil PERSON 'ரவி குமார்' -> Ravi Kumar: True
```

Negative cases in `backend/eval/labelled_entities.json` (rows NEG-HI-01…04, NEG-TA-01) assert that
`फोन`, `मोबाइल फोन`, `मोबाइल`, `संदेश`, `शिकायत` and `செல்போன்` are extracted as **no type at all**,
while the true entities in the same sentence are still found — 23/23 assertions held:

```text
REPORT 1b - NEGATIVE CASES (text where an entity must NOT be extracted)
============================================================================================
id          language  must NOT appear                           must still appear              outcome
--------------------------------------------------------------------------------------------
NEG-HI-01   hi        PERSON 'फोन'                   not present PERSON 'Ravi Kumar'            present
                      LOCATION 'फोन'                 not present PHONE '+919840012345'          present
                                                                DATE '12 August'               present
NEG-HI-02   hi        PERSON 'मोबाइल फोन'            not present PERSON 'Ravi Kumar'            present
                      PERSON 'मोबाइल'                not present VEHICLE 'TN01AB1234'           present
                      PERSON 'फोन'                   not present                                
                      LOCATION 'मोबाइल फोन'          not present                                
NEG-HI-03   hi        PERSON 'संदेश'                 not present PERSON 'Ravi Kumar'            present
                      LOCATION 'संदेश'               not present DATE '11 August'               present
NEG-HI-04   hi        PERSON 'शिकायत'                not present PERSON 'Ravi Kumar'            present
                      LOCATION 'शिकायत'              not present PHONE '+919840012345'          present
NEG-TA-01   ta        PERSON 'செல்போன்'              not present PERSON 'Ravi Kumar'            present
                      LOCATION 'செல்போன்'            not present PHONE '+919840012345'          present
--------------------------------------------------------------------------------------------
assertions held (5 cases, both halves of every assertion): 23/23

============================================================================================
REPORT 2 - ENTITY RESOLUTION TRAPS
============================================================================================
candidate band (human review): score >= 72.0   confident band (a HIGH proposal is what an officer is most likely to accept): score >= 88.0
auto-merge is disabled in every case: the resolver proposes, a human decides.

--- (A) SAME ENTITY: must be surfaced as a reviewable candidate ---
```

Full harness (check 2 below) — micro precision 100.0 %, recall 97.6 %, F1 98.8 %, 0 false
positives, false merges 0, and **ALIAS 100/100/100** (tp 7). Per-type numbers are identical to the
pre-hardening run; the only misses are still `madurai` and `11-aug`.

## A2 — explainable key influencers

`scripts/partA_proofs.py a2` → `POST /api/analysis/network`.

Every ranked row now carries an `interpretation` built from that node's own numbers plus an
`interpretation_basis` string the UI shows underneath it. 12 distinct texts across 20 rows; no
interpretation is a bare band label, and none is a constant with a name substituted:

```text
     interpretation: This organisation appears in 2 cases (CASE-305, CASE-407), is connected to 2 distinct entities (1 location and 1 person), sits inside one community but on the shortest evidence paths between the entities in it. 2 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     interpretation_basis: 2 evidence-linked relationships, 2 cases, 1 communities touched, present in 2 cases (CASE-305, CASE-407)
#9  Ravi K.                    [PERSON      ] score=0.0146
     interpretation: This person appears in 1 case (CASE-305), is connected to 2 distinct entities (1 location and 1 vehicle), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 2 evidence-linked relationships back it. Locations recorded on this entity: Chennai Port.
     interpretation_basis: 2 evidence-linked relationships, 1 cases, 2 communities touched, present in 1 case (CASE-305)
#10 A/C ••••0987               [ACCOUNT     ] score=0.0132
     interpretation: This bank account appears in 1 case (CASE-305), is connected to 3 distinct entities (2 people and 1 bank account), sits inside one community but on the shortest evidence paths between the entities in it. 3 evidence-linked relationships back it.
     interpretation_basis: 3 evidence-linked relationships, 1 cases, 1 communities touched, present in 1 case (CASE-305)

interpretation strings: 12 distinct of 20 rows
safety_note: Centrality measures structural position in the evidence graph only. It is not evidence of leadership, control or criminality.
interpretations containing no number: 0  (must be 0)
```

The `degree_centrality` and `betweenness_centrality` arrays, unedited, are in
`artifacts/A2_acceptance.txt` — including two adjacent nodes with visibly different explanations:
`TN01AB1234` ("appears in 3 cases (CASE-101, CASE-202, CASE-305) … connected to 5 distinct entities
(4 people and 1 location)") versus `Chennai Central` ("appears in 2 cases (CASE-101, CASE-202) …
4 people and 1 vehicle") versus `Ravi Kumar` ("appears in 1 case (CASE-101) … Locations recorded on
this entity: Chennai Central, Guindy Industrial Estate").

`safety_note` is unchanged: *Centrality measures structural position in the evidence graph only. It
is not evidence of leadership, control or criminality.*

## A3 — second detector, labelled

`scripts/partA_proofs.py a3` → `POST /api/analysis/anomaly`:

```text

====================================================================================================
A3 — TWO LABELLED DETECTORS   (POST /api/analysis/anomaly)
====================================================================================================
detector_count: 2
  - {'detector': 'isolation_forest_transaction_burst', 'detector_kind': 'classical_ml', 'question': 'Does an account behave abnormally against its own transaction baseline?', 'method': 'IsolationForest (scikit-learn)', 'findings': 1}
  - {'detector': 'shared_identifier_cross_case', 'detector_kind': 'rule_based', 'question': 'Flags an identifier (phone, vehicle, account, device) that appears in the evidence of 2+ cases that have no other declared connection.', 'method': 'rule matched', 'findings': 1}

[isolation_forest_transaction_burst]  kind=classical_ml  model=None
   account_id    : ACC-001
   case_id       : CASE-305
   window        : 2025-08-22 14:00:00+00:00
   observed      : {'transactions_in_hour': 50, 'total_amount': 1316081.59, 'distinct_counterparties': 2}
   baseline      : {'mean_transactions_per_day': 11.6, 'description': 'Mean daily transaction volume for this account across available evidence.'}
   anomaly_score : 0.2231
   evidence_ids  : ['EV-3070']
   interpretation: Behavioural anomaly detected relative to the account's own baseline. An anomaly is not an indication of criminal activity and requires corroboration and investigator review.

[shared_identifier_cross_case]  kind=rule_based  model=None
   evidence_ids  : ['EV-1024', 'EV-2041', 'EV-3071']
   interpretation: A shared identifier is a lead to check, not proof that the cases are related or that any person is involved in an offence. Co-occurrence of an identifier across cases may also be a data-entry or data-quality artefact.
   reason        : vehicle registration TN01AB1234 appears in the evidence for CASE-202 and CASE-305 with no other link between these cases: no shared person or alias, and no second identifier. The only other things these cases have in common are Location consistency: CHENNAI PORT; Temporal relationship: 3 day(s) between nearest events, neither of which this product treats as a connection (co-location is not proof of a meeting, and temporal proximity alone is not an association signal).
   pattern       : SHARED_IDENTIFIER_WITHOUT_OTHER_LINK

distinct detectors represented in findings: 2 -> ['isolation_forest_transaction_burst', 'shared_identifier_cross_case']
```

`verify_workflow.sh` stage 9 now asserts both detector names:

```text
STAGE 9 — TIMELINE / TEMPORAL
  PASS  1 behavioural anomaly (Isolation Forest) + 1 shared-identifier pattern (rule-based); 2 detectors active: isolation_forest_transaction_burst+shared_identifier_cross_case
```

## A4 — AI-safety posture, enforced by a check that can fail

`scripts`-level proof (`GET /api/security/ai-safety-posture`, then the static check as shipped,
then with `import openai` injected, then restored):

```text
=== A4(1) posture endpoint: GET /api/security/ai-safety-posture
{
    "generative_model_in_evidence_path": false,
    "reasoning": "Entity extraction, resolution, network/anomaly analysis and hypothesis generation are all rule-based or classical ML (spaCy NER, RapidFuzz, NetworkX, IsolationForest). No LLM or generative model receives untrusted document text with the ability to write to the graph, so there is no hallucination surface and no prompt-injection surface in the evidence path.",
    "verified_by": "backend/scripts/check_no_llm_in_path.py",
    "what_that_means": {
        "untrusted_text_never_reaches_a_generative_model": true,
        "no_model_can_write_to_the_graph": true,
        "every_extracted_entity_carries_its_method": "entity_agent records the methods (rule / NER / vocabulary / structural hint) on each extracted entity, so a reviewer sees why it was proposed.",
        "no_generated_text_in_the_ui": "Interpretation strings are templates filled from computed values, not generated prose."
    },
    "model_inventory": {
        "statistical_ner": "spaCy en_core_web_sm (en_core_web_sm, statistical NER for English text; a token-classification Transformers model is used only if local weights are present, and it is deliberately not required)",
        "string_matching": "RapidFuzz (deterministic edit-distance ratios)",
        "graph": "NetworkX (degree/betweenness centrality, Louvain communities)",
        "anomaly": "scikit-learn IsolationForest (classical ML, feature space documented in app/analytics/anomaly.py)",
        "generative": "none - no openai / anthropic / langchain / LLM client is imported anywhere in app/agents, app/analytics or app/api"
    },
    "residual_risks_we_do_not_claim_to_have_solved": [
        "Extraction is imperfect: a false positive is possible and is why every extracted entity carries a confidence and a method string, and why nothing is auto-merged.",
        "Uploaded documents can be wrong or poisoned at the source; source_trust records how the document arrived and corroboration weighs low-trust sources less.",
        "A rule-based pipeline can be wrong in a consistent way - the evaluation harness (scripts/eval_extraction.py) measures that against labelled ground truth, including negative cases that must NOT be extracted."
    ],
    "verified_at_runtime_by": "scripts/check_no_llm_in_path.py (static check, non-zero exit on a generative import in the evidence path)",
    "checked_by": "SUP-1100",
    "checked_at": "2026-09-22T16:26:08Z"
}

=== A4(2) static check, AS SHIPPED
   exit=0  (0 = PASS)

=== A4(3) TEMPORARY INJECTION: 'import openai' added at app/agents/network_agent.py line 1
VIOLATIONS - the evidence path now contains a generative model:
  FAIL  app/agents/network_agent.py:1  generative library 'openai'
        import openai

GENERATIVE-MODEL CHECK: FAIL
================================================================================================
   exit=1

=== A4(4) RESTORED (diff -q silent = byte-identical)
   restore verified byte-identical
   exit=0  (0 = PASS again)
```

## A5 — read-access audit

`scripts/partA_proofs.py a5` — one `EVIDENCE_VIEWED` record per content read, nothing for the list
endpoint:

```text
EVIDENCE_VIEWED records before this read: 0  -> after: 1
newest record:
{
  "audit_id": "AUD-00008",
  "timestamp": "2026-09-22T16:24:09Z",
  "user_id": "SUP-1100",
  "role": "SUPERVISOR",
  "action": "EVIDENCE_VIEWED",
  "case_id": "CASE-101",
  "object_id": "EV-1024",
  "status": "SUCCESS",
  "detail": "Opened evidence content (FIR, 577 characters) for case CASE-101.",
  "hash": "fefe0ac07cf4fe47fd7524b72aaa0efc19471479f360972489a7d9e874b48969",
  "prev_hash": "a7120c13c4c3e950acc23be71bd9ca9a3bf54b80bffae936400d5f7ae971e292",
  "chain_hash": "a7e5454ed30c30fbf8a7d06d88fa20e7a0319e80254e11c5b2f06e05bff84acc"
}

list endpoint (GET /api/evidence) added records: 0  (must be 0)
```

## A6 — masked identifier labels + audited reveal (policy (a))

`scripts/partA_proofs.py a6`:

```text

newest IDENTIFIER_REVEALED audit record:
{
  "audit_id": "AUD-00010",
  "timestamp": "2026-09-22T16:24:09Z",
  "user_id": "SUP-1100",
  "role": "SUPERVISOR",
  "action": "IDENTIFIER_REVEALED",
  "case_id": "CASE-101",
  "object_id": "PHN-001",
  "status": "SUCCESS",
  "detail": "Unmasked PHONE identifier +919840012345 (masked form +91 98400 ••••5).",
  "hash": "c173c76f855cc401dde045b055bac1fd218744a1c4b1da79baa04988baacdc23",
  "prev_hash": "4c752ca68e437cff909c841e1b1f5c069732147d56cc1660aa5819baf3eacc1d",
  "chain_hash": "8e06778ae44cf89898a1609a576a5058365cdd5b105aab52815e1f48b19c391c"
}

leak scan — raw digits 9840012345 in every entity-bearing response:
  clean GET  /api/graph                                    raw occurrences: 0
  clean GET  /api/entities?entity_type=PHONE               raw occurrences: 0
  clean GET  /api/entities/PHN-001                         raw occurrences: 0
  clean POST /api/analysis/network                         raw occurrences: 0
  clean POST /api/analysis/cross-case                      raw occurrences: 0
  clean POST /api/analysis/corroboration                   raw occurrences: 0
  clean GET  /api/timeline                                 raw occurrences: 0
  clean GET  /api/map                                      raw occurrences: 0
  clean GET  /api/search?q=9840012345                      raw occurrences: 0
  clean POST /api/analysis/entity-resolution               raw occurrences: 0

RESULT: PASS - no endpoint leaks the raw identifier
```

**Policy boundary, stated explicitly.** The masked form is what the graph, network analysis,
cross-case engine, timeline, map, search and entity profiles return. The single place a filed
document's own text returns verbatim is the evidence-detail read (`GET /api/evidence/{id}`), which
is the audited content access from A5 — an investigator reading their own case file must see it as
filed. Every derived response that re-uses that text (including relationship sources and
interpretations) routes through `security/pii.py` and is masked.

## A7 — source-trust weighting

`scripts/partA_proofs.py a7`. Two parts: the ladder read straight off the API, and a controlled A/B
where two fresh cases are given the **identical document and the identical candidate relationship**
and only the declared `source_trust` of the two uploads differs:

```text

====================================================================================================
A7 — SOURCE-TRUST WEIGHTING   (POST /api/analysis/evidence-support / corroboration)
====================================================================================================
the ladder (POST /api/analysis/evidence-support):

  2 x OFFICER_UPLOAD                     (EV-1024 + EV-1025)
     weighted_support       : 2.0
     independent_sources    : 2
     support_level_reachable: HIGH
     sources                : [('Police Report', 'OFFICER_UPLOAD', 1.0), ('Telecom Record (synthetic)', 'OFFICER_UPLOAD', 1.0)]
     explanation            : weighted support 2.00 from 2 independent sources reaches the confident band

  1 x OFFICER_UPLOAD + 1 x EXTERNAL_SUBMISSION (EV-1024 + EV-5122)
     weighted_support       : 1.35
     independent_sources    : 2
     support_level_reachable: MEDIUM
     sources                : [('Police Report', 'OFFICER_UPLOAD', 1.0), ('External partner feed (A7 ladder)', 'EXTERNAL_SUBMISSION', 0.35)]
     explanation            : weighted support 1.35 clears the reviewable-candidate band but not the confident band

controlled A/B — identical document, identical candidate relationship;
only the DECLARED source trust of the two uploads differs:

  [EXTERNAL] CASE-1291 <- EV-5123  source_trust=EXTERNAL_SUBMISSION
  [EXTERNAL] CASE-1292 <- EV-5124  source_trust=EXTERNAL_SUBMISSION
    document shared by both cases: Naveen Sundaram was observed at the scene with vehicle TN52YB1549 on 2025-09-01; contact +919773556117 was recorded in the same note.
    lead LEAD-XC-1291-1292: status=PARTIALLY CORROBORATED - FURTHER EVIDENCE REQUIRED
    support_level=LOW  raw=MEDIUM  capped_by_source_trust=True  weighted=0.7  sources=2
    cap reason: evidence weighted 0.70 (needs 2.00 from 2 independent sources for the confident band)
    weights used: {'OFFICER_UPLOAD': 1.0, 'BULK_IMPORT': 0.6, 'EXTERNAL_SUBMISSION': 0.35}

  [OFFICER] CASE-7781 <- EV-5125  source_trust=OFFICER_UPLOAD
  [OFFICER] CASE-7782 <- EV-5126  source_trust=OFFICER_UPLOAD
    document shared by both cases: Karthik Prakash was observed at the scene with vehicle TN19CT3873 on 2025-09-01; contact +919760620300 was recorded in the same note.
    lead LEAD-XC-7781-7782: status=CORROBORATED ANALYTICAL LEAD
    support_level=MEDIUM  raw=MEDIUM  capped_by_source_trust=False  weighted=2.0  sources=2
    weights used: {'OFFICER_UPLOAD': 1.0, 'BULK_IMPORT': 0.6, 'EXTERNAL_SUBMISSION': 0.35}
```

Mechanic worth stating plainly: the correlation engine computes its own raw level from signal
agreement, and source trust can only **cap** that level downward (`cap_level(raw, assessment)`) —
low-trust evidence can never inflate a lead, and it is never discarded or hidden. The external arm
above is capped `MEDIUM → LOW` with `capped_by_source_trust=True` and a named reason; the officer arm
reaches weighted support 2.00 over 2 sources and is not capped.

---

## FINAL CHECK — 1…8, in order

### 1) `bash backend/verify_workflow.sh`

```text
  PASS  EV-1024 integrity VERIFIED
  PASS  EV-2042 tamper demo returns INTEGRITY_MISMATCH

STAGE 15 — AUDIT + LEDGER
  PASS  31 append-only audit records written during this run
  PASS  ledger hash chain intact (19 blocks)

RESULT: 33 passed, 0 failed
```

### 2) `python3 backend/scripts/eval_extraction.py`

```text
ACCOUNT           100.0%   100.0% 100.0%      2    0    0
DEVICE            100.0%   100.0% 100.0%      1    0    0
DATE              100.0%    92.9%  96.3%     13    0    1
ALIAS             100.0%   100.0% 100.0%      7    0    0
--------------------------------------------------------------------------------------------
MICRO AVERAGE     100.0%    97.6%  98.8%     83    0    2

   ALL documents                      precision 100.0%   recall  97.6%   F1  98.8%   (tp 83, fp 0, fn 2)

ALIAS only (the type the second hardening pass fixed, scored here for the first time):
   precision 100.0%   recall 100.0%   F1 100.0%   tp 7  fp 0  fn 0

per-mention detail (what failed):
    EV-2043 LOCATION: MISSED   madurai

============================================================================================
PHASE 6 HARNESS: PASS   |  extraction micro-F1 sample size 85 mentions   |  negative assertions 23/23   |  false merges 0
============================================================================================
```

### 3) `python3 backend/scripts/measure_graph_recall.py`

```text
------------------------------------------------------------------------------------------------
REPRODUCED by the pipeline : 28/28 (100.0%)
Endpoints only (no co-event): 0
Not derivable at all       : 0
```

### 4) `python3 backend/scripts/tamper_test.py`

```text

   RESULT: DETECTED

================================================================================================
PHASE 4 ACCEPTANCE: object+DB rewrite detected = True | ledger rewrite detected = True
================================================================================================
```

### 5) `python3 backend/scripts/check_no_llm_in_path.py`

```text
  1. generative client libraries (openai, anthropic, langchain, cohere, ollama, ...): none imported
  2. generative service endpoints (api.openai.com, api.anthropic.com, ...): none called
  3. generative call shapes (chat.completions.create, generate_content, LLMChain, ...): none present

GENERATIVE-MODEL CHECK: PASS - no generative model is imported, called or reachable
from app/agents, app/analytics or app/api. Untrusted document text is processed by
rules, statistical NER, RapidFuzz, NetworkX and IsolationForest only.
================================================================================================
```

### 6) `python3 backend/scripts/benchmark_scale.py`

```text
 N entities   comparisons   wall clock   per pair  pairs/sec  candidates
--------------------------------------------------------------------------------------------
         50         1,225       0.13 s      106 us      9,434          16
        200        19,900       1.94 s       98 us     10,248         354
        500       124,750      11.93 s       96 us     10,459       2,176
      1,000       499,500      52.80 s      106 us      9,461       8,780
--------------------------------------------------------------------------------------------
growth: 20x the entities costs 406.6x the time (quadratic)
projected for 5,000 entities : 22.0 minutes   (single core, this implementation, no blocking)
projected for 10,000 entities: 88.1 minutes   (single core, this implementation, no blocking)

```

### 7) `python3 -m pytest backend/tests/`

```text
.....................                                  [100%]
21 passed, 18 subtests passed in 2.50s
```

### 8) `cd frontend && npm run build`

```text
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
✓ built in 907ms
```

## Result table

| # | check | result | run it yourself |
| --- | --- | --- | --- |
| 1 | end-to-end workflow | **PASS — 33 passed, 0 failed** (stage 9 shows both detector names) | `bash backend/verify_workflow.sh` |
| 2 | extraction vs ground truth | **PASS — P 100.0 / R 97.6 / F1 98.8; 0 fp; negative assertions 23/23; ALIAS 100/100/100** | `python3 backend/scripts/eval_extraction.py` |
| 3 | graph recall | **PASS — 28/28 reproduced, 0 endpoints-only, 0 not-derivable** | `python3 backend/scripts/measure_graph_recall.py` |
| 4 | tamper detection | **PASS — object+DB rewrite DETECTED, ledger rewrite DETECTED** | `python3 backend/scripts/tamper_test.py` |
| 5 | no generative model in the evidence path | **PASS — 28 files scanned, 0 violations; injected `import openai` → FAIL exit 1; restored → PASS exit 0** | `python3 backend/scripts/check_no_llm_in_path.py` |
| 6 | scale benchmark | **PASS — 0.13 / 1.94 / 11.93 / 52.80 s; per-pair 106 / 98 / 96 / 106 µs vs 116 / 107 / 108 / 119 µs recorded (same cost constant, resolution code untouched)** | `python3 backend/scripts/benchmark_scale.py` |
| 7 | backend tests | **PASS — 21 passed, 18 subtests passed** | `python3 -m pytest backend/tests/` |
| 8 | frontend build | **PASS — built in 907 ms; CSS 75.67 kB (gzip 18.56), JS 1,303.56 kB (gzip 363.01)** | `cd frontend && npm run build` |

## A1–A7: PASS/FAIL and how to verify

| item | result | exact command / endpoint |
| --- | --- | --- |
| A1 Hindi false positive | **PASS** — `फोन` extracted as no type (NEG-HI-01); `रवि कुमार` still PERSON; Tamil `ரவி குமார்` → Ravi Kumar unchanged; 23/23 negative assertions | `python3 scripts/a1_api_repro.py` · `POST /api/evidence` then `POST /api/evidence/{id}/process` |
| A2 explainable influencers | **PASS** — per-node `interpretation` + `interpretation_basis` (case count, entity types, communities bridged, relationships backing it); 12 distinct of 20 rows; `safety_note` intact | `python3 scripts/partA_proofs.py a2` · `POST /api/analysis/network` |
| A3 second detector | **PASS** — `detector_count: 2`; one finding each from `isolation_forest_transaction_burst` (`classical_ml`) and `shared_identifier_cross_case` (`rule_based`) with plain-language reasons; 33/33 re-run green | `python3 scripts/partA_proofs.py a3` · `POST /api/analysis/anomaly` |
| A4 AI-safety posture | **PASS** — posture JSON served; static check PASS → FAIL (exit 1) → PASS (exit 0) after byte-identical restore | `GET /api/security/ai-safety-posture` · `python3 backend/scripts/check_no_llm_in_path.py` |
| A5 read-access audit | **PASS** — `EVIDENCE_VIEWED` with user, evidence_id, case, timestamp, hash and chain_hash; list endpoint adds 0 records | `GET /api/evidence/EV-1024` then `GET /api/audit?action=EVIDENCE_VIEWED` |
| A6 PII policy (a) | **PASS** — 9/42 nodes masked (`+91 98400 ••••5`, `A/C ••••1122`, `IMEI ••••3809`); reveal returns the value with `at_rest` proof and writes `IDENTIFIER_REVEALED`; leak scan 10/10 clean | `GET /api/graph` · `GET /api/entities/PHN-001/reveal` · `python3 scripts/partA_proofs.py a6` |
| A7 source trust | **PASS** — ladder 2×OFFICER → 2.00 HIGH / OFFICER+EXTERNAL → 1.35 MEDIUM / EXTERNAL-only → 0.35 LOW; identical-document A/B: external arm capped to LOW (`capped_by_source_trust=True`), officer arm uncapped at 2.00 | `python3 scripts/partA_proofs.py a7` · `POST /api/analysis/evidence-support` · `POST /api/analysis/corroboration` |

## Screens (Part B) — unchanged by this pass, still building

`npm run build` above is the same frontend delivered in the redesign pass: all 17 pages on one token
layer, glass limited to nav / drawers / provenance strip / KPI cards, dense content on opaque
surfaces, designed empty/loading/error states, CANDIDATE outlined rather than filled, 2px focus ring
throughout. Source for Dashboard, NetworkIntelligence and Evidence is in `PART3_component_source.md`.

Live right now: UI on :5173, API on :8000 (both started with the process tool).
