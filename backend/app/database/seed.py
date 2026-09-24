"""SYNTHETIC DEMONSTRATION DATA loader.

Every record produced here is fictional and generated for demonstration only.
It is labelled "SYNTHETIC DEMONSTRATION DATA" at the record level and surfaced as
such in the UI. No real person, vehicle, account or case is represented.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from typing import Any

from ..agents import evidence_agent
from ..audit import audit_log, ledger
from ..database.neo4j_graph import graph_store
from ..database.object_storage import object_storage
from ..database.postgres import relational
from ..models.domain import now_iso
from ..security.crypto import encrypt_field, hash_password

CLASSIFICATION = "SYNTHETIC DEMONSTRATION DATA"

# ---------------------------------------------------------------------------
# USERS
# ---------------------------------------------------------------------------
USERS = [
    {"user_id": "INV-2201", "display_name": "Priya Raman", "role": "INVESTIGATOR",
     "badge": "TN-INV-2201", "unit": "City Crime Branch (synthetic)", "password": "investigate123",
     "case_access": ["CASE-101", "CASE-202", "CASE-512"]},
    {"user_id": "ANL-3310", "display_name": "Karthik Subramanian", "role": "ANALYST",
     "badge": "TN-ANL-3310", "unit": "Intelligence Analysis Cell (synthetic)", "password": "analyze123",
     "case_access": ["CASE-101", "CASE-202", "CASE-305", "CASE-407"]},
    {"user_id": "SUP-1100", "display_name": "Deepa Krishnan", "role": "SUPERVISOR",
     "badge": "TN-SUP-1100", "unit": "Case Review & Verification (synthetic)", "password": "supervise123",
     "case_access": ["*"]},
    {"user_id": "ADM-0001", "display_name": "System Administrator", "role": "ADMIN",
     "badge": "TN-ADM-0001", "unit": "Platform Security (synthetic)", "password": "administer123",
     "case_access": ["*"]},
]

# ---------------------------------------------------------------------------
# CASES
# ---------------------------------------------------------------------------
CASES = [
    {"case_id": "CASE-101", "title": "Chennai Vehicle Theft Network",
     "case_type": "Vehicle Theft", "priority": "HIGH",
     "description": "Series of reported vehicle thefts in the Chennai Central and Guindy corridors. "
                    "Synthetic scenario used to demonstrate evidence-driven network reconstruction.",
     "investigator": "INV-2201", "created_date": "2025-08-11", "status": "ACTIVE"},
    {"case_id": "CASE-202", "title": "Coordinated Property Crime",
     "case_type": "Property Crime", "priority": "HIGH",
     "description": "Property offences reported across T Nagar and Chennai Central with overlapping "
                    "vehicle sightings. Synthetic scenario.",
     "investigator": "INV-2201", "created_date": "2025-08-19", "status": "ACTIVE"},
    {"case_id": "CASE-305", "title": "Cross-Case Financial Association",
     "case_type": "Financial", "priority": "MEDIUM",
     "description": "Unusual account activity potentially associated with entities named in earlier "
                    "synthetic cases. Synthetic scenario.",
     "investigator": "ANL-3310", "created_date": "2025-08-23", "status": "ACTIVE"},
    {"case_id": "CASE-407", "title": "Coimbatore Transport Document Inquiry",
     "case_type": "Document Fraud", "priority": "LOW",
     "description": "Transport documentation irregularities reported by a logistics operator. "
                    "Synthetic scenario providing a weak-signal comparison case.",
     "investigator": "ANL-3310", "created_date": "2025-08-27", "status": "OPEN"},
    {"case_id": "CASE-512", "title": "Unverified Tip — Minimal Evidence",
     "case_type": "Preliminary Inquiry", "priority": "LOW",
     "description": "Single anonymous tip with no supporting records. Deliberately included to "
                    "demonstrate the INSUFFICIENT EVIDENCE pathway.",
     "investigator": "INV-2201", "created_date": "2025-09-01", "status": "OPEN"},
]

# ---------------------------------------------------------------------------
# ENTITIES
# ---------------------------------------------------------------------------
LOCATIONS = [
    ("LOC-001", "Chennai Central", 13.0827, 80.2707, ["CASE-101", "CASE-202"]),
    ("LOC-002", "T Nagar", 13.0418, 80.2341, ["CASE-202"]),
    ("LOC-003", "Guindy Industrial Estate", 13.0067, 80.2206, ["CASE-101", "CASE-305"]),
    ("LOC-004", "Anna Nagar", 13.0850, 80.2101, ["CASE-101"]),
    ("LOC-005", "Chennai Port", 13.1067, 80.2925, ["CASE-305", "CASE-202"]),
    ("LOC-006", "Coimbatore RS Puram", 11.0045, 76.9490, ["CASE-407"]),
]

PERSONS = [
    ("PER-001", "Ravi Kumar", ["CASE-101"], {
        "vehicles": ["TN01AB1234"], "phones": ["+919840012345"],
        "locations": ["CHENNAI CENTRAL", "GUINDY INDUSTRIAL ESTATE"],
        "activity_dates": ["2025-08-10", "2025-08-12"], "role_in_case": "Named in FIR (synthetic)"}),
    ("PER-002", "R. Kumar", ["CASE-202"], {
        "vehicles": ["TN01AB1234"], "phones": ["+919840012345"],
        "locations": ["CHENNAI CENTRAL"], "activity_dates": ["2025-08-18"],
        "role_in_case": "Referenced in police report (synthetic)"}),
    ("PER-003", "Ravi K.", ["CASE-305"], {
        "vehicles": ["TN01AB1234"], "phones": [],
        "locations": ["CHENNAI PORT"], "activity_dates": ["2025-08-25"],
        "role_in_case": "Referenced in intelligence report (synthetic)"}),
    ("PER-004", "Arun Selvam", ["CASE-101", "CASE-202", "CASE-305"], {
        "vehicles": ["TN01AB1234", "TN07XY4455"], "phones": ["+919840099887"],
        "locations": ["CHENNAI CENTRAL", "CHENNAI PORT"],
        "activity_dates": ["2025-08-12", "2025-08-18", "2025-08-25"],
        "role_in_case": "Observed vehicle user (synthetic)"}),
    ("PER-005", "Meena Raghavan", ["CASE-202"], {
        "vehicles": ["TN09KL8899"], "phones": ["+919790011223"],
        "locations": ["CHENNAI CENTRAL", "T NAGAR"], "activity_dates": ["2025-08-18"],
        "role_in_case": "Witness (synthetic)"}),
    ("PER-006", "Suresh Balan", ["CASE-305"], {
        "accounts": ["33901122"], "phones": ["+919566778899"],
        "activity_dates": ["2025-08-22"],
        "role_in_case": "Account holder (synthetic)"}),
    ("PER-007", "Karthik Rajan", ["CASE-101"], {
        "vehicles": ["TN07XY4455"], "locations": ["GUINDY INDUSTRIAL ESTATE"],
        "activity_dates": ["2025-08-12"], "role_in_case": "Observed at scene (synthetic)"}),
    ("PER-008", "Divya Nair", ["CASE-305"], {
        "accounts": ["44120987"], "locations": ["CHENNAI PORT"],
        "activity_dates": ["2025-08-22"], "role_in_case": "Counterparty account holder (synthetic)"}),
    ("PER-009", "Vignesh Anand", ["CASE-202"], {
        "vehicles": ["TN09KL8899"], "locations": ["T NAGAR"],
        "activity_dates": ["2025-08-19"], "role_in_case": "Named in report (synthetic)"}),
    ("PER-010", "Prakash Menon", ["CASE-407"], {
        "vehicles": ["TN22CD3311"], "locations": ["COIMBATORE RS PURAM"],
        "activity_dates": ["2025-08-26"], "role_in_case": "Complainant (synthetic)"}),
    ("PER-011", "Anitha Rao", ["CASE-407"], {
        "vehicles": ["TN38EF7712"], "locations": ["COIMBATORE RS PURAM"],
        "activity_dates": ["2025-08-26"], "role_in_case": "Transport clerk (synthetic)"}),
    ("PER-012", "Mohan Das", ["CASE-101"], {
        "vehicles": ["TN07XY4455"], "locations": ["ANNA NAGAR"],
        "activity_dates": ["2025-08-12"], "role_in_case": "Observed with vehicle (synthetic)"}),
    ("PER-013", "Farhan Ali", ["CASE-202"], {
        "phones": ["+919840099887"], "locations": ["CHENNAI CENTRAL"],
        "activity_dates": ["2025-08-18"], "role_in_case": "Contact in call record (synthetic)"}),
    ("PER-014", "Lakshmi Iyer", ["CASE-305"], {
        "accounts": ["44120987"],
        "activity_dates": ["2025-08-22"], "role_in_case": "Account signatory (synthetic)"}),
    ("PER-015", "Sanjay Prabhu", ["CASE-407"], {
        "vehicles": ["TN22CD3311"], "locations": ["COIMBATORE RS PURAM"],
        "activity_dates": ["2025-08-27"], "role_in_case": "Named in document (synthetic)"}),
]

VEHICLES = [
    ("VEH-001", "TN01AB1234", ["CASE-101", "CASE-202", "CASE-305"]),
    ("VEH-002", "TN07XY4455", ["CASE-101"]),
    ("VEH-003", "TN09KL8899", ["CASE-202"]),
    ("VEH-004", "TN22CD3311", ["CASE-407"]),
    ("VEH-005", "TN38EF7712", ["CASE-407"]),
]

PHONES = [
    ("PHN-001", "+919840012345", ["CASE-101", "CASE-202"]),
    ("PHN-002", "+919840099887", ["CASE-101", "CASE-202"]),
    ("PHN-003", "+919790011223", ["CASE-202"]),
    ("PHN-004", "+919566778899", ["CASE-305"]),
]

ACCOUNTS = [
    ("ACC-001", "33901122", ["CASE-305"]),
    ("ACC-002", "44120987", ["CASE-305"]),
    ("ACC-003", "77650034", ["CASE-407"]),
]

ORGS = [
    ("ORG-001", "Metro Auto Spares", ["CASE-101", "CASE-202"]),
    ("ORG-002", "Coastal Logistics Pvt Ltd", ["CASE-305", "CASE-407"]),
]

DEVICES = [
    ("DEV-001", "IMEI 356938035643809", ["CASE-202"]),
    ("DEV-002", "IMEI 490154203237518", ["CASE-305"]),
]

# ---------------------------------------------------------------------------
# EVIDENCE (synthetic documents)
# ---------------------------------------------------------------------------
EVIDENCE_DOCS: list[dict[str, Any]] = [
    # PHASE 3: every document below is written so that the LIVE pipeline
    # (document_agent -> entity_agent.run -> event extraction) reproduces the
    # relationships in RELATIONSHIPS from the text itself. Each pair is stated in
    # a single sentence with an event trigger, so the relationship is a
    # co-occurrence the extraction layer finds - not a hand-entered fact.
    # Run `python3 scripts/measure_graph_recall.py` to verify.
    {
        "evidence_id": "EV-1024", "case_id": "CASE-101", "evidence_type": "FIR",
        "source": "Police Report", "timestamp": "2025-08-10T18:20:00Z", "uploaded_by": "INV-2201",
        "verification_status": "HUMAN_VERIFIED", "processing_status": "RELATIONSHIPS_CANDIDATE",
        "text": (
            "SYNTHETIC DEMONSTRATION DATA - FIR EXTRACT (CASE-101)\n\n"
            "First Information Report registered at Chennai Central on 10 August 2025.\n"
            "Complainant reported that Ravi Kumar was observed near Chennai Central using vehicle "
            "TN01AB1234 on 10 August, and that the contact number +919840012345 was recorded as "
            "belonging to Ravi Kumar.\n"
            "The same vehicle TN01AB1234 later moved towards Guindy Industrial Estate, where Ravi "
            "Kumar was reported present on 12 August according to the patrol unit.\n"
            "No suspect has been identified or charged. This record is fictional and generated for "
            "demonstration."
        ),
    },
    {
        "evidence_id": "EV-1025", "case_id": "CASE-101", "evidence_type": "CDR",
        "source": "Telecom Record (synthetic)", "timestamp": "2025-08-12T11:05:00Z",
        "uploaded_by": "ANL-3310", "verification_status": "UNVERIFIED",
        "processing_status": "ENTITIES_FOUND",
        "text": (
            "SYNTHETIC DEMONSTRATION DATA - CALL DETAIL RECORD SUMMARY (CASE-101)\n\n"
            "Subscriber +919840012345 contacted +919840099887 on 12 August at 10:15 for 96 "
            "seconds; Arun Selvam is the registered subscriber of +919840099887.\n"
            "A call between +919840012345 and +919840099887 was also recorded on 12 August at "
            "18:40 for 41 seconds.\n"
            "The cell reference for the first record resolves to Guindy Industrial Estate.\n"
            "No content of communication is available; only synthetic metadata is represented."
        ),
    },
    {
        "evidence_id": "EV-1026", "case_id": "CASE-101", "evidence_type": "SURVEILLANCE_REPORT",
        "source": "Field Observation Log (synthetic)", "timestamp": "2025-08-12T13:00:00Z",
        "uploaded_by": "INV-2201", "verification_status": "UNVERIFIED",
        "processing_status": "RELATIONSHIPS_CANDIDATE",
        "text": (
            "SYNTHETIC DEMONSTRATION DATA - FIELD OBSERVATION LOG (CASE-101)\n\n"
            "On 12 August at 12:30, Karthik Rajan was observed beside vehicle TN07XY4455 parked at "
            "Guindy Industrial Estate.\n"
            "Mohan Das was observed with vehicle TN07XY4455 at Anna Nagar earlier on 12 August.\n"
            "Mohan Das was observed beside vehicle TN07XY4455 at Guindy Industrial Estate at 12:40 "
            "on 12 August.\n"
            "Ravi Kumar was reported present at Guindy Industrial Estate at 12:35 according to the "
            "patrol note.\n"
            "Ravi Kumar was also reported visiting the premises of Metro Auto Spares on 12 August.\n"
            "Observation is descriptive only and attributes no offence to any individual."
        ),
    },
    {
        "evidence_id": "EV-2041", "case_id": "CASE-202", "evidence_type": "POLICE_REPORT",
        "source": "Police Report", "timestamp": "2025-08-18T11:00:00Z", "uploaded_by": "INV-2201",
        "verification_status": "HUMAN_VERIFIED", "processing_status": "RELATIONSHIPS_CANDIDATE",
        "text": (
            "SYNTHETIC DEMONSTRATION DATA - POLICE REPORT (CASE-202)\n\n"
            "On 18 August at 10:05, R. Kumar was recorded using vehicle TN01AB1234 at Chennai "
            "Central; the contact number +919840012345 was recorded against that entry.\n"
            "Arun Selvam was observed at Chennai Central at 10:12 using vehicle TN01AB1234.\n"
            "Meena Raghavan, a witness, reported being present at Chennai Central at 10:18, stated "
            "that she had seen vehicle TN09KL8899 in the same parking area, and left the "
            "contact number +919790011223 for further enquiry.\n"
            "No determination of involvement has been made. Fictional demonstration record."
        ),
    },
    {
        "evidence_id": "EV-2042", "case_id": "CASE-202", "evidence_type": "IMAGE",
        "source": "CCTV Still Placeholder (synthetic)", "timestamp": "2025-08-18T10:07:00Z",
        "uploaded_by": "ANL-3310", "verification_status": "UNVERIFIED",
        "processing_status": "PREPROCESSED_SYNTHETIC_TEXT", "tamper_after_registration": True,
        "text": (
            "SYNTHETIC DEMONSTRATION DATA - IMAGE EVIDENCE PLACEHOLDER (CASE-202)\n"
            "This object represents an image-type evidence item. No OCR engine is installed in this "
            "environment, therefore no text has been machine-extracted from an image. The "
            "accompanying preprocessed synthetic description is used to demonstrate the pipeline "
            "honestly.\n"
            "Preprocessed description: vehicle TN01AB1234 was present at Chennai Central on 18 "
            "August at 10:07; the telematics unit recorded as IMEI 356938035643809 was reported "
            "present with R. Kumar as the recorded user of the vehicle."
        ),
    },
    {
        "evidence_id": "EV-2043", "case_id": "CASE-202", "evidence_type": "INTELLIGENCE_REPORT",
        "source": "Intelligence Note (synthetic)", "timestamp": "2025-08-19T09:00:00Z",
        "uploaded_by": "ANL-3310", "verification_status": "UNVERIFIED",
        "processing_status": "RELATIONSHIPS_CANDIDATE",
        "text": (
            "SYNTHETIC DEMONSTRATION DATA - INTELLIGENCE NOTE (CASE-202)\n\n"
            "An unverified note states that Ravi Kumar was reported at Madurai on 18 August at "
            "10:00, which conflicts with the Chennai Central observation recorded in EV-2041 for "
            "the same window.\n"
            "This contradiction is retained deliberately and must not be suppressed during "
            "analysis.\n"
            "Vignesh Anand was reported present with vehicle TN09KL8899 at T Nagar on 19 August.\n"
            "Farhan Ali was reported in contact with the number +919840099887 on 18 August.\n"
            "The note is unverified and carries no evidentiary weight without corroboration."
        ),
    },
    {
        "evidence_id": "EV-3070", "case_id": "CASE-305", "evidence_type": "FINANCIAL_RECORD",
        "source": "Bank Statement Extract (synthetic)", "timestamp": "2025-08-22T16:00:00Z",
        "uploaded_by": "ANL-3310", "verification_status": "UNVERIFIED",
        "processing_status": "RELATIONSHIPS_CANDIDATE",
        "text": (
            "SYNTHETIC DEMONSTRATION DATA - ACCOUNT ACTIVITY EXTRACT (CASE-305)\n\n"
            "Suresh Balan holds account A/C 33901122, which shows a burst of transactions on 22 "
            "August between 14:00 and 15:00; Suresh Balan contacted the bank on +919566778899 "
            "regarding that activity.\n"
            "Counterparty account A/C 44120987 is associated with Divya Nair and was used to "
            "receive transfers from A/C 33901122 on 22 August.\n"
            "Lakshmi Iyer is recorded as a signatory on account A/C 44120987.\n"
            "Baseline activity for account A/C 33901122 is approximately two transactions per "
            "day.\n"
            "Amounts are fictional and generated for demonstration."
        ),
    },
    {
        "evidence_id": "EV-3071", "case_id": "CASE-305", "evidence_type": "INTELLIGENCE_REPORT",
        "source": "Intelligence Note (synthetic)", "timestamp": "2025-08-25T16:00:00Z",
        "uploaded_by": "ANL-3310", "verification_status": "UNVERIFIED",
        "processing_status": "RELATIONSHIPS_CANDIDATE",
        "text": (
            "SYNTHETIC DEMONSTRATION DATA - INTELLIGENCE NOTE (CASE-305)\n\n"
            "Ravi K. was reported present with vehicle TN01AB1234 at Chennai Port on 25 August.\n"
            "Arun Selvam was observed at Chennai Port at 15:20 on 25 August.\n"
            "Coastal Logistics Pvt Ltd was reported to operate a facility located at Chennai "
            "Port in this synthetic dataset.\n"
            "The note is unverified and carries no evidentiary weight without corroboration."
        ),
    },
    {
        "evidence_id": "EV-4090", "case_id": "CASE-407", "evidence_type": "POLICE_REPORT",
        "source": "Police Report", "timestamp": "2025-08-27T12:00:00Z", "uploaded_by": "INV-2201",
        "verification_status": "UNVERIFIED", "processing_status": "RELATIONSHIPS_CANDIDATE",
        "text": (
            "SYNTHETIC DEMONSTRATION DATA - POLICE REPORT (CASE-407)\n\n"
            "Prakash Menon reported documentation irregularities involving vehicle TN22CD3311 at "
            "Coimbatore RS Puram on 26 August.\n"
            "Anitha Rao, a transport clerk, provided a statement at Coimbatore RS Puram on 26 "
            "August and named her employer Coastal Logistics Pvt Ltd.\n"
            "Sanjay Prabhu is named in a transport document that describes vehicle TN22CD3311 "
            "and is dated 27 August.\n"
            "Anitha Rao stated that vehicle TN38EF7712 was also observed parked at Coimbatore RS "
            "Puram that day.\n"
            "No link to Chennai cases has been established from this record alone."
        ),
    },
    {
        "evidence_id": "EV-5120", "case_id": "CASE-512", "evidence_type": "FIR",
        "source": "Anonymous Tip Register (synthetic)", "timestamp": "2025-08-28T09:00:00Z",
        "uploaded_by": "INV-2201", "verification_status": "UNVERIFIED",
        "processing_status": "EXTRACTED",
        "text": (
            "SYNTHETIC DEMONSTRATION DATA - PRELIMINARY TIP (CASE-512)\n\n"
            "An anonymous caller stated that 'something suspicious is happening near the "
            "market'.\n"
            "No name, no vehicle, no phone number, no location detail, no time and no supporting "
            "record were provided. No prior case reference exists.\n"
            "This item exists to demonstrate the INSUFFICIENT EVIDENCE pathway."
        ),
    },
]

# ---------------------------------------------------------------------------
# RELATIONSHIPS
# ---------------------------------------------------------------------------
RELATIONSHIPS = [
    ("REL-001", "PER-001", "VEH-001", "USED", "2025-08-10T09:40:00Z", "EV-1024", "CASE-101", "HIGH", "HUMAN_VERIFIED"),
    ("REL-002", "PER-001", "LOC-001", "OBSERVED_AT", "2025-08-10T09:40:00Z", "EV-1024", "CASE-101", "HIGH", "HUMAN_VERIFIED"),
    ("REL-003", "PER-001", "PHN-001", "USED", "2025-08-10T18:20:00Z", "EV-1024", "CASE-101", "MEDIUM", "UNVERIFIED"),
    ("REL-004", "PHN-001", "PHN-002", "CONNECTED_TO", "2025-08-12T10:15:00Z", "EV-1025", "CASE-101", "MEDIUM", "UNVERIFIED"),
    ("REL-005", "PER-004", "PHN-002", "USED", "2025-08-12T10:15:00Z", "EV-1025", "CASE-101", "MEDIUM", "UNVERIFIED"),
    ("REL-006", "PER-007", "VEH-002", "OBSERVED_AT", "2025-08-12T12:30:00Z", "EV-1026", "CASE-101", "MEDIUM", "UNVERIFIED"),
    ("REL-007", "PER-012", "VEH-002", "OBSERVED_AT", "2025-08-12T12:30:00Z", "EV-1026", "CASE-101", "LOW", "UNVERIFIED"),
    ("REL-008", "VEH-002", "LOC-003", "LOCATED_AT", "2025-08-12T12:30:00Z", "EV-1026", "CASE-101", "MEDIUM", "UNVERIFIED"),
    ("REL-009", "PER-002", "VEH-001", "USED", "2025-08-18T10:05:00Z", "EV-2041", "CASE-202", "HIGH", "HUMAN_VERIFIED"),
    ("REL-010", "PER-002", "LOC-001", "OBSERVED_AT", "2025-08-18T10:05:00Z", "EV-2041", "CASE-202", "HIGH", "HUMAN_VERIFIED"),
    ("REL-011", "PER-004", "LOC-001", "OBSERVED_AT", "2025-08-18T10:12:00Z", "EV-2041", "CASE-202", "MEDIUM", "UNVERIFIED"),
    ("REL-012", "PER-005", "LOC-001", "OBSERVED_AT", "2025-08-18T10:18:00Z", "EV-2041", "CASE-202", "MEDIUM", "UNVERIFIED"),
    ("REL-013", "PER-009", "VEH-003", "USED", "2025-08-19T14:00:00Z", "EV-2043", "CASE-202", "LOW", "UNVERIFIED"),
    ("REL-014", "PER-013", "PHN-002", "CONNECTED_TO", "2025-08-18T11:00:00Z", "EV-2043", "CASE-202", "LOW", "UNVERIFIED"),
    ("REL-015", "PER-006", "ACC-001", "USED", "2025-08-22T14:00:00Z", "EV-3070", "CASE-305", "HIGH", "UNVERIFIED"),
    ("REL-016", "ACC-001", "ACC-002", "TRANSACTED_WITH", "2025-08-22T14:20:00Z", "EV-3070", "CASE-305", "MEDIUM", "UNVERIFIED"),
    ("REL-017", "PER-008", "ACC-002", "USED", "2025-08-24T10:00:00Z", "EV-3070", "CASE-305", "MEDIUM", "UNVERIFIED"),
    ("REL-018", "PER-003", "VEH-001", "USED", "2025-08-25T15:10:00Z", "EV-3071", "CASE-305", "MEDIUM", "UNVERIFIED"),
    ("REL-019", "PER-003", "LOC-005", "OBSERVED_AT", "2025-08-25T15:10:00Z", "EV-3071", "CASE-305", "MEDIUM", "UNVERIFIED"),
    ("REL-020", "PER-004", "LOC-005", "OBSERVED_AT", "2025-08-25T15:20:00Z", "EV-3071", "CASE-305", "MEDIUM", "UNVERIFIED"),
    ("REL-021", "ORG-002", "LOC-005", "LOCATED_AT", "2025-08-25T00:00:00Z", "EV-3071", "CASE-305", "LOW", "UNVERIFIED"),
    ("REL-022", "PER-010", "VEH-004", "USED", "2025-08-26T09:30:00Z", "EV-4090", "CASE-407", "MEDIUM", "UNVERIFIED"),
    ("REL-023", "PER-011", "ORG-002", "PART_OF", "2025-08-26T09:30:00Z", "EV-4090", "CASE-407", "LOW", "UNVERIFIED"),
    ("REL-024", "PER-015", "VEH-004", "MENTIONED_IN", "2025-08-27T10:00:00Z", "EV-4090", "CASE-407", "LOW", "UNVERIFIED"),
    ("REL-025", "PER-014", "ACC-002", "ASSOCIATED_WITH", "2025-08-22T14:35:00Z", "EV-3070", "CASE-305", "LOW", "UNVERIFIED"),
    ("REL-026", "PER-001", "ORG-001", "ASSOCIATED_WITH", "2025-08-12T00:00:00Z", "EV-1026", "CASE-101", "LOW", "UNVERIFIED"),
    ("REL-027", "PER-004", "VEH-001", "USED", "2025-08-18T10:12:00Z", "EV-2041", "CASE-202", "MEDIUM", "UNVERIFIED"),
    ("REL-028", "DEV-001", "PER-002", "ASSOCIATED_WITH", "2025-08-18T10:05:00Z", "EV-2042", "CASE-202", "LOW", "UNVERIFIED"),
]

# ---------------------------------------------------------------------------
# EVENTS
# ---------------------------------------------------------------------------
EVENTS = [
    ("EVT-001", "CASE-101", "Vehicle TN01AB1234 observed near Chennai Central", "2025-08-10T09:40:00Z",
     "LOC-001", ["PER-001", "VEH-001"], "EV-1024", "OBSERVATION"),
    ("EVT-002", "CASE-101", "FIR registered at Chennai Central", "2025-08-10T18:20:00Z",
     "LOC-001", ["PER-001"], "EV-1024", "REPORT"),
    ("EVT-003", "CASE-101", "Call between +919840012345 and +919840099887", "2025-08-12T10:15:00Z",
     "LOC-003", ["PHN-001", "PHN-002", "PER-001", "PER-004"], "EV-1025", "COMMUNICATION"),
    ("EVT-004", "CASE-101", "Vehicle TN07XY4455 observed at Guindy Industrial Estate", "2025-08-12T12:30:00Z",
     "LOC-003", ["VEH-002", "PER-007", "PER-012"], "EV-1026", "OBSERVATION"),
    ("EVT-005", "CASE-101", "Ravi Kumar reported present at Guindy Industrial Estate", "2025-08-12T12:35:00Z",
     "LOC-003", ["PER-001"], "EV-1026", "OBSERVATION"),
    ("EVT-006", "CASE-202", "Vehicle TN01AB1234 observed at Chennai Central", "2025-08-18T10:05:00Z",
     "LOC-001", ["PER-002", "VEH-001"], "EV-2041", "OBSERVATION"),
    ("EVT-007", "CASE-202", "Arun Selvam observed at Chennai Central", "2025-08-18T10:12:00Z",
     "LOC-001", ["PER-004"], "EV-2041", "OBSERVATION"),
    ("EVT-008", "CASE-202", "Witness Meena Raghavan present at Chennai Central", "2025-08-18T10:18:00Z",
     "LOC-001", ["PER-005"], "EV-2041", "CO_PRESENCE"),
    ("EVT-009", "CASE-202", "Conflicting note places Ravi Kumar at Madurai", "2025-08-18T10:00:00Z",
     None, ["PER-001"], "EV-2043", "REPORT"),
    ("EVT-010", "CASE-202", "Vehicle TN09KL8899 associated with Vignesh Anand at T Nagar", "2025-08-19T14:00:00Z",
     "LOC-002", ["PER-009", "VEH-003"], "EV-2043", "OBSERVATION"),
    ("EVT-011", "CASE-305", "Burst of account activity on A/C 33901122", "2025-08-22T14:00:00Z",
     "LOC-003", ["PER-006", "ACC-001", "ACC-002"], "EV-3070", "TRANSACTION"),
    ("EVT-012", "CASE-305", "Counterparty activity recorded for A/C 44120987", "2025-08-24T10:00:00Z",
     "LOC-003", ["PER-008", "ACC-002"], "EV-3070", "TRANSACTION"),
    ("EVT-013", "CASE-305", "Ravi K. reported near Chennai Port with vehicle TN01AB1234", "2025-08-25T15:10:00Z",
     "LOC-005", ["PER-003", "VEH-001"], "EV-3071", "OBSERVATION"),
    ("EVT-014", "CASE-305", "Arun Selvam observed at Chennai Port", "2025-08-25T15:20:00Z",
     "LOC-005", ["PER-004"], "EV-3071", "OBSERVATION"),
    ("EVT-015", "CASE-407", "Documentation irregularity reported at Coimbatore RS Puram", "2025-08-26T09:30:00Z",
     "LOC-006", ["PER-010", "PER-011", "VEH-004"], "EV-4090", "REPORT"),
    ("EVT-016", "CASE-407", "Transport document naming Sanjay Prabhu", "2025-08-27T10:00:00Z",
     "LOC-006", ["PER-015", "VEH-004"], "EV-4090", "REGISTRATION"),
    ("EVT-017", "CASE-512", "Anonymous tip received", "2025-09-01T08:15:00Z",
     None, [], "EV-5120", "REPORT"),
]

CONTRADICTIONS = [
    {
        "contradiction_id": "CON-001", "case_id": "CASE-202",
        "entity_ids": ["PER-001", "PER-002"],
        "statement": "EV-2043 places Ravi Kumar at Madurai at 10:00 on 18 August while EV-2041 records "
                     "the same identity profile at Chennai Central at 10:05 on 18 August.",
        "evidence_ids": ["EV-2041", "EV-2043"],
        "impact": "Weakens the Ravi Kumar ↔ R. Kumar identity hypothesis until independent "
                  "identity confirmation is obtained.",
        "status": "OPEN",
    },
]


# ---------------------------------------------------------------------------
def _register_evidence_objects() -> None:
    for doc in EVIDENCE_DOCS:
        ext = doc.get("object_ext", "txt")
        object_key = f"{doc['case_id']}/{doc['evidence_id']}.{ext}"
        record = {
            "evidence_id": doc["evidence_id"], "case_id": doc["case_id"],
            "evidence_type": doc["evidence_type"], "source": doc["source"],
            "timestamp": doc["timestamp"], "uploaded_by": doc["uploaded_by"],
            "object_key": object_key, "sha256": "",
            "integrity_status": "UNCHECKED",
            "verification_status": doc.get("verification_status", "UNVERIFIED"),
            "processing_status": doc.get("processing_status", "UPLOADED"),
            # SOURCE TRUST (app/analytics/trust.py): the ten synthetic case papers are
            # curator-provided demonstration documents registered through the officer
            # path, so they carry the officer-upload weight. Stated explicitly here so the
            # field is never ambiguous in an API response.
            "source_trust": doc.get("source_trust", "OFFICER_UPLOAD"),
            "provenance": [], "language": "en", "ocr_applied": False,
            "text_origin": ("PREPROCESSED_SYNTHETIC_TEXT"
                            if doc["evidence_type"] in {"IMAGE", "PDF"} else "NATIVE_TEXT"),
            "notes": "", "classification": CLASSIFICATION,
            "size_bytes": len(doc["text"].encode()),
        }
        evidence_agent.register_evidence(record, doc["text"].encode("utf-8"), actor=doc["uploaded_by"])

        if doc.get("tamper_after_registration"):
            # Deliberate demonstration of a post-registration modification made
            # OUTSIDE the application (simulating storage tampering). The registered
            # hash is preserved, so the integrity check will report a MISMATCH.
            object_storage.put_text(
                object_key,
                doc["text"] + "\n[OBJECT MODIFIED AFTER REGISTRATION - DELIBERATE INTEGRITY "
                              "MISMATCH DEMONSTRATION]\n")
            rec = relational.get("evidence", doc["evidence_id"])
            rec["notes"] = ("Demonstration item: the stored object was altered after registration so "
                            "that an integrity check reports INTEGRITY MISMATCH.")
            relational.upsert("evidence", doc["evidence_id"], rec)


def _build_graph() -> None:
    def add(entity_id: str, entity_type: str, label: str, cases: list[str],
            attributes: dict[str, Any] | None = None, lat: float | None = None,
            lon: float | None = None, support: str = "MEDIUM",
            verification: str = "UNVERIFIED") -> None:
        evidence_ids = sorted({r[5] for r in RELATIONSHIPS if entity_id in (r[1], r[2])})
        graph_store.merge_node(entity_id, [entity_type], {
            "entity_id": entity_id, "entity_type": entity_type, "label": label,
            "normalized": label.upper(), "cases": cases, "attributes": attributes or {},
            "evidence_ids": evidence_ids, "verification_status": verification,
            "support_level": support, "lat": lat, "lon": lon,
            "classification": CLASSIFICATION,
        })

    for pid, name, cases, attrs in PERSONS:
        add(pid, "PERSON", name, cases, attrs,
            verification="HUMAN_VERIFIED" if pid in {"PER-001"} else "UNVERIFIED",
            support="HIGH" if pid in {"PER-001", "PER-004"} else "MEDIUM")
    for vid, plate, cases in VEHICLES:
        add(vid, "VEHICLE", plate, cases, {"registration": plate}, support="HIGH")
    for phid, number, cases in PHONES:
        add(phid, "PHONE", number, cases, {"msisdn_encrypted": encrypt_field(number)})
    for aid, number, cases in ACCOUNTS:
        add(aid, "ACCOUNT", f"A/C {number}", cases, {"account_encrypted": encrypt_field(number)})
    for lid, name, lat, lon, cases in LOCATIONS:
        add(lid, "LOCATION", name, cases, {"city": "Chennai" if lid != "LOC-006" else "Coimbatore"},
            lat=lat, lon=lon)
    for oid, name, cases in ORGS:
        add(oid, "ORGANIZATION", name, cases, {})
    for did, label, cases in DEVICES:
        add(did, "DEVICE", label, cases, {})
    for case in CASES:
        graph_store.merge_node(case["case_id"], ["CASE"], {
            "entity_id": case["case_id"], "entity_type": "CASE", "label": case["case_id"],
            "normalized": case["case_id"], "cases": [case["case_id"]],
            "attributes": {"title": case["title"]}, "evidence_ids": [],
            "verification_status": "UNVERIFIED", "support_level": "HIGH",
            "classification": CLASSIFICATION,
        })

    for rid, src, tgt, rtype, ts, evid, case_id, support, verification in RELATIONSHIPS:
        ev = relational.get("evidence", evid) or {}
        graph_store.merge_relationship(rid, src, tgt, rtype, {
            "relationship_id": rid, "rel_type": rtype, "timestamp": ts,
            "evidence_id": evid, "case_id": case_id, "support_level": support,
            "verification_status": verification, "source_document": ev.get("source", "synthetic"),
            "notes": "", "classification": CLASSIFICATION,
        })
        # every entity is linked to the case node and to its evidence provenance
        graph_store.merge_relationship(f"{rid}-CASE", src, case_id, "PART_OF", {
            "relationship_id": f"{rid}-CASE", "rel_type": "PART_OF", "timestamp": ts,
            "evidence_id": evid, "case_id": case_id, "support_level": "HIGH",
            "verification_status": "UNVERIFIED", "source_document": ev.get("source", "synthetic"),
            "hidden": True, "classification": CLASSIFICATION,
        })


def _transactions() -> None:
    rng = random.Random(42)
    rows: list[dict[str, Any]] = []
    counter = 1
    base = datetime(2025, 8, 18)
    # baseline: ~2 transactions/day for four days
    for day in range(4):
        for _ in range(2):
            ts = base + timedelta(days=day, hours=rng.randint(9, 17), minutes=rng.randint(0, 59))
            rows.append({
                "txn_id": f"TXN-{counter:04d}", "account_id": "ACC-001", "case_id": "CASE-305",
                "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "amount": round(rng.uniform(1500, 9000), 2), "counterparty": "ACC-002",
                "evidence_id": "EV-3070", "classification": CLASSIFICATION,
            })
            counter += 1
    # deliberate burst: 50 transactions within one hour on 22 August
    burst = datetime(2025, 8, 22, 14, 0)
    for i in range(50):
        ts = burst + timedelta(seconds=i * 70)
        rows.append({
            "txn_id": f"TXN-{counter:04d}", "account_id": "ACC-001", "case_id": "CASE-305",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "amount": round(rng.uniform(4000, 48000), 2),
            "counterparty": "ACC-002" if i % 3 else "ACC-003",
            "evidence_id": "EV-3070", "classification": CLASSIFICATION,
        })
        counter += 1
    # counterparty account baseline
    for day in range(5):
        ts = datetime(2025, 8, 20) + timedelta(days=day, hours=11)
        rows.append({
            "txn_id": f"TXN-{counter:04d}", "account_id": "ACC-002", "case_id": "CASE-305",
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "amount": round(rng.uniform(2000, 12000), 2), "counterparty": "ACC-001",
            "evidence_id": "EV-3070", "classification": CLASSIFICATION,
        })
        counter += 1
    relational.bulk("transactions", [(r["txn_id"], r) for r in rows])


def load(force: bool = False) -> dict[str, Any]:
    if relational.count("cases") and not force:
        return {"status": "already_loaded"}

    ledger.reset()
    graph_store.clear()
    object_storage.reset()

    for u in USERS:
        relational.insert("users", u["user_id"], {
            "user_id": u["user_id"], "display_name": u["display_name"], "role": u["role"],
            "badge": u["badge"], "unit": u["unit"],
            "password_hash": hash_password(u["password"]),
            "case_access": u["case_access"], "active": True,
            "created_at": now_iso(), "classification": CLASSIFICATION,
        })

    for c in CASES:
        relational.insert("cases", c["case_id"], {**c, "classification": CLASSIFICATION,
                                                  "jurisdiction": "Synthetic Jurisdiction"})

    _register_evidence_objects()
    _build_graph()

    for eid, case_id, title, ts, loc, ents, evid, etype in EVENTS:
        relational.insert("events", eid, {
            "event_id": eid, "case_id": case_id, "title": title, "timestamp": ts,
            "location_id": loc, "entity_ids": ents, "evidence_id": evid,
            "event_type": etype, "description": title, "classification": CLASSIFICATION,
        })

    _transactions()

    for c in CONTRADICTIONS:
        relational.insert("contradictions", c["contradiction_id"], {**c, "classification": CLASSIFICATION})

    # pre-existing human verification records (demonstrates the audit history)
    relational.insert("verifications", "REL-001", {
        "record_id": "VER-0001", "object_id": "REL-001", "object_type": "RELATIONSHIP",
        "case_id": "CASE-101", "decision": "HUMAN_VERIFIED", "verified_by": "SUP-1100",
        "role": "SUPERVISOR", "timestamp": "2025-08-13T10:00:00Z",
        "rationale": "Vehicle usage corroborated by FIR narrative and patrol note.",
        "evidence_ids": ["EV-1024"],
    })

    ledger.append("CASE_REGISTRY_SEALED",
                  {"cases": [c["case_id"] for c in CASES], "classification": CLASSIFICATION})

    audit_log.record("system", "SYSTEM", "SYNTHETIC_DATASET_LOADED",
                     detail=f"{len(CASES)} cases, {len(EVIDENCE_DOCS)} evidence items, "
                            f"{len(RELATIONSHIPS)} relationships, {len(EVENTS)} events "
                            f"({CLASSIFICATION}).")

    return {
        "status": "loaded",
        "classification": CLASSIFICATION,
        "cases": len(CASES),
        "users": len(USERS),
        "entities": graph_store.status()["nodes"],
        "relationships": graph_store.status()["relationships"],
        "evidence": len(EVIDENCE_DOCS),
        "events": len(EVENTS),
        "transactions": relational.count("transactions"),
    }

def entity_labels() -> list[tuple[str, str, str]]:
    """(entity_id, label, entity_type) for every seeded entity - used by the
    Phase 3 recall harness and the Phase 6 evaluation to know the ground-truth
    vocabulary without depending on a loaded graph."""
    rows: list[tuple[str, str, str]] = []
    rows += [(pid, name, "PERSON") for pid, name, _c, _a in PERSONS]
    rows += [(vid, plate, "VEHICLE") for vid, plate, _c in VEHICLES]
    rows += [(phid, number, "PHONE") for phid, number, _c in PHONES]
    rows += [(aid, number, "ACCOUNT") for aid, number, _c in ACCOUNTS]
    rows += [(lid, name, "LOCATION") for lid, name, _lat, _lon, _c in LOCATIONS]
    rows += [(oid, name, "ORGANIZATION") for oid, name, _c in ORGS]
    rows += [(did, label, "DEVICE") for did, label, _c in DEVICES]
    return rows
