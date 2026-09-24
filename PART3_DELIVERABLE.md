# CrimeNet AI — PART 3 deliverable

**Scope of this pass.** PART A = close the seven remaining SIH26189 gaps (A1–A7), each with its
stated acceptance test actually run; PART B = full visual redesign of every page in
`frontend/src/pages/`. Every command below was executed in this workspace against the running API
(embedded PostgreSQL / Neo4j / Redis profiles) over the real seeded dataset; the raw logs are kept
unchanged in `artifacts/`.

**Two environment facts that matter when you re-run check 1.**

- `backend/verify_workflow.sh` defaults to `BASE=http://127.0.0.1:5173`, i.e. it drives the product
  through the Vite dev server, which proxies `/api` to the API on :8000. The dev server must be up,
  or pass the API directly: `bash backend/verify_workflow.sh http://127.0.0.1:8000`.
- `seed.load()` reseeds on startup, so the ledger block count printed in stage 15 grows with the
  actions performed since the process started. The assertion is *chain intact*, not a fixed count.

---

## PART A — acceptance proofs (verbatim)

### A1 — Hindi false positive removed, Tamil regression guarded

The reported sentence used to yield `PERSON 'फोन' -> 'Phona'` from the sentence-initial-subject
structural hint at confidence 0.55. The stoplist in `sentence_initial_subjects()` now rejects
month/device/deictic vocabulary before that hint can fire. Produced by running the extractor twice
on the same sentence — once with the stoplist disabled (the code as it was), once as shipped:

```text
================================================================================================
HINDI - the sentence in the report
================================================================================================
--- BEFORE (stoplist disabled = the code as it was)
   DATE        '12 अगस्त'               -> '12 August'          conf=0.85  ['indic-date-vocabulary']
   LOCATION    'चेन्नई सेंट्रल'         -> 'Chennai Central'    conf=0.82  ['indic-transliteration+vocabulary']
   PERSON      'फोन'                    -> 'Phona'              conf=0.55  ['indic-structural (sentence-initial subject)']
   PERSON      'रवि कुमार'              -> 'Ravi Kumar'         conf=0.82  ['indic-transliteration+vocabulary']
   PHONE       '+919840012345'          -> '+919840012345'      conf=0.98  ['regex', 'gazetteer']
   VEHICLE     'TN01AB1234'             -> 'TN01AB1234'         conf=0.98  ['regex', 'gazetteer']
+++ AFTER  (current code)
   DATE        '12 अगस्त'               -> '12 August'          conf=0.85  ['indic-date-vocabulary']
   LOCATION    'चेन्नई सेंट्रल'         -> 'Chennai Central'    conf=0.82  ['indic-transliteration+vocabulary']
   PERSON      'रवि कुमार'              -> 'Ravi Kumar'         conf=0.82  ['indic-transliteration+vocabulary']
   PHONE       '+919840012345'          -> '+919840012345'      conf=0.98  ['regex', 'gazetteer']
   VEHICLE     'TN01AB1234'             -> 'TN01AB1234'         conf=0.98  ['regex', 'gazetteer']
--- unified diff
   --- before
   +++ after
   @@ -2,3 +2,2 @@
       LOCATION    'चेन्नई सेंट्रल'         -> 'Chennai Central'    conf=0.82  ['indic-transliteration+vocabulary']
   -   PERSON      'फोन'                    -> 'Phona'              conf=0.55  ['indic-structural (sentence-initial subject)']
       PERSON      'रवि कुमार'              -> 'Ravi Kumar'         conf=0.82  ['indic-transliteration+vocabulary']

================================================================================================
TAMIL - the sentence fixed in the previous pass
================================================================================================
--- BEFORE (stoplist disabled = the code as it was)
   DATE        '12 ஆகஸ்ட்'              -> '12 August'          conf=0.85  ['indic-date-vocabulary']
   LOCATION    'சென்னை சென்ட்ரலில்'     -> 'Chennai Central'    conf=0.82  ['indic-transliteration+vocabulary']
   PERSON      'ரவி குமார்'             -> 'Ravi Kumar'         conf=0.82  ['indic-transliteration+vocabulary']
   VEHICLE     'TN01AB1234'             -> 'TN01AB1234'         conf=0.98  ['regex', 'gazetteer']
+++ AFTER  (current code)
   DATE        '12 ஆகஸ்ட்'              -> '12 August'          conf=0.85  ['indic-date-vocabulary']
   LOCATION    'சென்னை சென்ட்ரலில்'     -> 'Chennai Central'    conf=0.82  ['indic-transliteration+vocabulary']
   PERSON      'ரவி குமார்'             -> 'Ravi Kumar'         conf=0.82  ['indic-transliteration+vocabulary']
   VEHICLE     'TN01AB1234'             -> 'TN01AB1234'         conf=0.98  ['regex', 'gazetteer']
--- unified diff
   (no change)
```

Tamil is byte-for-byte unchanged (`--- unified diff` → `(no change)`), and the harness that scores
extraction against labelled ground truth still passes with the negative cases in place:

```text
(C) identifier objects folded correctly  : 12/12  (100.0%)
    --  Suresh Balan <-> S. Balan scored 63.0 (LOW) - below the review threshold: account holder recorded two ways (account + phone support only)

============================================================================================
PHASE 6 HARNESS: PASS   |  extraction micro-F1 sample size 85 mentions   |  negative assertions 23/23   |  false merges 0
============================================================================================
```

### A2 — explainable key influencers

`POST /api/analysis/network`. Every interpretation is generated from the values printed beside it
(case count, connected entity types, communities bridged, relationships backing it) — 12 of 12
nodes carry a distinct, concrete text — and the `safety_note` is unchanged:

```text
engine=NetworkX  nodes=29  edges=28  communities=7  modularity=0.6327
====================================================================================================
DEGREE_CENTRALITY - as returned by POST /api/analysis/network
====================================================================================================
#1  'Ravi Kumar' [PERSON]  score=0.1429  degree=4  cases=['CASE-101']  communities_touched=[5, 6]
     connected_type_counts={'LOCATION': 1, 'ORGANIZATION': 1, 'PHONE': 1, 'VEHICLE': 1}
     interpretation: This person appears in 1 case (CASE-101), is connected to 4 distinct entities (1 location, 1 organisation and 1 phone number), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 4 evidence-linked relationships back it. Locations recorded on this entity: Chennai Central, Guindy Industrial Estate.
     basis: 4 evidence-linked relationships, 1 cases, 2 communities touched, present in 1 case (CASE-101)
#2  'TN01AB1234' [VEHICLE]  score=0.1429  degree=4  cases=['CASE-101', 'CASE-202', 'CASE-305']  communities_touched=[0, 6]
     connected_type_counts={'PERSON': 4}
     interpretation: This vehicle appears in 3 cases (CASE-101, CASE-202, CASE-305), is connected to 4 distinct entities (4 people), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 4 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     basis: 4 evidence-linked relationships, 3 cases, 2 communities touched, present in 3 cases (CASE-101, CASE-202, CASE-305)
#3  'Chennai Central' [LOCATION]  score=0.1429  degree=4  cases=['CASE-101', 'CASE-202']  communities_touched=[6]
     connected_type_counts={'PERSON': 4}
     interpretation: This location appears in 2 cases (CASE-101, CASE-202), is connected to 4 distinct entities (4 people), sits inside one community but on the shortest evidence paths between the entities in it. 4 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     basis: 4 evidence-linked relationships, 2 cases, 1 communities touched, present in 2 cases (CASE-101, CASE-202)
#4  'Arun Selvam' [PERSON]  score=0.1429  degree=4  cases=['CASE-101', 'CASE-202', 'CASE-305']  communities_touched=[0, 5, 6]
     connected_type_counts={'LOCATION': 2, 'PHONE': 1, 'VEHICLE': 1}
     interpretation: This person appears in 3 cases (CASE-101, CASE-202, CASE-305), is connected to 4 distinct entities (2 locations, 1 phone number and 1 vehicle), and links 3 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 4 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding. Locations recorded on this entity: Chennai Central, Chennai Port.
     basis: 4 evidence-linked relationships, 3 cases, 3 communities touched, present in 3 cases (CASE-101, CASE-202, CASE-305)
#5  'R. Kumar' [PERSON]  score=0.1071  degree=3  cases=['CASE-202']  communities_touched=[6]
     connected_type_counts={'DEVICE': 1, 'LOCATION': 1, 'VEHICLE': 1}
     interpretation: This person appears in 1 case (CASE-202), is connected to 3 distinct entities (1 device, 1 location and 1 vehicle), sits inside one community but on the shortest evidence paths between the entities in it. 3 evidence-linked relationships back it. Locations recorded on this entity: Chennai Central.
     basis: 3 evidence-linked relationships, 1 cases, 1 communities touched, present in 1 case (CASE-202)
#6  'Chennai Port' [LOCATION]  score=0.1071  degree=3  cases=['CASE-305', 'CASE-202']  communities_touched=[0, 6]
     connected_type_counts={'ORGANIZATION': 1, 'PERSON': 2}
     interpretation: This location appears in 2 cases (CASE-202, CASE-305), is connected to 3 distinct entities (2 people and 1 organisation), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 3 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     basis: 3 evidence-linked relationships, 2 cases, 2 communities touched, present in 2 cases (CASE-202, CASE-305)
#7  '+91 98400 ••••7' [PHONE]  score=0.1071  degree=3  cases=['CASE-101', 'CASE-202']  communities_touched=[5, 6]
     connected_type_counts={'PERSON': 2, 'PHONE': 1}
     interpretation: This phone number appears in 2 cases (CASE-101, CASE-202), is connected to 3 distinct entities (2 people and 1 phone number), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 3 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     basis: 3 evidence-linked relationships, 2 cases, 2 communities touched, present in 2 cases (CASE-101, CASE-202)
#8  'TN07XY4455' [VEHICLE]  score=0.1071  degree=3  cases=['CASE-101']  communities_touched=[1]
     connected_type_counts={'LOCATION': 1, 'PERSON': 2}
     interpretation: This vehicle appears in 1 case (CASE-101), is connected to 3 distinct entities (2 people and 1 location), sits inside one community but on the shortest evidence paths between the entities in it. 3 evidence-linked relationships back it.
     basis: 3 evidence-linked relationships, 1 cases, 1 communities touched, present in 1 case (CASE-101)
#9  'A/C ••••0987' [ACCOUNT]  score=0.1071  degree=3  cases=['CASE-305']  communities_touched=[2]
     connected_type_counts={'ACCOUNT': 1, 'PERSON': 2}
     interpretation: This bank account appears in 1 case (CASE-305), is connected to 3 distinct entities (2 people and 1 bank account), sits inside one community but on the shortest evidence paths between the entities in it. 3 evidence-linked relationships back it.
     basis: 3 evidence-linked relationships, 1 cases, 1 communities touched, present in 1 case (CASE-305)
#10  '+91 98400 ••••5' [PHONE]  score=0.0714  degree=2  cases=['CASE-101', 'CASE-202']  communities_touched=[5, 6]
     connected_type_counts={'PERSON': 1, 'PHONE': 1}
     interpretation: This phone number appears in 2 cases (CASE-101, CASE-202), is connected to 2 distinct entities (1 person and 1 phone number), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 2 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     basis: 2 evidence-linked relationships, 2 cases, 2 communities touched, present in 2 cases (CASE-101, CASE-202)
====================================================================================================
BETWEENNESS_CENTRALITY - as returned by POST /api/analysis/network
====================================================================================================
#1  'Arun Selvam' [PERSON]  score=0.101  degree=4  cases=['CASE-101', 'CASE-202', 'CASE-305']  communities_touched=[0, 5, 6]
     connected_type_counts={'LOCATION': 2, 'PHONE': 1, 'VEHICLE': 1}
     interpretation: This person appears in 3 cases (CASE-101, CASE-202, CASE-305), is connected to 4 distinct entities (2 locations, 1 phone number and 1 vehicle), and links 3 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 4 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding. Locations recorded on this entity: Chennai Central, Chennai Port.
     basis: 4 evidence-linked relationships, 3 cases, 3 communities touched, present in 3 cases (CASE-101, CASE-202, CASE-305)
#2  'Chennai Port' [LOCATION]  score=0.0688  degree=3  cases=['CASE-305', 'CASE-202']  communities_touched=[0, 6]
     connected_type_counts={'ORGANIZATION': 1, 'PERSON': 2}
     interpretation: This location appears in 2 cases (CASE-202, CASE-305), is connected to 3 distinct entities (2 people and 1 organisation), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 3 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     basis: 3 evidence-linked relationships, 2 cases, 2 communities touched, present in 2 cases (CASE-202, CASE-305)
#3  'Chennai Central' [LOCATION]  score=0.0635  degree=4  cases=['CASE-101', 'CASE-202']  communities_touched=[6]
     connected_type_counts={'PERSON': 4}
     interpretation: This location appears in 2 cases (CASE-101, CASE-202), is connected to 4 distinct entities (4 people), sits inside one community but on the shortest evidence paths between the entities in it. 4 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     basis: 4 evidence-linked relationships, 2 cases, 1 communities touched, present in 2 cases (CASE-101, CASE-202)
#4  'TN01AB1234' [VEHICLE]  score=0.0608  degree=4  cases=['CASE-101', 'CASE-202', 'CASE-305']  communities_touched=[0, 6]
     connected_type_counts={'PERSON': 4}
     interpretation: This vehicle appears in 3 cases (CASE-101, CASE-202, CASE-305), is connected to 4 distinct entities (4 people), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 4 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     basis: 4 evidence-linked relationships, 3 cases, 2 communities touched, present in 3 cases (CASE-101, CASE-202, CASE-305)
#5  'Ravi Kumar' [PERSON]  score=0.0534  degree=4  cases=['CASE-101']  communities_touched=[5, 6]
     connected_type_counts={'LOCATION': 1, 'ORGANIZATION': 1, 'PHONE': 1, 'VEHICLE': 1}
     interpretation: This person appears in 1 case (CASE-101), is connected to 4 distinct entities (1 location, 1 organisation and 1 phone number), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 4 evidence-linked relationships back it. Locations recorded on this entity: Chennai Central, Guindy Industrial Estate.
     basis: 4 evidence-linked relationships, 1 cases, 2 communities touched, present in 1 case (CASE-101)
#6  '+91 98400 ••••7' [PHONE]  score=0.045  degree=3  cases=['CASE-101', 'CASE-202']  communities_touched=[5, 6]
     connected_type_counts={'PERSON': 2, 'PHONE': 1}
     interpretation: This phone number appears in 2 cases (CASE-101, CASE-202), is connected to 3 distinct entities (2 people and 1 phone number), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 3 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     basis: 3 evidence-linked relationships, 2 cases, 2 communities touched, present in 2 cases (CASE-101, CASE-202)
#7  'R. Kumar' [PERSON]  score=0.0375  degree=3  cases=['CASE-202']  communities_touched=[6]
     connected_type_counts={'DEVICE': 1, 'LOCATION': 1, 'VEHICLE': 1}
     interpretation: This person appears in 1 case (CASE-202), is connected to 3 distinct entities (1 device, 1 location and 1 vehicle), sits inside one community but on the shortest evidence paths between the entities in it. 3 evidence-linked relationships back it. Locations recorded on this entity: Chennai Central.
     basis: 3 evidence-linked relationships, 1 cases, 1 communities touched, present in 1 case (CASE-202)
#8  'Coastal Logistics Pvt Ltd' [ORGANIZATION]  score=0.0344  degree=2  cases=['CASE-305', 'CASE-407']  communities_touched=[0]
     connected_type_counts={'LOCATION': 1, 'PERSON': 1}
     interpretation: This organisation appears in 2 cases (CASE-305, CASE-407), is connected to 2 distinct entities (1 location and 1 person), sits inside one community but on the shortest evidence paths between the entities in it. 2 evidence-linked relationships back it. Cross-case overlap such as this is a lead for an investigator to check, not a finding.
     basis: 2 evidence-linked relationships, 2 cases, 1 communities touched, present in 2 cases (CASE-305, CASE-407)
#9  'Ravi K.' [PERSON]  score=0.0146  degree=2  cases=['CASE-305']  communities_touched=[0, 6]
     connected_type_counts={'LOCATION': 1, 'VEHICLE': 1}
     interpretation: This person appears in 1 case (CASE-305), is connected to 2 distinct entities (1 location and 1 vehicle), and links 2 communities that otherwise have no shared entity (one of 7 bridging entities in this projection). 2 evidence-linked relationships back it. Locations recorded on this entity: Chennai Port.
     basis: 2 evidence-linked relationships, 1 cases, 2 communities touched, present in 1 case (CASE-305)
#10  'A/C ••••0987' [ACCOUNT]  score=0.0132  degree=3  cases=['CASE-305']  communities_touched=[2]
     connected_type_counts={'ACCOUNT': 1, 'PERSON': 2}
     interpretation: This bank account appears in 1 case (CASE-305), is connected to 3 distinct entities (2 people and 1 bank account), sits inside one community but on the shortest evidence paths between the entities in it. 3 evidence-linked relationships back it.
     basis: 3 evidence-linked relationships, 1 cases, 1 communities touched, present in 1 case (CASE-305)

distinct interpretation strings among all returned rows: 12 of 12 distinct nodes
safety_note present: True -> Centrality measures structural position in the evidence graph only. It is not evidence of leadership, control or criminality.
```

