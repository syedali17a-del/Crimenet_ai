# CrimeNet AI — Synthetic Dataset Pack

**Evidence → Relationships → Analysis → Validation**

> **SYNTHETIC DEMONSTRATION DATA.** Every file in this pack is fictional. No real person, vehicle, phone number, bank account, case, police station, bank or telecom operator is represented. Nothing here is evidence and nothing here may be used operationally.

Generated 06 September 2026 · 63 files · 3335 KB · 10 folders

---

## 1. Is every dataset type present?

| # | Dataset type asked for | Present | Where | Format(s) |
|---|---|---|---|---|
| 1 | **FIR** | ✅ | `01_FIR/` — 2 files (CASE-101 vehicle theft, CASE-512 anonymous tip) | TXT + PDF |
| 2 | **Police report** | ✅ | `02_POLICE_REPORT/` — 2 files (CASE-202 case diary, CASE-407 enquiry) | TXT + PDF |
| 3 | **CDR** | ✅ | `03_CDR_CALL_DETAIL_RECORDS/` — 2 subscriber dumps + cell-site master + requisition + covering letter | CSV + TXT + PDF |
| 4 | **Financial record** | ✅ | `04_FINANCIAL_RECORDS/` — 2 certified bank statements + requisition | CSV + TXT + PDF |
| 5 | **Surveillance report** | ✅ | `05_SURVEILLANCE_REPORTS/` — Field observation log + ANPR camera log | TXT + PDF + CSV |
| 6 | **Intelligence report** | ✅ | `06_INTELLIGENCE_REPORTS/` — 2 notes graded on the 5×5×5 scale | TXT + PDF |
| 7 | **Image** | ✅ | `07_IMAGE_EVIDENCE/` — 3 stills with camera OSD + EXIF-style metadata | PNG + CSV + TXT |
| 8 | **PDF** | ✅ | `08_PDF_CASE_BUNDLES/` — 5 per-case printable bundles, plus a PDF of every narrative document in its own folder | PDF |
| 9 | **CSV** | ✅ | `09_CSV_STRUCTURED_DATASETS/` — 16 machine-readable registers (cases, entities, relationships, events, transactions…) | CSV |
| + | Chain of custody & s.63 BSA certificates | ✅ (bonus) | `10_CHAIN_OF_CUSTODY_AND_CERTIFICATES/` — 5 custody registers, 3 certificates | TXT |

Every dataset type you listed is present, in the format that artefact really uses.

---

## 2. Why these files look real

| Artefact | Real-world layout it follows |
|---|---|
| FIR | Form **IF1** (Integrated Investigation Form 1) — all 15 numbered items, sections cited under BNS 2023 with the erstwhile IPC equivalents, GD entry reference, delay explanation, property table, despatch-to-court entry |
| Police report | Case diary extract, Part I — Cr. No., sections, IO, timed observation table, assessment, action taken, countersignature |
| CDR | LEA dump column set — `TARGET_MSISDN, CALL_TYPE, A_PARTY, B_PARTY, FIRST_CGI, LAST_CGI, IMEI, IMSI, CIRCLE, ROAMING` — with an MCC-MNC-LAC-CID CGI resolved against a cell-site master, requested under s.94 BNSS |
| Financial record | Certified statement of account — value date, posting date, narration in `UPI/DR/ref/PAYEE/IFSC` form, debit, credit, running balance, IFSC |
| Surveillance report | Static observation log — operation reference, written authority, observation post, timed entries, still-image references, no-intrusion caveat |
| Intelligence report | **5×5×5** national intelligence model — source evaluation A–E, intelligence evaluation 1–5, handling code |
| Image | Camera OSD burnt in (camera id, timestamp, location, REC indicator) plus EXIF-style metadata sidecar |
| Certificates | s.**63(4)(c) Bharatiya Sakshya Adhiniyam 2023** (erstwhile s.65B Evidence Act) electronic-record certificate, with the SHA-256 of the produced file |

Realistic **layout**, entirely fictional **content** — and every page carries a synthetic-data banner and watermark so a printed copy can never be mistaken for a real document.

---

## 3. The dataset in numbers

| Item | Count | Spec minimum | Met |
|---|---|---|---|
| Cases | 5 | 5 | ✅ |
| Persons | 15 | 15 | ✅ |
| Vehicles | 5 | 5 | ✅ |
| Locations | 6 | 5 | ✅ |
| Evidence items | 10 | 5 | ✅ |
| Relationships | 28 | 10 | ✅ |
| Phones / accounts / orgs / devices | 4 / 3 / 2 / 2 | — | ✅ |
| **Entities in total** | **37** (+ 5 case nodes in the graph) | — | ✅ |
| Timeline events | 17 | — | ✅ |
| Financial transactions | 63 | — | ✅ |
| Cross-case overlaps | 8 | ≥1 | ✅ |
| Anomalies | 1 (50-txn burst, 22 Aug 14:00) | ≥1 | ✅ |
| Contradictions | 1 (CON-001, Madurai vs Chennai Central) | ≥1 | ✅ |
| Information gaps | 5 (incl. the missing 15–19 Aug CDR) | ≥1 | ✅ |
| Evidence-poor case | CASE-512 → INSUFFICIENT EVIDENCE | ≥1 | ✅ |

---

## 4. The demonstration scenario, told through the files

| Step | File to open | What it shows |
|---|---|---|
| 1 | `01_FIR/FIR_0412-2025_CASE-101…` | 10 Aug — **Ravi Kumar** with **TN01AB1234** at **Chennai Central** |
| 2 | `03_CDR…/CDR_9840012345…csv` | 12 Aug 10:15 — a 96-second call to +919840099887 off the Guindy cell |
| 3 | `05_SURVEILLANCE…/SURVEILLANCE-REPORT_OP-KAVAL-07…` | 12 Aug — TN07XY4455 and two persons at Guindy |
| 4 | `02_POLICE_REPORT/POLICE-REPORT_Cr-0518-2025…` | 18 Aug — **R. Kumar**, the **same vehicle**, the same location |
| 5 | `06_INTELLIGENCE…/INT-2025-0442…` | The **contradiction**: the same profile reported at Madurai five minutes earlier |
| 6 | `06_INTELLIGENCE…/INT-2025-0517…` | 25 Aug — **Ravi K.** and the same vehicle at Chennai Port |
| 7 | `09_CSV…/CROSS_CASE_OVERLAPS.csv` | The link across all three cases is the **registration number**, not the name |
| 8 | `04_FINANCIAL…/BANK-STATEMENT_AC-33901122…csv` | The 50-transaction burst on 22 Aug that the anomaly detector flags |
| 9 | `03_CDR…/CDR-COVERING-LETTER…` | The **information gap**: no telecom records for 15–19 Aug, so 18 Aug cannot be resolved |
| 10 | `01_FIR/FIR_0731-2025_CASE-512…` | The tip with no particulars → **INSUFFICIENT EVIDENCE** |

The three name variants — *Ravi Kumar*, *R. Kumar*, *Ravi K.* — are **never merged by the system**. They are raised as a candidate identity at 95.0 similarity and left for a human to decide, precisely because CON-001 is unresolved.

---

## 5. Full file inventory

### `01_FIR/`

| File | Format | Evidence | Case | What it is |
|---|---|---|---|---|
| `FIR_0412-2025_CASE-101_Chennai-Central.pdf` | PDF | EV-1024 | CASE-101 | First Information Report, Form IF1 layout, vehicle theft, Chennai Central (PDF rendering) |
| `FIR_0412-2025_CASE-101_Chennai-Central.txt` | TXT | EV-1024 | CASE-101 | First Information Report, Form IF1 layout, vehicle theft, Chennai Central |
| `FIR_0731-2025_CASE-512_Anonymous-Tip.pdf` | PDF | EV-5120 | CASE-512 | Anonymous tip register entry with no particulars - drives the INSUFFICIENT EVIDENCE pathway (PDF rendering) |
| `FIR_0731-2025_CASE-512_Anonymous-Tip.txt` | TXT | EV-5120 | CASE-512 | Anonymous tip register entry with no particulars - drives the INSUFFICIENT EVIDENCE pathway |

### `02_POLICE_REPORT/`