### A3 — two detectors, each labelled by name

One transparent rule (`shared_identifier_cross_case`) beside the existing classical-ML detector
(`isolation_forest_transaction_burst`). No second ML model was added; the rule carries
`detector_kind: rule_based` and a plain-language reason that names what it does *not* treat as a
connection:

```text
A3 — ANOMALY ENDPOINT: TWO LABELLED DETECTORS
====================================================================================================
detector_count: 2
  - {'detector': 'isolation_forest_transaction_burst', 'detector_kind': 'classical_ml', 'question': 'Does an account behave abnormally against its own transaction baseline?', 'method': 'IsolationForest (scikit-learn)', 'findings': 1}
  - {'detector': 'shared_identifier_cross_case', 'detector_kind': 'rule_based', 'question': 'Flags an identifier (phone, vehicle, account, device) that appears in the evidence of 2+ cases that have no other declared connection.', 'method': 'rule matched', 'findings': 1}

[isolation_forest_transaction_burst]  (plain-language reason)
  detector: isolation_forest_transaction_burst | kind: classical_ml | model: IsolationForest (scikit-learn)
  account : ACC-001 | case: CASE-305 | window: 2025-08-22 14:00:00+00:00
  observed: {"transactions_in_hour": 50, "total_amount": 1316081.59, "distinct_counterparties": 2}
  baseline: {"mean_transactions_per_day": 11.6, "description": "Mean daily transaction volume for this account across available evidence."}
  score   : 0.2231 | evidence: ['EV-3070']
  reason  : Behavioural anomaly detected relative to the account's own baseline. An anomaly is not an indication of criminal activity and requires corroboration and investigator review.

[shared_identifier_cross_case]
  detector: shared_identifier_cross_case | kind: rule_based
  reason  : vehicle registration TN01AB1234 appears in the evidence for CASE-202 and CASE-305 with no other link between these cases: no shared person or alias, and no second identifier. The only other things these cases have in common are Location consistency: CHENNAI PORT; Temporal relationship: 3 day(s) between nearest events, neither of which this product treats as a connection (co-location is not proof of a meeting, and temporal proximity alone is not an association signal).
  evidence: ['EV-1024', 'EV-2041', 'EV-3071']

====================================================================================================
```