| File | Format | Evidence | Case | What it is |
|---|---|---|---|---|
| `POLICE-REPORT_Cr-0518-2025_CASE-202_Chennai-Central.pdf` | PDF | EV-2041 | CASE-202 | Case diary extract recording the 18 Aug Chennai Central observations (PDF rendering) |
| `POLICE-REPORT_Cr-0518-2025_CASE-202_Chennai-Central.txt` | TXT | EV-2041 | CASE-202 | Case diary extract recording the 18 Aug Chennai Central observations |
| `POLICE-REPORT_Enq-0134-2025_CASE-407_Coimbatore.pdf` | PDF | EV-4090 | CASE-407 | Preliminary enquiry note, Coimbatore document irregularity (PDF rendering) |
| `POLICE-REPORT_Enq-0134-2025_CASE-407_Coimbatore.txt` | TXT | EV-4090 | CASE-407 | Preliminary enquiry note, Coimbatore document irregularity |

### `03_CDR_CALL_DETAIL_RECORDS/`

| File | Format | Evidence | Case | What it is |
|---|---|---|---|---|
| `CDR-COVERING-LETTER_STL-2025-2214.pdf` | PDF | EV-1025 | CASE-101 | Covering letter (PDF rendering) |
| `CDR-COVERING-LETTER_STL-2025-2214.txt` | TXT | EV-1025 | CASE-101 | Operator covering letter; states the 15-19 Aug records were NOT furnished - this is the deliberate information gap |
| `CDR-REQUISITION_Cr-0412-2025_CASE-101.pdf` | PDF | EV-1025 | CASE-101 | Requisition letter (PDF rendering) |
| `CDR-REQUISITION_Cr-0412-2025_CASE-101.txt` | TXT | EV-1025 | CASE-101 | Requisition to the telecom nodal officer under s.94 BNSS |
| `CDR_9840012345_2025-08-10_to_2025-08-14.csv` | CSV | EV-1025 | CASE-101 | Call detail records for +919840012345 (PHN-001), LEA dump layout |
| `CDR_9840099887_2025-08-10_to_2025-08-14.csv` | CSV | EV-1025 | CASE-101 | Call detail records for +919840099887 (PHN-002), LEA dump layout |
| `CELL-SITE-MASTER.csv` | CSV | EV-1025 | CASE-101 | CGI to tower address / lat-lon mapping for every cell in the CDRs |

### `04_FINANCIAL_RECORDS/`

| File | Format | Evidence | Case | What it is |
|---|---|---|---|---|
| `BANK-REQUISITION_CASE-305.txt` | TXT | EV-3070 | CASE-305 | Requisition to the bank nodal officer under s.94 BNSS |
| `BANK-STATEMENT-COVER_AC-33901122_Suresh-Balan_Aug2025.pdf` | PDF | EV-3070 | CASE-305 | Statement cover (PDF) |
| `BANK-STATEMENT-COVER_AC-33901122_Suresh-Balan_Aug2025.txt` | TXT | EV-3070 | CASE-305 | Certified statement cover page for ACC-001 |
| `BANK-STATEMENT-COVER_AC-44120987_Divya-Nair_Aug2025.pdf` | PDF | EV-3070 | CASE-305 | Statement cover (PDF) |
| `BANK-STATEMENT-COVER_AC-44120987_Divya-Nair_Aug2025.txt` | TXT | EV-3070 | CASE-305 | Certified statement cover page for ACC-002 |
| `BANK-STATEMENT_AC-33901122_Suresh-Balan_Aug2025.csv` | CSV | EV-3070 | CASE-305 | Transaction rows for ACC-001 with running balance - the exact rows the platform analyses |
| `BANK-STATEMENT_AC-44120987_Divya-Nair_Aug2025.csv` | CSV | EV-3070 | CASE-305 | Transaction rows for ACC-002 with running balance - the exact rows the platform analyses |

### `05_SURVEILLANCE_REPORTS/`

| File | Format | Evidence | Case | What it is |
|---|---|---|---|---|
| `ANPR-CAMERA-LOG_Aug2025.csv` | CSV | EV-1026 | MULTI | Automatic number plate reader log across 5 camera sites; 8 evidenced reads plus routine traffic |
| `SURVEILLANCE-REPORT_OP-KAVAL-07_CASE-101_Guindy.pdf` | PDF | EV-1026 | CASE-101 | Field observation log (PDF rendering) |
| `SURVEILLANCE-REPORT_OP-KAVAL-07_CASE-101_Guindy.txt` | TXT | EV-1026 | CASE-101 | Static field observation log, Guindy Industrial Estate |

### `06_INTELLIGENCE_REPORTS/`

| File | Format | Evidence | Case | What it is |
|---|---|---|---|---|
| `INTELLIGENCE-REPORT_INT-2025-0442_CASE-202.pdf` | PDF | EV-2043 | CASE-202 | 5x5x5-graded note carrying the deliberate Madurai / Chennai Central contradiction (PDF rendering) |
| `INTELLIGENCE-REPORT_INT-2025-0442_CASE-202.txt` | TXT | EV-2043 | CASE-202 | 5x5x5-graded note carrying the deliberate Madurai / Chennai Central contradiction |
| `INTELLIGENCE-REPORT_INT-2025-0517_CASE-305.pdf` | PDF | EV-3071 | CASE-305 | 5x5x5-graded note placing TN01AB1234 at Chennai Port (PDF rendering) |
| `INTELLIGENCE-REPORT_INT-2025-0517_CASE-305.txt` | TXT | EV-3071 | CASE-305 | 5x5x5-graded note placing TN01AB1234 at Chennai Port |

### `07_IMAGE_EVIDENCE/`

| File | Format | Evidence | Case | What it is |
|---|---|---|---|---|
| `EV-1026_surveillance-still_Guindy_2025-08-12T1230Z.png` | PNG | EV-1026 | CASE-101 | Illustrative surveillance still accompanying the Guindy observation log |
| `EV-2042_CCTV-still_Chennai-Central_2025-08-18T1007Z.png` | PNG | EV-2042 | CASE-202 | CCTV still backing EV-2042. The registered copy of this object is the one deliberately altered so the SHA-256 check reports a mismatch |
| `EV-2042b_ANPR-plate-crop_Chennai-Central_2025-08-18T1007Z.png` | PNG | EV-2042 | CASE-202 | Composited ANPR plate crop showing TN01AB1234 - the identifier that links CASE-101, CASE-202 and CASE-305 |
| `IMAGE-EVIDENCE-METADATA.csv` | CSV | EV-2042 | CASE-202 | EXIF-style metadata for every image, including the explicit 'no OCR was performed' declaration |
| `README_IMAGE_HONESTY_NOTE.txt` | TXT | — | — | Plain statement of what the images are and are not |

### `08_PDF_CASE_BUNDLES/`

| File | Format | Evidence | Case | What it is |
|---|---|---|---|---|
| `CASE-101_EVIDENCE-BUNDLE.pdf` | PDF | — | CASE-101 | Every narrative document for CASE-101 in one printable PDF (3 evidence items) |
| `CASE-202_EVIDENCE-BUNDLE.pdf` | PDF | — | CASE-202 | Every narrative document for CASE-202 in one printable PDF (3 evidence items) |
| `CASE-305_EVIDENCE-BUNDLE.pdf` | PDF | — | CASE-305 | Every narrative document for CASE-305 in one printable PDF (2 evidence items) |
| `CASE-407_EVIDENCE-BUNDLE.pdf` | PDF | — | CASE-407 | Every narrative document for CASE-407 in one printable PDF (1 evidence items) |
| `CASE-512_EVIDENCE-BUNDLE.pdf` | PDF | — | CASE-512 | Every narrative document for CASE-512 in one printable PDF (1 evidence items) |

### `09_CSV_STRUCTURED_DATASETS/`