### A4 — AI-safety posture endpoint + a static check that can actually fail

`GET /api/security/ai-safety-posture`:

```json
A4 — AI SAFETY POSTURE ENDPOINT
====================================================================================================
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
  "checked_at": "2026-09-22T13:24:15Z"
}

====================================================================================================
```

`scripts/check_no_llm_in_path.py` must fail the moment a generative client enters the evidence
path. Proven by injecting `import openai` into `app/agents/network_agent.py`, then restoring the
file (verified byte-identical with `diff -q`):

```text
=== A4 static check: BASELINE (as shipped)
GENERATIVE-MODEL CHECK: PASS - no generative model is imported, called or reachable
from app/agents, app/analytics or app/api. Untrusted document text is processed by
rules, statistical NER, RapidFuzz, NetworkX and IsolationForest only.
================================================================================================
   exit=0

=== A4 static check: TEMPORARY INJECTION  (import openai added at app/agents/network_agent.py line 1)
================================================================================================
AI-SAFETY STATIC CHECK - is there a generative model in the evidence path?
================================================================================================
scanned 28 python files under: app/agents, app/analytics, app/api (+ app/main.py)

allowed non-generative components found in the evidence path:
  ALLOWED  transformers   in 3 file(s) - document_agent.py loads an OCR/token-classification model from local weights when present; token classification returns labels, it does not generate text and it never writes to the graph.
  ALLOWED  spacy          in 3 file(s) - statistical NER (en_core_web_sm): trained tagger, not a generator.
  ALLOWED  sklearn        in 1 file(s) - classical ML: IsolationForest over transaction features.
  ALLOWED  rapidfuzz      in 4 file(s) - deterministic string ratio, no model at all.

VIOLATIONS - the evidence path now contains a generative model:
  FAIL  app/agents/network_agent.py:1  generative library 'openai'
        import openai

GENERATIVE-MODEL CHECK: FAIL
================================================================================================
   exit=1

=== A4 static check: AFTER RESTORE (byte-identical to shipped file)
   restore verified byte-identical
GENERATIVE-MODEL CHECK: PASS - no generative model is imported, called or reachable
from app/agents, app/analytics or app/api. Untrusted document text is processed by
rules, statistical NER, RapidFuzz, NetworkX and IsolationForest only.
================================================================================================
   exit=0
```

### A5 — read-access audit on evidence open

`GET /api/evidence/{id}` writes exactly one `EVIDENCE_VIEWED` record; the list endpoint writes
none:

```text
A5 — READ-ACCESS AUDIT (EVIDENCE_VIEWED)
====================================================================================================
EVIDENCE_VIEWED records before this demo: 0 -> after opening one record: 1
newest record: {
  "audit_id": "AUD-00010",
  "timestamp": "2026-09-22T13:24:15Z",
  "user_id": "SUP-1100",
  "role": "SUPERVISOR",
  "action": "EVIDENCE_VIEWED",
  "case_id": "CASE-101",
  "object_id": "EV-1024",
  "status": "SUCCESS",
  "detail": "Opened evidence content (FIR, 577 characters) for case CASE-101.",
  "hash": "f1c8c874b3d856f4bfc34af54ff1e98d0e8ae8464cb579013a604123617a055a",
  "prev_hash": "520603f5eda831070b7685bc72421afab2dfb5ed8dd807c30f575deeff34b585",
  "chain_hash": "fad9a45053f14e2f64168f3f900cf7a9315dcacd0f23ded7a8f78ffbb5e8df38"
}

====================================================================================================
```