| File | Format | Evidence | Case | What it is |
|---|---|---|---|---|
| `CASES.csv` | CSV | — | — | 5 cases including the deliberately evidence-poor CASE-512 |
| `CONTRADICTIONS.csv` | CSV | — | — | The open contradiction CON-001 |
| `CROSS_CASE_OVERLAPS.csv` | CSV | — | — | Every shared identifier between cases, with the basis for the link |
| `ENTITIES_ACCOUNTS.csv` | CSV | — | — | 3 bank accounts |
| `ENTITIES_LOCATIONS.csv` | CSV | — | — | 6 locations with coordinates |
| `ENTITIES_MASTER.csv` | CSV | — | — | All 37 entities of all 7 types in one register |
| `ENTITIES_ORGS_AND_DEVICES.csv` | CSV | — | — | 2 organisations, 2 devices |
| `ENTITIES_PERSONS.csv` | CSV | — | — | 15 persons with their identifiers |
| `ENTITIES_PHONES.csv` | CSV | — | — | 4 phone numbers and CDR availability |
| `ENTITIES_VEHICLES.csv` | CSV | — | — | 5 vehicles and their case spread |
| `EVENTS_TIMELINE.csv` | CSV | — | — | 17 timeline events, 10-27 Aug 2025 |
| `EVIDENCE_REGISTER.csv` | CSV | — | — | 10 evidence items mapped to the source file in this pack that backs each one |
| `EXPECTED_ANALYSIS_OUTCOMES.csv` | CSV | — | — | What the platform should output for each stage - use this to check the demo live |
| `RELATIONSHIPS.csv` | CSV | — | — | 28 relationships, each citing the evidence id that supports it |
| `TRANSACTIONS.csv` | CSV | — | — | 63 transactions: baseline plus the 50-transaction burst that the anomaly detector flags |
| `USERS_AND_RBAC.csv` | CSV | — | — | 4 demo accounts, roles and case-level access |

### `10_CHAIN_OF_CUSTODY_AND_CERTIFICATES/`

| File | Format | Evidence | Case | What it is |
|---|---|---|---|---|
| `CERTIFICATE-63-BSA_BCBK-CERT-2025-0881_EV-3070.txt` | TXT | EV-3070 | CASE-305 | s.63(4)(c) BSA 2023 electronic-record certificate for EV-3070 |
| `CERTIFICATE-63-BSA_CCTV-CERT-2025-0119_EV-2042.txt` | TXT | EV-2042 | CASE-202 | s.63(4)(c) BSA 2023 electronic-record certificate for EV-2042 |
| `CERTIFICATE-63-BSA_STL-CERT-2025-2214_EV-1025.txt` | TXT | EV-1025 | CASE-101 | s.63(4)(c) BSA 2023 electronic-record certificate for EV-1025 |
| `CHAIN-OF-CUSTODY_EV-1024.txt` | TXT | EV-1024 | CASE-101 | Chain of custody / evidence movement register for EV-1024 |
| `CHAIN-OF-CUSTODY_EV-1025.txt` | TXT | EV-1025 | CASE-101 | Chain of custody / evidence movement register for EV-1025 |
| `CHAIN-OF-CUSTODY_EV-2041.txt` | TXT | EV-2041 | CASE-202 | Chain of custody / evidence movement register for EV-2041 |
| `CHAIN-OF-CUSTODY_EV-2042.txt` | TXT | EV-2042 | CASE-202 | Chain of custody / evidence movement register for EV-2042 |
| `CHAIN-OF-CUSTODY_EV-3070.txt` | TXT | EV-3070 | CASE-305 | Chain of custody / evidence movement register for EV-3070 |

---

## 6. Integrity of the pack itself

`DATASET_MANIFEST.csv` lists every file with its **SHA-256** digest, size, dataset type, and the evidence id and case it belongs to. To prove no file has been changed since generation:

```bash
cd datasets
python3 - <<'PY'
import csv, hashlib, pathlib
bad = 0
for r in csv.DictReader(open('DATASET_MANIFEST.csv')):
    h = hashlib.sha256(pathlib.Path(r['FILE_PATH']).read_bytes()).hexdigest()
    if h != r['SHA256']:
        bad += 1; print('MISMATCH', r['FILE_PATH'])
print('OK' if not bad else f'{bad} mismatched')
PY
```

This is the same principle the platform applies to evidence: hash at registration, re-hash on demand, report any difference rather than hide it.

---

## 7. How this pack relates to the running application

These files are generated **from the application's own seed data** (`backend/app/database/seed.py`) by `tools/build_datasets.py`, which reads that file directly. So the paperwork and the running demo can never drift apart: every name, plate, number, amount and timestamp in this pack is the same value the application serves through its API.

`09_CSV_STRUCTURED_DATASETS/EVIDENCE_REGISTER.csv` maps each of the 10 evidence items to the exact file here that backs it, and `EXPECTED_ANALYSIS_OUTCOMES.csv` states what the platform should output at each of the 13 pipeline stages — so the dataset can be checked against the live demo, stage by stage.

Regenerate at any time with:

```bash
python3 -m tools.build_datasets
```