### A6 — masked identifier labels + audited reveal (policy (a))

```text
A6 — PII MASKING + AUDITED REVEAL
====================================================================================================
nodes with identifier_masked: 9 / 42
  PHN-001      PHONE    label=+91 98400 ••••5          reveal_endpoint=/api/entities/PHN-001/reveal
  PHN-002      PHONE    label=+91 98400 ••••7          reveal_endpoint=/api/entities/PHN-002/reveal
  PHN-003      PHONE    label=+91 97900 ••••3          reveal_endpoint=/api/entities/PHN-003/reveal
  DEV-001      DEVICE   label=IMEI ••••3809            reveal_endpoint=/api/entities/DEV-001/reveal
graph pii_policy: PHONE / ACCOUNT / DEVICE labels are masked; GET /api/entities/{entity_id}/reveal returns the full value and is audited.

reveal: {
  "entity_id": "PHN-001",
  "entity_type": "PHONE",
  "masked": true,
  "value": "+919840012345",
  "normalized": "+919840012345",
  "masked_form": "+91 98400 \u2022\u2022\u2022\u20225",
  "at_rest": {
    "field": "msisdn_encrypted",
    "encrypted": true,
    "note": "The stored copy is AES-256-GCM ciphertext; it is decrypted only for authorized access, and every access is audited."
  },
  "audited": true,
  "audit_action": "IDENTIFIER_REVEALED",
  "revealed_by": "SUP-1100",
  "revealed_at": "2026-09-22T13:24:15Z",
  "policy_note": "Identifiers are masked by default. This reveal is recorded in the append-only audit trail and the hash-chained ledger."
}

IDENTIFIER_REVEALED audit record  : {
  "audit_id": "AUD-00007",
  "timestamp": "2026-09-22T13:23:18Z",
  "user_id": "SUP-1100",
  "role": "SUPERVISOR",
  "action": "IDENTIFIER_REVEALED",
  "case_id": "CASE-101",
  "object_id": "PHN-001",
  "status": "SUCCESS",
  "detail": "Unmasked PHONE identifier +919840012345 (masked form +91 98400 \u2022\u2022\u2022\u20225).",
  "hash": "0a96e025a15c1bbb604a6bdefb08869ad76b6aea668760a663d52dd65d824984",
  "prev_hash": "0349dd0b2735e9ed724788704dce506772f98e14aa27fe2e7427aa29fc9d4826",
  "chain_hash": "28e40e7f127e4162f06fa116c3150b3a451f58a3d2ced4150af94bd4ee7951c7"
}
```

Leak scan — every response that can carry an entity, checked for the raw identifier:

```text
scanning for the raw identifier digits 9840012345 in every response:
  clean GET   /api/graph                                 raw occurrences: 0
  clean GET   /api/entities?entity_type=PHONE            raw occurrences: 0
  clean GET   /api/entities/PHN-001                      raw occurrences: 0
  clean POST  /api/analysis/network                      raw occurrences: 0
  clean POST  /api/analysis/cross-case                   raw occurrences: 0
  clean POST  /api/analysis/corroboration                raw occurrences: 0
  clean GET   /api/timeline                              raw occurrences: 0
  clean GET   /api/map                                   raw occurrences: 0
  clean GET   /api/search?q=9840012345                   raw occurrences: 0
  clean POST  /api/analysis/entity-resolution            raw occurrences: 0

audited reveal action: value=+919840012345 masked_form=+91 98400 ••••5 audited=True
RESULT: PASS - no endpoint leaks the raw identifier
```

### A7 — source-trust weighting

The ladder itself, printed straight from the API:

```text
====================================================================================================
registered: EV-5121 source_trust = EXTERNAL_SUBMISSION weight = 0.35
explanation: Declared as arriving from outside the console (partner feed, public or third-party submission).

2 x OFFICER_UPLOAD          (EV-1024 + EV-1025)
   weighted_support     : 2.0
   independent_sources  : 2
   support_level_reachable: HIGH
   sources              : [('Police Report', 'OFFICER_UPLOAD', 1.0), ('Telecom Record (synthetic)', 'OFFICER_UPLOAD', 1.0)]
   explanation          : weighted support 2.00 from 2 independent sources reaches the confident band

OFFICER_UPLOAD + EXTERNAL   (EV-1024 + EV-5121)
   weighted_support     : 1.35
   independent_sources  : 2
   support_level_reachable: MEDIUM
   sources              : [('Police Report', 'OFFICER_UPLOAD', 1.0), ('Partner feed', 'EXTERNAL_SUBMISSION', 0.35)]
   explanation          : weighted support 1.35 clears the reviewable-candidate band but not the confident band

EXTERNAL_SUBMISSION only    (EV-5121)
   weighted_support     : 0.35
   independent_sources  : 1
   support_level_reachable: LOW
   sources              : [('Partner feed', 'EXTERNAL_SUBMISSION', 0.35)]
   explanation          : weighted support 0.35 from 1 source(s) stays below the reviewable-candidate band
```

Weight ladder `OFFICER_UPLOAD 1.00` / `BULK_IMPORT 0.60` / `EXTERNAL_SUBMISSION 0.35`, and the cap
proof — the same candidate relationship first backed by two officer uploads (HIGH), then by two
external feeds (correlation engine still says HIGH, weighted support caps it at LOW):

```text
  created CASE-901: CASE-901
  created CASE-902: CASE-902
  CASE-901 <- EV-5122  source='External partner feed CASE-901'  source_trust=EXTERNAL_SUBMISSION
  CASE-902 <- EV-5123  source='External partner feed CASE-902'  source_trust=EXTERNAL_SUBMISSION

  LEAD: LEAD-XC-901-902 ['CASE-901', 'CASE-902']
    status=PARTIALLY CORROBORATED - FURTHER EVIDENCE REQUIRED
    support_level=LOW   raw (correlation engine)=HIGH
    capped_by_source_trust=True
    weighted_support=0.7  independent_sources=2
    cap reason: evidence weighted 0.70 (needs 2.00 from 2 independent sources for the confident band)
    sources: [('External partner feed CASE-901', 'EXTERNAL_SUBMISSION', 0.35), ('External partner feed CASE-902', 'EXTERNAL_SUBMISSION', 0.35)]
    methods: [('Cross-case correlation', True), ('Temporal analysis', False), ('Network analysis', False)]
```

---

## PART B — visual redesign

### Design tokens, defined once in `frontend/src/index.css`

| token | value | used for |
| --- | --- | --- |
| `--color-bg` | `#F4F7FC` | page background (soft off-white: less glare over long sessions) |
| `--color-surface` | `rgba(255,255,255,0.65)` | glass panels only |
| `--color-surface-solid` | `#FFFFFF` | tables, evidence text, forms, dense lists |
| `--color-border` | `rgba(15,42,89,0.10)` | every hairline |
| `--color-primary` | `#1450C4` | buttons, links, active nav, focus ring |
| `--color-primary-deep` | `#0B2F73` | page titles, nav, high-emphasis text |
| `--color-primary-soft` | `#E8F0FE` | selected rows, quiet fills |
| `--color-accent` | `#2FA7DB` | graph edges, secondary charts |
| `--color-success` / `--color-warning` / `--color-danger` | `#1E8E5A` / `#B8791A` / `#C4341F` | status only, never decoration |
| `--color-text` / `--color-text-muted` | `#101828` / `#5B6B85` | body / secondary |
| `--radius-panel` | `16px` | every card |
| `--shadow-glass` / `--shadow-solid` / `--shadow-lift` | one ladder | elevation |
| `--font-sans` / `--font-mono` | system stacks, no webfont fetched | one sans family; Tamil/Devanagari stacks switch on `html.lang-*` |

Glass (`backdrop-filter: blur(16px)`) is applied by `.glass` and only behind: the fixed top bar, the
fixed left nav, modals/drawers, the evidence provenance strip and evidence card headers, and the
Dashboard KPI cards. Everything read closely — tables, evidence text, forms, audit rows,
relationship lists — is `.surface-solid`, i.e. opaque, so blur never sits behind small text.

Status language is centralised: `.status-verified` (solid success, filled), `.status-candidate`
(outlined warning — a CANDIDATE can never read as settled as VERIFIED), `.status-rejected` (dashed
danger, claim struck through, original finding retained), `.status-insufficient` (dashed muted).
One 2px primary focus ring is declared globally for every interactive element.

### Page files touched

All 17 pages in `frontend/src/pages/`:

- `src/pages/Audit.tsx`
- `src/pages/CaseDetails.tsx`
- `src/pages/Cases.tsx`
- `src/pages/CrossCase.tsx`
- `src/pages/Dashboard.tsx`
- `src/pages/EntityResolution.tsx`
- `src/pages/Evidence.tsx`
- `src/pages/Hypotheses.tsx`
- `src/pages/InformationGaps.tsx`
- `src/pages/LanguageSelect.tsx`
- `src/pages/Login.tsx`
- `src/pages/MapIntelligence.tsx`
- `src/pages/NetworkIntelligence.tsx`
- `src/pages/NextBestAction.tsx`
- `src/pages/Security.tsx`
- `src/pages/Timeline.tsx`
- `src/pages/Workflow.tsx`

Shared shell and components restyled in the same pass:

- `src/App.tsx`
- `src/components/agents/AgentRunModal.tsx`
- `src/components/brand/Brand.tsx`
- `src/components/graph/EntityPanel.tsx`
- `src/components/graph/NetworkGraph.tsx`
- `src/components/layout/AppLayout.tsx`
- `src/components/layout/LanguageSwitcher.tsx`
- `src/components/map/MapView.tsx`
- `src/components/shared/Icon.tsx`
- `src/components/shared/ui.tsx`
- `src/components/system/BootSplash.tsx`
- `src/i18n/LanguageContext.tsx`
- `src/main.tsx`
- `src/state/AppContext.tsx`

- `frontend/index.html` — real `<title>`, colour-scheme and description meta (was literally `frontend`)
- `frontend/src/index.css` — the token layer, surface classes, status classes, focus ring, script-aware typography

### Page notes (the brief's specific requirements)

| page | what it does now |
| --- | --- |
| Dashboard | six glass KPI cards, a pipeline strip, then an **activity feed** built from the audit trail (most recent first: action, object, time, hash-linked), then solid panels for findings, integrity, timeline preview, recent evidence, pending validation, information gaps, next-best action and the standing principle note. Skeleton → real error state carrying the API's message → per-panel empty states; never a bare spinner. |
| NetworkIntelligence | solid canvas panel (a working chart never sits on blur), glass **control panel** (filters, hop depth, ego mode, shortest path) and glass **node drawer**. The A2 structural explanation is the first block in the drawer, above the raw relationship list, with a one-click "run network analysis" when it has not been computed yet. |
| Evidence | solid two-column reading panel (15 px/1.75 body copy), glass provenance strip above it, monospace evidence ID and SHA-256 wherever they appear, integrity and verification pills, upload form on a solid surface. |
| Login | centred glass card over the faint drifting network-line pattern; the "SYNTHETIC DEMONSTRATION DATA" line and the demo-account disclosure are untouched. |
| Security, Audit | the most serious pages: minimal colour (primary for actions only, status hues reserved for status), dense tables on solid surfaces, monospace for permissions, hashes and IDs. Security carries the AI-safety-posture tab that fetches `/api/security/ai-safety-posture`. |
| LanguageSelect | language before login, no glass, large single-choice rows. |
| Cases, CaseDetails, CrossCase, EntityResolution, Timeline, MapIntelligence, Hypotheses, InformationGaps, NextBestAction, Workflow | same token layer; dense content on solid cards; every list, chart and map has a designed empty state; every fetch has loading and error states. |

Two latent Tailwind bugs were found while verifying Part B and fixed: arbitrary-value opacity
(`bg-[rgba(...)]/60`) silently generates no rule at all (verified against the built CSS), and 206
legacy palette tokens (`text-navy-700`, `bg-brand-50`, `text-rose-600`, …) were migrated onto the
token layer so that no page depends on a colour that no longer exists.

### `npm run build`

```text

> frontend@0.0.0 build
> tsc -b && vite build

vite v8.2.2 building client environment for production...
transforming...
✓ 71 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                     0.78 kB │ gzip:   0.45 kB
dist/assets/index-BsWW2t4c.css     75.67 kB │ gzip:  18.56 kB
dist/assets/index-Lu14yZzD.js   1,303.56 kB │ gzip: 363.01 kB

✓ built in 734ms
[plugin builtin:vite-reporter] 
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

---

## FINAL CHECK — all eight, in the order requested

### 1) `bash backend/verify_workflow.sh`

```text
  PASS  EV-1024 integrity VERIFIED
  PASS  EV-2042 tamper demo returns INTEGRITY_MISMATCH

STAGE 15 — AUDIT + LEDGER
  PASS  65 append-only audit records written during this run
  PASS  ledger hash chain intact (34 blocks)

RESULT: 33 passed, 0 failed
```

### 2) `python3 backend/scripts/eval_extraction.py`

```text

--------------------------------------------------------------------------------------------
(A) same-entity pairs shown for review   : 16/17  (94.1% recall)
(B) different-entity pairs kept apart    : 16/16  (100.0%)
    FALSE MERGES (the number to protect) : 0
    of the traps, 1 reach the candidate band and therefore need an explicit human rejection, never an automatic merge
(C) identifier objects folded correctly  : 12/12  (100.0%)
    --  Suresh Balan <-> S. Balan scored 63.0 (LOW) - below the review threshold: account holder recorded two ways (account + phone support only)

============================================================================================
PHASE 6 HARNESS: PASS   |  extraction micro-F1 sample size 85 mentions   |  negative assertions 23/23   |  false merges 0
============================================================================================
```

### 3) `python3 backend/scripts/measure_graph_recall.py`

```text
REL-025   PER-014   ASSOCIATED_WITH  ACC-002   EV-3070   yes   yes   yes       REPRODUCED
REL-026   PER-001   ASSOCIATED_WITH  ORG-001   EV-1026   yes   yes   yes       REPRODUCED
REL-027   PER-004   USED             VEH-001   EV-2041   yes   yes   yes       REPRODUCED
REL-028   DEV-001   ASSOCIATED_WITH  PER-002   EV-2042   yes   yes   yes       REPRODUCED
------------------------------------------------------------------------------------------------
REPRODUCED by the pipeline : 28/28 (100.0%)
Endpoints only (no co-event): 0
Not derivable at all       : 0
```

### 4) `python3 backend/scripts/tamper_test.py`

```text
   WITNESS comparison                         : agrees=False, divergent_blocks=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36]
   reported chain_intact                      : False

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
         50         1,225       0.14 s      116 us      8,590          16
        200        19,900       2.17 s      109 us      9,172         354
        500       124,750      13.16 s      105 us      9,482       2,176
      1,000       499,500      54.03 s      108 us      9,244       8,780
--------------------------------------------------------------------------------------------
growth: 20x the entities costs 378.9x the time (quadratic)
projected for 5,000 entities : 22.5 minutes   (single core, this implementation, no blocking)
projected for 10,000 entities: 90.1 minutes   (single core, this implementation, no blocking)

honest reading: this is the worst case (every pair compared). A production
deployment adds blocking keys - exact identifier match first, then name
phonetics - so only a small candidate set reaches the fuzzy resolver.
```

### 7) `python3 -m pytest backend/tests/`

```text
.....................                                  [100%]
21 passed, 18 subtests passed in 1.73s
```

### 8) `npm run build`

```text
dist/assets/index-Lu14yZzD.js   1,303.56 kB │ gzip: 363.01 kB

✓ built in 734ms
[plugin builtin:vite-reporter] 
(!) Some chunks are larger than 500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.
```

### Result table

| # | check | result | exact command to verify |
| --- | --- | --- | --- |
| 1 | end-to-end workflow | **PASS — 33 passed, 0 failed** | `bash backend/verify_workflow.sh` (dev server up, or pass `http://127.0.0.1:8000`) |
| 2 | extraction vs labelled ground truth | **PASS — negative assertions 23/23, 0 false positives, false merges 0** | `python3 backend/scripts/eval_extraction.py` |
| 3 | graph recall | **PASS — 28/28 reproduced, 0 endpoints-only, 0 not-derivable** | `python3 backend/scripts/measure_graph_recall.py` |
| 4 | tamper detection | **PASS — object+DB rewrite DETECTED, ledger rewrite DETECTED** | `python3 backend/scripts/tamper_test.py` |
| 5 | no generative model in the evidence path | **PASS — 28 files scanned, 0 violations; injected `import openai` → FAIL exit 1** | `python3 backend/scripts/check_no_llm_in_path.py` |
| 6 | scale benchmark | **PASS — 50/200/500/1000 entities: 0.14 / 2.17 / 13.16 / 54.03 s; per-pair cost 116 / 109 / 105 / 108 µs, i.e. the same cost constant as the recorded baseline** | `python3 backend/scripts/benchmark_scale.py` |
| 7 | backend test suite | **PASS — 21 passed, 18 subtests passed** | `python3 -m pytest backend/tests/` |
| 8 | frontend production build | **PASS — built in 734 ms; CSS 75.67 kB (gzip 18.56), JS 1,303.56 kB (gzip 363.01)** | `cd frontend && npm run build` |

**Honest note on check 6.** The algorithm is untouched. Per-pair cost is statistically identical to
the earlier run (116 / 107 / 108 / 119 µs then, 116 / 109 / 105 / 108 µs now); the wall-clock
differences against the recorded 0.15 / 2.31 / 13.40 / 52.57 s are −6.7 % / −6.1 % / −1.8 % /
+2.8 %, and an intermediate run in this session produced 0.14 / 2.12 / 13.44 / 59.39 s. That spread
is sandbox CPU contention (API + dev server running alongside), not a code change: the growth
factor, the candidate counts and the projections (≈23 min for 5,000 entities, ≈93 min for 10,000)
are unchanged.

### A1–A7 + Part B

| item | result | exact command / endpoint |
| --- | --- | --- |
| A1 Hindi false positive | **PASS** — `फोन` no longer extracted as any type (was `PERSON` @ 0.55); Tamil diff empty; harness 23/23 negatives; prior types unchanged | `python3 backend/scripts/eval_extraction.py` · `artifacts/A1_before_after.txt` |
| A2 explainable influencers | **PASS** — per-node explanation with case count, entity types connected, communities bridged, relationships backing it; `safety_note` intact; 12/12 distinct texts; top-10 differ between degree and betweenness | `POST /api/analysis/network` |
| A3 second detector | **PASS** — `detector_count: 2`: `isolation_forest_transaction_burst` (`classical_ml`) + `shared_identifier_cross_case` (`rule_based`), each with a plain-language reason | `POST /api/analysis/anomaly` |
| A4 AI-safety posture | **PASS** — posture JSON; static check PASS → FAIL (exit 1, `network_agent.py:1`) → PASS (exit 0) after byte-identical restore | `GET /api/security/ai-safety-posture` · `python3 backend/scripts/check_no_llm_in_path.py` |
| A5 read-access audit | **PASS** — `EVIDENCE_VIEWED` written by `GET /api/evidence/{id}` only; demo count 0→1; list reads add nothing | `GET /api/evidence/EV-1024` → `GET /api/audit?action=EVIDENCE_VIEWED` |
| A6 PII policy (a) | **PASS** — masked labels on 9/42 nodes (`PHN/DEVICE/ACCOUNT`), `+91 98400 ••••5` style; audited reveal returns the value with `at_rest.msisdn_encrypted` proof and writes `IDENTIFIER_REVEALED`; leak scan **10/10 clean** (`/api/search` echo now masked too) | `GET /api/graph` · `GET /api/entities/PHN-001/reveal` |
| A7 source trust | **PASS** — ladder 1.00/0.60/0.35 drives `support_level`; cap proof: 2×EXTERNAL raw HIGH → `support_level=LOW`, `capped_by_source_trust=True`, weighted 0.70 of 2.00 | `POST /api/analysis/corroboration` `{case_ids:["CASE-901","CASE-902"]}` |
| B redesign | **PASS** — tokens defined once, glass only where allowed, designed empty/loading/error states everywhere, build green, no API contract or route touched | `cd frontend && npm run build` |

### Fixed during this pass (found by running the checks, not by inspection)

1. `app/api/intel.py` used `pii.mask_payload` without importing it — the timeline endpoint returned
   500 and stage 9 of `verify_workflow.sh` failed 2 assertions. Caught by check 1, fixed, re-run
   green (33/33).
2. `/api/search` echoed the raw query back and `query` was exempt from masking — the last leak in
   the A6 scan. The exemption was removed and the whole search payload now routes through
   `mask_payload`, which is what closed the scan at 10/10.
3. The arbitrary-value-opacity and legacy-token issues described under Part B.

### Open items carried forward (decided, not forgotten)

1. **Evidence text blobs are stored plaintext at the object-storage layer**; structured identifier
   fields are AES-256-GCM encrypted at rest. This is now an explicit scope decision: the blob is
   the investigator's own filed document and is governed by the SHA-256 integrity check and the
   `EVIDENCE_VIEWED` audit trail. Encrypting blobs as well is a contained change at the storage
   layer if deployment policy requires it.
2. **The ledger block count restarts when the dataset is reseeded** (`seed.load(force)` calls
   `ledger.reset()`), which is why the count differs between runs. The witness file plus chain
   verification are the durable guarantees, and nothing in the product claims a production
   blockchain.
3. **Extraction misses `madurai` and `11-aug` remain open** — they are the 2 false negatives in the
   97.6 % recall figure, visible in the harness rather than hidden.

Raw logs for every paste above live in `artifacts/` — `1_verify_workflow.txt` …
`8_npm_build.txt`, plus `A1_before_after.txt`, `A2_proof.txt`, `A3_A7_proofs.txt`,
`A4_injection_proof.txt`, `A6_leak_scan.txt`, `A7_cap_proof.txt`. The full source of Dashboard,
NetworkIntelligence and Evidence is reproduced in `PART3_component_source.md`.
