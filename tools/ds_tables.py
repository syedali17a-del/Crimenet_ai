"""Structured (CSV) synthetic datasets for the CrimeNet AI dataset pack.

Column layouts follow the shape of the real artefact: LEA call-detail-record
dumps, ANPR camera logs, bank statement extracts and entity/relationship
registers. Every row carries a CLASSIFICATION column so no record can be
detached from its synthetic label.
"""
from __future__ import annotations

import csv
import io
import random
from datetime import datetime, timedelta

from . import ds_source as S

CLS = S.CLASSIFICATION


def to_csv(header: list[str], rows: list[list]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(header)
    w.writerows(rows)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# CELL SITE MASTER
# ---------------------------------------------------------------------------
CELL_SITES = [
    # cgi, lac, cid, site name, address, lat, lon, loc_id
    ("404-85-2201-14501", "2201", "14501", "CHN_CENTRAL_01",
     "Poonamallee High Road, Chennai Central, Chennai 600003", 13.0827, 80.2707, "LOC-001"),
    ("404-85-2201-14502", "2201", "14502", "CHN_CENTRAL_02",
     "Wall Tax Road, Chennai Central, Chennai 600003", 13.0841, 80.2731, "LOC-001"),
    ("404-85-2203-14812", "2203", "14812", "TNAGAR_01",
     "Usman Road, T Nagar, Chennai 600017", 13.0418, 80.2341, "LOC-002"),
    ("404-85-2205-15104", "2205", "15104", "GUINDY_IE_01",
     "Industrial Estate Main Road, Guindy, Chennai 600032", 13.0067, 80.2206, "LOC-003"),
    ("404-85-2205-15105", "2205", "15105", "GUINDY_IE_02",
     "Unit 14 Approach Road, Guindy, Chennai 600032", 13.0079, 80.2218, "LOC-003"),
    ("404-85-2207-15330", "2207", "15330", "ANNANAGAR_01",
     "2nd Avenue, Anna Nagar, Chennai 600040", 13.0850, 80.2101, "LOC-004"),
    ("404-85-2209-15602", "2209", "15602", "CHNPORT_01",
     "Rajaji Salai, Chennai Port, Chennai 600001", 13.1067, 80.2925, "LOC-005"),
    ("404-85-3301-21105", "3301", "21105", "CBE_RSPURAM_01",
     "D B Road, R S Puram, Coimbatore 641002", 11.0045, 76.9490, "LOC-006"),
]
CGI_BY_LOC = {}
for _c in CELL_SITES:
    CGI_BY_LOC.setdefault(_c[7], _c)


def cell_site_master_csv() -> str:
    header = ["CGI", "MCC_MNC", "LAC", "CELL_ID", "SITE_NAME", "SITE_ADDRESS",
              "LATITUDE", "LONGITUDE", "AZIMUTH_DEG", "COVERAGE_RADIUS_M",
              "MAPPED_LOCATION_ID", "OPERATOR", "CLASSIFICATION"]
    rows = []
    rng = random.Random(11)
    for cgi, lac, cid, name, addr, lat, lon, loc in CELL_SITES:
        rows.append([cgi, "404-85", lac, cid, name, addr, lat, lon,
                     rng.choice([0, 120, 240]), rng.choice([450, 600, 800, 1100]),
                     loc, "Synthetic Telecom Ltd (STL)", CLS])
    return to_csv(header, rows)


# ---------------------------------------------------------------------------
# CALL DETAIL RECORDS
# ---------------------------------------------------------------------------
SUBSCRIBERS = {
    "+919840012345": {
        "imei": "356938035643809", "imsi": "404859123456789",
        "subscriber": "Ravi Kumar (as recorded in the FIR - identity unverified)",
        "entity": "PHN-001", "device_entity": "DEV-001", "home_cgi": "404-85-2201-14501",
    },
    "+919840099887": {
        "imei": "359881034512906", "imsi": "404859987654321",
        "subscriber": "Arun Selvam (registered subscriber, synthetic)",
        "entity": "PHN-002", "device_entity": "NOT_IN_GRAPH", "home_cgi": "404-85-2205-15104",
    },
}

# Non-case filler numbers - deliberately NOT entities in the demo graph.
FILLER_NUMBERS = ["+919003471182", "+919176554023", "+918939220417",
                  "+919600713948", "+917299018866", "+919789334105",
                  "18002094455", "+919841200377"]


def _cdr_rows_for(target: str) -> list[list]:
    """Deterministic CDR for 10-14 Aug 2025 (the period the operator furnished)."""
    meta = SUBSCRIBERS[target]
    other = "+919840099887" if target == "+919840012345" else "+919840012345"
    rng = random.Random(hash(target) % 9973)
    rows: list[list] = []
    seq = 1

    def add(dt: datetime, ctype: str, a: str, b: str, dur: int, cgi: str) -> None:
        nonlocal seq
        site = next(c for c in CELL_SITES if c[0] == cgi)
        rows.append([
            f"{target[-10:]}-{seq:04d}", target, ctype, a, b,
            dt.strftime("%d/%m/%Y"), dt.strftime("%H:%M:%S"), dur,
            cgi, cgi, site[4], site[4], site[5], site[6],
            meta["imei"], meta["imsi"], "GSM", "TAMIL NADU",
            "N", "STL_LEA_DUMP_v3", CLS,
        ])
        seq += 1

    # --- 10 Aug: activity around Chennai Central, then movement to Guindy
    add(datetime(2025, 8, 10, 8, 52, 11), "OUT", target, FILLER_NUMBERS[0], 47,
        "404-85-2201-14501")
    if target == "+919840012345":
        add(datetime(2025, 8, 10, 9, 38, 26), "IN", FILLER_NUMBERS[1], target, 112,
            "404-85-2201-14501")
        add(datetime(2025, 8, 10, 9, 47, 3), "SMS-OUT", target, FILLER_NUMBERS[2], 0,
            "404-85-2201-14502")
        add(datetime(2025, 8, 10, 10, 21, 40), "OUT", target, FILLER_NUMBERS[3], 63,
            "404-85-2205-15104")
        add(datetime(2025, 8, 10, 17, 4, 55), "IN", FILLER_NUMBERS[4], target, 28,
            "404-85-2205-15104")
    else:
        add(datetime(2025, 8, 10, 11, 15, 9), "IN", FILLER_NUMBERS[5], target, 205,
            "404-85-2205-15104")
        add(datetime(2025, 8, 10, 19, 30, 44), "OUT", target, FILLER_NUMBERS[6], 19,
            "404-85-2205-15105")

    # --- 11 Aug: routine filler
    for _ in range(3):
        dt = datetime(2025, 8, 11, rng.randint(8, 21), rng.randint(0, 59), rng.randint(0, 59))
        add(dt, rng.choice(["IN", "OUT", "SMS-IN"]),
            target if rng.random() > 0.5 else rng.choice(FILLER_NUMBERS),
            rng.choice(FILLER_NUMBERS), rng.randint(0, 240), meta["home_cgi"])

    # --- 12 Aug 10:15:00 : THE evidenced call (EV-1025), 96 seconds, Guindy cell
    if target == "+919840012345":
        add(datetime(2025, 8, 12, 10, 15, 0), "OUT", target, other, 96, "404-85-2205-15104")
    else:
        add(datetime(2025, 8, 12, 10, 15, 0), "IN", other, target, 96, "404-85-2205-15104")

    add(datetime(2025, 8, 12, 12, 41, 18), "SMS-IN", FILLER_NUMBERS[7], target, 0,
        "404-85-2205-15104")
    add(datetime(2025, 8, 12, 18, 9, 2), "OUT", target, FILLER_NUMBERS[2], 74,
        "404-85-2207-15330" if target == "+919840012345" else "404-85-2205-15105")

    # --- 13-14 Aug: routine filler
    for day in (13, 14):
        for _ in range(rng.randint(2, 3)):
            dt = datetime(2025, 8, day, rng.randint(8, 21), rng.randint(0, 59), rng.randint(0, 59))
            b = rng.choice(FILLER_NUMBERS)
            ctype = rng.choice(["IN", "OUT", "SMS-OUT"])
            a = target if ctype.endswith("OUT") else b
            bb = b if ctype.endswith("OUT") else target
            add(dt, ctype, a, bb, 0 if ctype.startswith("SMS") else rng.randint(11, 380),
                rng.choice([meta["home_cgi"], "404-85-2201-14501", "404-85-2205-15105"]))

    rows.sort(key=lambda r: (r[5].split("/")[::-1], r[6]))
    for i, r in enumerate(rows, 1):
        r[0] = f"{target[-10:]}-{i:04d}"
    return rows


CDR_HEADER = ["RECORD_ID", "TARGET_MSISDN", "CALL_TYPE", "A_PARTY", "B_PARTY",
              "CALL_DATE", "CALL_TIME", "DURATION_SEC", "FIRST_CGI", "LAST_CGI",
              "FIRST_CELL_ADDRESS", "LAST_CELL_ADDRESS", "LATITUDE", "LONGITUDE",
              "IMEI", "IMSI", "SERVICE_TYPE", "CIRCLE", "ROAMING",
              "RECORD_SOURCE", "CLASSIFICATION"]


def cdr_csv(target: str) -> str:
    return to_csv(CDR_HEADER, _cdr_rows_for(target))


def cdr_covering_letter() -> str:
    from .ds_documents import banner, kv, RULE, footer, OFFICIALS, W
    return "\n".join([
        banner("Telecom Covering Letter"),
        "SYNTHETIC TELECOM LTD. - LAW ENFORCEMENT LIAISON".center(W),
        "COVERING LETTER - PRODUCTION OF CALL DETAIL RECORDS".center(W),
        "",
        RULE,
        kv(" Our reference", "STL/LEA/CHN/2025/08/2214"),
        kv(" Your requisition", "Cr. No. 0412/2025 / CDR / 03 dated 12/08/2025"),
        kv(" Date of production", "14/08/2025"),
        kv(" Produced to", OFFICIALS["cc_sho"]),
        RULE,
        "",
        " 1. RECORDS FURNISHED",
        "",
        "    (a) +91 98400 12345  -  10/08/2025 to 14/08/2025  (file: CDR_9840012345_...csv)",
        "    (b) +91 98400 99887  -  10/08/2025 to 14/08/2025  (file: CDR_9840099887_...csv)",
        "    (c) Cell site master for the CGIs appearing above (CELL-SITE-MASTER.csv)",
        "",
        " 2. RECORDS NOT FURNISHED  ** THIS IS A DELIBERATE INFORMATION GAP **",
        "",
        "    Records for the period 15/08/2025 to 19/08/2025 are NOT included in this",
        "    production. The requisitioned dump was generated before that period closed.",
        "    A fresh requisition is required for the later period.",
        "",
        "    Consequence for the investigation: there is NO call-detail evidence covering",
        "    18/08/2025. The location of either subscriber on 18/08/2025 therefore CANNOT",
        "    be established from telecom metadata, and the conflict between the Chennai",
        "    Central observation (EV-2041) and the Madurai claim (EV-2043) CANNOT be",
        "    resolved from these records. The platform must report this as an information",
        "    gap and must not infer a location.",
        "",
        " 3. LIMITATIONS",
        "    (a) No content of communication is held or produced.",
        "    (b) Cell site indicates the serving cell only; it is an approximation of",
        "        location and is not a positioning fix.",
        "    (c) Subscriber particulars reflect the records of the operator and are not",
        "        independent proof of the identity of the person using the handset.",
        "",
        " 4. Certificate under Section 63(4)(c) BSA 2023 is enclosed separately.",
        "",
        "                                       For Synthetic Telecom Ltd.",
        "                                       /s/ Nodal Officer (LEA), Chennai Circle",
        footer("STL/LEA/CHN/2025/08/2214 (synthetic)", "EV-1025", "CASE-101"),
    ])


# ---------------------------------------------------------------------------
# ANPR CAMERA LOG
# ---------------------------------------------------------------------------
def anpr_csv() -> str:
    header = ["READ_ID", "CAMERA_ID", "CAMERA_LOCATION", "MAPPED_LOCATION_ID",
              "LATITUDE", "LONGITUDE", "DIRECTION", "READ_TIMESTAMP", "PLATE_TEXT",
              "OCR_CONFIDENCE", "VEHICLE_CLASS", "IMAGE_REF", "HOTLIST_HIT",
              "LINKED_CASE", "CLASSIFICATION"]
    cams = {
        "LOC-001": ("CAM-CHN-CENTRAL-04", "Chennai Central approach road", 13.0827, 80.2707),
        "LOC-002": ("CAM-TNGR-USMAN-11", "Usman Road, T Nagar", 13.0418, 80.2341),
        "LOC-003": ("CAM-GNDY-IE-07", "Industrial Estate Main Road, Guindy", 13.0067, 80.2206),
        "LOC-005": ("CAM-PORT-RAJAJI-02", "Rajaji Salai, Chennai Port", 13.1067, 80.2925),
        "LOC-006": ("CAM-CBE-DBROAD-05", "D B Road, R S Puram, Coimbatore", 11.0045, 76.9490),
    }
    evidenced = [
        ("LOC-001", "2025-08-10T09:40:12Z", "TN01AB1234", "IN", 0.97, "CASE-101"),
        ("LOC-003", "2025-08-10T10:24:38Z", "TN01AB1234", "IN", 0.93, "CASE-101"),
        ("LOC-003", "2025-08-12T12:30:05Z", "TN07XY4455", "IN", 0.95, "CASE-101"),
        ("LOC-001", "2025-08-18T10:05:41Z", "TN01AB1234", "IN", 0.96, "CASE-202"),
        ("LOC-002", "2025-08-19T14:00:52Z", "TN09KL8899", "OUT", 0.88, "CASE-202"),
        ("LOC-005", "2025-08-25T15:10:19Z", "TN01AB1234", "IN", 0.91, "CASE-305"),
        ("LOC-006", "2025-08-26T09:30:47Z", "TN22CD3311", "IN", 0.94, "CASE-407"),
        ("LOC-006", "2025-08-26T09:41:06Z", "TN38EF7712", "OUT", 0.90, "CASE-407"),
    ]
    rng = random.Random(23)
    filler_plates = ["TN02BK7741", "TN05CH2290", "TN10DA5518", "TN11EX9032",
                     "TN14FG1177", "TN18HJ6604", "TN21KM3345", "TN37LQ8820",
                     "KA03MN4412", "AP09PQ7756"]
    rows: list[list] = []
    n = 1
    for loc, ts, plate, direction, conf, case in evidenced:
        cam = cams[loc]
        rows.append([f"ANPR-{n:05d}", cam[0], cam[1], loc, cam[2], cam[3], direction, ts,
                     plate, conf, "LMV", f"{cam[0]}/{ts[:10].replace('-', '')}/{n:05d}.jpg",
                     "Y", case, CLS])
        n += 1
    for _ in range(34):
        loc = rng.choice(list(cams))
        cam = cams[loc]
        day = rng.choice([10, 11, 12, 13, 18, 19, 22, 25, 26])
        ts = datetime(2025, 8, day, rng.randint(6, 21), rng.randint(0, 59), rng.randint(0, 59))
        rows.append([f"ANPR-{n:05d}", cam[0], cam[1], loc, cam[2], cam[3],
                     rng.choice(["IN", "OUT"]), ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     rng.choice(filler_plates), round(rng.uniform(0.71, 0.99), 2),
                     rng.choice(["LMV", "LMV", "MCWG", "HGV"]),
                     f"{cam[0]}/{ts.strftime('%Y%m%d')}/{n:05d}.jpg", "N", "", CLS])
        n += 1
    rows.sort(key=lambda r: r[7])
    for i, r in enumerate(rows, 1):
        r[0] = f"ANPR-{i:05d}"
    return to_csv(header, rows)


# ---------------------------------------------------------------------------
# BANK STATEMENTS
# ---------------------------------------------------------------------------
ACCOUNT_META = {
    "ACC-001": {"number": "33901122", "holder": "Suresh Balan", "person": "PER-006",
                "branch": "Guindy Industrial Estate Branch", "ifsc": "BCBK0003390",
                "type": "SB", "opening": 184500.00},
    "ACC-002": {"number": "44120987", "holder": "Divya Nair", "person": "PER-008",
                "branch": "Chennai Port Branch", "ifsc": "BCBK0004412",
                "type": "CA", "opening": 96200.00},
    "ACC-003": {"number": "77650034", "holder": "Coastal Logistics Pvt Ltd",
                "person": "ORG-002", "branch": "R S Puram Branch, Coimbatore",
                "ifsc": "BCBK0007765", "type": "CA", "opening": 512000.00},
}
ACC_BY_ID = {k: v["number"] for k, v in ACCOUNT_META.items()}


def bank_statement_csv(account_id: str) -> str:
    meta = ACCOUNT_META[account_id]
    txns = [t for t in S.transactions() if t["account_id"] == account_id]
    txns.sort(key=lambda t: t["timestamp"])
    header = ["SR_NO", "TXN_ID", "VALUE_DATE", "POSTING_DATE", "POSTING_TIME",
              "NARRATION", "REF_NO", "CHANNEL", "DEBIT_INR", "CREDIT_INR",
              "BALANCE_INR", "COUNTERPARTY_ACCOUNT", "COUNTERPARTY_NAME",
              "COUNTERPARTY_IFSC", "LINKED_EVIDENCE", "CLASSIFICATION"]
    rows: list[list] = []
    bal = meta["opening"]
    rng = random.Random(int(account_id[-1]) * 31)
    for i, t in enumerate(txns, 1):
        dt = datetime.strptime(t["timestamp"], "%Y-%m-%dT%H:%M:%SZ")
        cp_id = t["counterparty"]
        cp = ACCOUNT_META[cp_id]
        # ACC-001 pays out, counterparties receive
        debit = t["amount"] if account_id == "ACC-001" else 0.0
        credit = 0.0 if account_id == "ACC-001" else t["amount"]
        bal = round(bal - debit + credit, 2)
        channel = rng.choice(["UPI", "IMPS", "NEFT", "UPI"])
        ref = f"{channel}{dt.strftime('%y%m%d')}{rng.randint(100000, 999999)}"
        narration = (f"{channel}/{'DR' if debit else 'CR'}/{ref}/"
                     f"{cp['holder'].upper().replace(' ', '')}/{cp['ifsc']}")
        rows.append([i, t["txn_id"], dt.strftime("%d/%m/%Y"), dt.strftime("%d/%m/%Y"),
                     dt.strftime("%H:%M:%S"), narration, ref, channel,
                     f"{debit:.2f}" if debit else "", f"{credit:.2f}" if credit else "",
                     f"{bal:.2f}", cp["number"], cp["holder"], cp["ifsc"],
                     t["evidence_id"], CLS])
    return to_csv(header, rows)


def bank_statement_header_text(account_id: str) -> str:
    from .ds_documents import banner, kv, RULE, W
    meta = ACCOUNT_META[account_id]
    txns = [t for t in S.transactions() if t["account_id"] == account_id]
    total = sum(t["amount"] for t in txns)
    return "\n".join([
        banner("Bank Statement"),
        "BHARAT COASTAL BANK (SYNTHETIC)".center(W),
        "CERTIFIED STATEMENT OF ACCOUNT".center(W),
        "",
        RULE,
        kv(" Account number", f"A/C {meta['number']}"),
        kv(" Account holder", meta["holder"]),
        kv(" Account type", meta["type"]),
        kv(" Branch", meta["branch"]),
        kv(" IFSC", meta["ifsc"]),
        kv(" Statement period", "18/08/2025 to 25/08/2025"),
        kv(" Opening balance (INR)", f"{meta['opening']:,.2f}"),
        kv(" Number of transactions", str(len(txns))),
        kv(" Total value (INR)", f"{total:,.2f}"),
        kv(" Produced against", "CASE-305 / BANK / 01 dated 22/08/2025"),
        kv(" System evidence reference", "EV-3070"),
        RULE,
        "",
        " REMARKS OF THE PRODUCING OFFICER",
        "",
        " The statement is produced in machine-readable form. Amounts, references and",
        " counterparty particulars are fictional. The transaction pattern on 22/08/2025",
        " between 14:00 and 15:00 hrs is materially denser than the account baseline of",
        " approximately two transactions per day; the pattern is stated as a fact of the",
        " record and carries NO implication of wrongdoing.",
        "",
        " A burst of activity is a statistical observation, not an offence, and not",
        " evidence of any offence. It is furnished so that the analytical platform can",
        " flag it for human review.",
        RULE,
    ])


# ---------------------------------------------------------------------------
# MASTER REGISTERS (the structured datasets the platform loads)
# ---------------------------------------------------------------------------
def cases_csv() -> str:
    header = ["CASE_ID", "TITLE", "CASE_TYPE", "PRIORITY", "STATUS", "CREATED_DATE",
              "LEAD_OFFICER_ID", "JURISDICTION", "DESCRIPTION", "CLASSIFICATION"]
    return to_csv(header, [[c["case_id"], c["title"], c["case_type"], c["priority"],
                            c["status"], c["created_date"], c["investigator"],
                            "Synthetic Jurisdiction", c["description"], CLS]
                           for c in S.CASES])


def users_csv() -> str:
    header = ["USER_ID", "DISPLAY_NAME", "ROLE", "BADGE", "UNIT", "CASE_ACCESS",
              "DEMO_PASSWORD", "ACTIVE", "CLASSIFICATION"]
    return to_csv(header, [[u["user_id"], u["display_name"], u["role"], u["badge"],
                            u["unit"], " | ".join(u["case_access"]), u["password"],
                            "TRUE", CLS] for u in S.USERS])


def evidence_register_csv() -> str:
    header = ["EVIDENCE_ID", "CASE_ID", "EVIDENCE_TYPE", "SOURCE", "TIMESTAMP",
              "UPLOADED_BY", "VERIFICATION_STATUS", "PROCESSING_STATUS", "OBJECT_FORMAT",
              "TEXT_ORIGIN", "OCR_APPLIED", "SOURCE_DOCUMENT_FILE", "CLASSIFICATION"]
    from .ds_index import SOURCE_FILE_FOR
    rows = []
    for e in S.EVIDENCE_DOCS:
        ext = e.get("object_ext", "txt")
        origin = "PREPROCESSED_SYNTHETIC_TEXT" if e["evidence_type"] in {"IMAGE", "PDF"} else "NATIVE_TEXT"
        rows.append([e["evidence_id"], e["case_id"], e["evidence_type"], e["source"],
                     e["timestamp"], e["uploaded_by"], e.get("verification_status", "UNVERIFIED"),
                     e.get("processing_status", "UPLOADED"), ext.upper(), origin, "FALSE",
                     SOURCE_FILE_FOR.get(e["evidence_id"], ""), CLS])
    return to_csv(header, rows)


def entities_master_csv() -> str:
    header = ["ENTITY_ID", "ENTITY_TYPE", "LABEL", "NORMALIZED", "CASES",
              "ATTRIBUTES", "LATITUDE", "LONGITUDE", "CLASSIFICATION"]
    rows: list[list] = []

    def attr_str(d: dict) -> str:
        return "; ".join(f"{k}={v if not isinstance(v, list) else ','.join(map(str, v))}"
                         for k, v in d.items())

    for pid, name, cases, attrs in S.PERSONS:
        rows.append([pid, "PERSON", name, name.upper(), " | ".join(cases),
                     attr_str(attrs), "", "", CLS])
    for vid, plate, cases in S.VEHICLES:
        rows.append([vid, "VEHICLE", plate, plate.upper(), " | ".join(cases),
                     f"registration={plate}", "", "", CLS])
    for phid, num, cases in S.PHONES:
        rows.append([phid, "PHONE", num, num, " | ".join(cases),
                     "msisdn stored field-encrypted in the platform", "", "", CLS])
    for aid, num, cases in S.ACCOUNTS:
        rows.append([aid, "ACCOUNT", f"A/C {num}", f"A/C {num}", " | ".join(cases),
                     "account number stored field-encrypted in the platform", "", "", CLS])
    for lid, name, lat, lon, cases in S.LOCATIONS:
        rows.append([lid, "LOCATION", name, name.upper(), " | ".join(cases),
                     f"city={'Coimbatore' if lid == 'LOC-006' else 'Chennai'}", lat, lon, CLS])
    for oid, name, cases in S.ORGS:
        rows.append([oid, "ORGANIZATION", name, name.upper(), " | ".join(cases), "", "", "", CLS])
    for did, label, cases in S.DEVICES:
        rows.append([did, "DEVICE", label, label.upper(), " | ".join(cases), "", "", "", CLS])
    return to_csv(header, rows)


def persons_csv() -> str:
    header = ["PERSON_ID", "NAME", "NORMALIZED_NAME", "CASES", "ROLE_IN_CASE",
              "VEHICLES", "PHONES", "ACCOUNTS", "LOCATIONS", "ACTIVITY_DATES",
              "IDENTITY_STATUS", "CLASSIFICATION"]
    rows = []
    for pid, name, cases, a in S.PERSONS:
        rows.append([pid, name, name.upper(), " | ".join(cases), a.get("role_in_case", ""),
                     " | ".join(a.get("vehicles", [])), " | ".join(a.get("phones", [])),
                     " | ".join(a.get("accounts", [])), " | ".join(a.get("locations", [])),
                     " | ".join(a.get("activity_dates", [])),
                     "HUMAN_VERIFIED" if pid == "PER-001" else "UNVERIFIED", CLS])
    return to_csv(header, rows)


def vehicles_csv() -> str:
    header = ["VEHICLE_ID", "REGISTRATION", "CASES", "ASSOCIATED_PERSONS",
              "APPEARS_IN_CASE_COUNT", "CLASSIFICATION"]
    rows = []
    for vid, plate, cases in S.VEHICLES:
        people = [f"{p[0]}:{p[1]}" for p in S.person_of_vehicle(plate)]
        rows.append([vid, plate, " | ".join(cases), " | ".join(people), len(cases), CLS])
    return to_csv(header, rows)


def locations_csv() -> str:
    header = ["LOCATION_ID", "NAME", "CITY", "LATITUDE", "LONGITUDE", "CASES",
              "CELL_SITES", "ANPR_CAMERA", "CLASSIFICATION"]
    cams = {"LOC-001": "CAM-CHN-CENTRAL-04", "LOC-002": "CAM-TNGR-USMAN-11",
            "LOC-003": "CAM-GNDY-IE-07", "LOC-005": "CAM-PORT-RAJAJI-02",
            "LOC-006": "CAM-CBE-DBROAD-05"}
    rows = []
    for lid, name, lat, lon, cases in S.LOCATIONS:
        cgis = " | ".join(c[0] for c in CELL_SITES if c[7] == lid)
        rows.append([lid, name, "Coimbatore" if lid == "LOC-006" else "Chennai", lat, lon,
                     " | ".join(cases), cgis, cams.get(lid, ""), CLS])
    return to_csv(header, rows)


def phones_csv() -> str:
    header = ["PHONE_ID", "MSISDN", "CASES", "SUBSCRIBER_PERSON", "IMEI_OBSERVED",
              "CDR_AVAILABLE", "CLASSIFICATION"]
    rows = []
    for phid, num, cases in S.PHONES:
        p = S.person_of_phone(num)
        meta = SUBSCRIBERS.get(num)
        rows.append([phid, num, " | ".join(cases), f"{p[0]}:{p[1]}" if p else "UNKNOWN",
                     meta["imei"] if meta else "NOT COLLECTED",
                     "YES (10-14 Aug 2025 only)" if meta else "NO - information gap", CLS])
    return to_csv(header, rows)


def accounts_csv() -> str:
    header = ["ACCOUNT_ID", "ACCOUNT_NUMBER", "HOLDER", "HOLDER_ENTITY", "BANK", "BRANCH",
              "IFSC", "ACCOUNT_TYPE", "CASES", "TXN_COUNT_IN_DATASET", "CLASSIFICATION"]
    txns = S.transactions()
    rows = []
    for aid, num, cases in S.ACCOUNTS:
        m = ACCOUNT_META[aid]
        n = len([t for t in txns if t["account_id"] == aid])
        rows.append([aid, num, m["holder"], m["person"], "Bharat Coastal Bank (synthetic)",
                     m["branch"], m["ifsc"], m["type"], " | ".join(cases), n, CLS])
    return to_csv(header, rows)


def orgs_devices_csv() -> str:
    header = ["ENTITY_ID", "ENTITY_TYPE", "LABEL", "CASES", "CLASSIFICATION"]
    rows = [[o[0], "ORGANIZATION", o[1], " | ".join(o[2]), CLS] for o in S.ORGS]
    rows += [[d[0], "DEVICE", d[1], " | ".join(d[2]), CLS] for d in S.DEVICES]
    return to_csv(header, rows)


def relationships_csv() -> str:
    header = ["RELATIONSHIP_ID", "SOURCE_ENTITY", "SOURCE_LABEL", "RELATIONSHIP_TYPE",
              "TARGET_ENTITY", "TARGET_LABEL", "TIMESTAMP", "EVIDENCE_ID", "CASE_ID",
              "SUPPORT_LEVEL", "VERIFICATION_STATUS", "CLASSIFICATION"]
    label = {}
    for pid, name, *_ in S.PERSONS:
        label[pid] = name
    for vid, plate, _ in S.VEHICLES:
        label[vid] = plate
    for phid, num, _ in S.PHONES:
        label[phid] = num
    for aid, num, _ in S.ACCOUNTS:
        label[aid] = f"A/C {num}"
    for lid, name, *_ in S.LOCATIONS:
        label[lid] = name
    for oid, name, _ in S.ORGS:
        label[oid] = name
    for did, lab, _ in S.DEVICES:
        label[did] = lab
    rows = []
    for rid, src, tgt, rtype, ts, evid, case_id, support, verification in S.RELATIONSHIPS:
        rows.append([rid, src, label.get(src, src), rtype, tgt, label.get(tgt, tgt), ts,
                     evid, case_id, support, verification, CLS])
    return to_csv(header, rows)


def events_csv() -> str:
    header = ["EVENT_ID", "CASE_ID", "TIMESTAMP", "EVENT_TYPE", "TITLE", "LOCATION_ID",
              "LOCATION_NAME", "ENTITY_IDS", "EVIDENCE_ID", "CLASSIFICATION"]
    rows = []
    for eid, case_id, title, ts, loc, ents, evid, etype in S.EVENTS:
        rows.append([eid, case_id, ts, etype, title, loc or "",
                     S.LOC_BY_ID[loc][1] if loc else "", " | ".join(ents), evid, CLS])
    return to_csv(header, rows)


def transactions_csv() -> str:
    header = ["TXN_ID", "ACCOUNT_ID", "ACCOUNT_NUMBER", "TIMESTAMP", "AMOUNT_INR",
              "COUNTERPARTY_ID", "COUNTERPARTY_ACCOUNT", "CASE_ID", "EVIDENCE_ID",
              "CLASSIFICATION"]
    rows = []
    for t in S.transactions():
        rows.append([t["txn_id"], t["account_id"], ACC_BY_ID[t["account_id"]],
                     t["timestamp"], f"{t['amount']:.2f}", t["counterparty"],
                     ACC_BY_ID[t["counterparty"]], t["case_id"], t["evidence_id"], CLS])
    return to_csv(header, rows)


def contradictions_csv() -> str:
    header = ["CONTRADICTION_ID", "CASE_ID", "ENTITY_IDS", "EVIDENCE_IDS", "STATEMENT",
              "IMPACT", "STATUS", "CLASSIFICATION"]
    rows = [[c["contradiction_id"], c["case_id"], " | ".join(c["entity_ids"]),
             " | ".join(c["evidence_ids"]), c["statement"], c["impact"], c["status"], CLS]
            for c in S.CONTRADICTIONS]
    return to_csv(header, rows)


def cross_case_overlap_csv() -> str:
    """Shared identifiers across cases - the raw material for cross-case correlation."""
    header = ["OVERLAP_ID", "SHARED_IDENTIFIER", "IDENTIFIER_TYPE", "ENTITY_ID",
              "CASE_A", "CASE_B", "EVIDENCE_A", "EVIDENCE_B", "STRENGTH",
              "BASIS", "CLASSIFICATION"]
    rows = [
        ["XC-001", "TN01AB1234", "VEHICLE_REGISTRATION", "VEH-001", "CASE-101", "CASE-202",
         "EV-1024", "EV-2041", "HIGH",
         "Exact registration match documented in both files", CLS],
        ["XC-002", "TN01AB1234", "VEHICLE_REGISTRATION", "VEH-001", "CASE-202", "CASE-305",
         "EV-2041", "EV-3071", "HIGH",
         "Exact registration match documented in both files", CLS],
        ["XC-003", "TN01AB1234", "VEHICLE_REGISTRATION", "VEH-001", "CASE-101", "CASE-305",
         "EV-1024", "EV-3071", "HIGH",
         "Exact registration match documented in both files", CLS],
        ["XC-004", "Arun Selvam", "PERSON_NAME", "PER-004", "CASE-101", "CASE-202",
         "EV-1025", "EV-2041", "MEDIUM",
         "Identical full name recorded in both files; identity not documentarily confirmed", CLS],
        ["XC-005", "Arun Selvam", "PERSON_NAME", "PER-004", "CASE-202", "CASE-305",
         "EV-2041", "EV-3071", "MEDIUM",
         "Identical full name recorded in both files; identity not documentarily confirmed", CLS],
        ["XC-006", "+919840012345", "MSISDN", "PHN-001", "CASE-101", "CASE-202",
         "EV-1024", "EV-2041", "MEDIUM",
         "Same number recorded against Ravi Kumar and R. Kumar; subscriber identity unverified", CLS],
        ["XC-007", "Ravi Kumar / R. Kumar / Ravi K.", "PERSON_NAME_VARIANT",
         "PER-001|PER-002|PER-003", "CASE-101", "CASE-202|CASE-305", "EV-1024",
         "EV-2041|EV-3071", "CANDIDATE - NOT MERGED",
         "Name variants plus shared vehicle and phone. Contradiction CON-001 is unresolved, "
         "so the identity remains a candidate for human decision and is NOT auto-merged", CLS],
        ["XC-008", "Coastal Logistics Pvt Ltd", "ORGANISATION", "ORG-002", "CASE-305",
         "CASE-407", "EV-3071", "EV-4090", "LOW",
         "Same organisation name appears in both files; no shared transaction or document", CLS],
    ]
    return to_csv(header, rows)


def image_metadata_csv() -> str:
    header = ["IMAGE_FILE", "EVIDENCE_ID", "CASE_ID", "CAMERA_ID", "CAPTURE_TIMESTAMP",
              "LOCATION_ID", "LATITUDE", "LONGITUDE", "WIDTH_PX", "HEIGHT_PX", "FORMAT",
              "COLOUR_SPACE", "OCR_APPLIED", "OCR_ENGINE", "EXTRACTED_TEXT",
              "IMAGE_ORIGIN", "INTEGRITY_NOTE", "CLASSIFICATION"]
    rows = [
        ["EV-2042_CCTV-still_Chennai-Central_2025-08-18T1007Z.png", "EV-2042", "CASE-202",
         "CAM-CHN-CENTRAL-04", "2025-08-18T10:07:00Z", "LOC-001", 13.0827, 80.2707,
         1280, 720, "PNG", "sRGB", "FALSE", "NONE - no OCR engine installed",
         "(none - see note)", "AI-GENERATED SYNTHETIC IMAGE, NOT A PHOTOGRAPH",
         "This is the item deliberately altered after registration so that the platform's "
         "SHA-256 integrity check reports INTEGRITY MISMATCH", CLS],
        ["EV-2042b_ANPR-plate-crop_Chennai-Central_2025-08-18T1007Z.png", "EV-2042", "CASE-202",
         "CAM-CHN-CENTRAL-04", "2025-08-18T10:07:00Z", "LOC-001", 13.0827, 80.2707,
         640, 240, "PNG", "sRGB", "FALSE", "NONE - no OCR engine installed",
         "(none - plate text carried in the ANPR log, not read from this crop)",
         "AI-GENERATED SYNTHETIC IMAGE, NOT A PHOTOGRAPH",
         "Supporting crop; not separately registered in the platform", CLS],
        ["EV-1026_surveillance-still_Guindy_2025-08-12T1230Z.png", "EV-1026", "CASE-101",
         "DC-114 (departmental camera)", "2025-08-12T12:30:00Z", "LOC-003", 13.0067, 80.2206,
         1280, 720, "PNG", "sRGB", "FALSE", "NONE - no OCR engine installed",
         "(none - see note)", "AI-GENERATED SYNTHETIC IMAGE, NOT A PHOTOGRAPH",
         "Illustrative still accompanying the surveillance log", CLS],
    ]
    return to_csv(header, rows)


def expected_outcomes_csv() -> str:
    header = ["STAGE", "WHAT_THE_DATASET_CONTAINS", "WHAT_THE_PLATFORM_SHOULD_OUTPUT",
              "WHY_IT_MATTERS", "CLASSIFICATION"]
    rows = [
        ["Entity extraction", "10 evidence documents in 7 formats",
         "37 entities: 15 PERSON, 5 VEHICLE, 6 LOCATION, 4 PHONE, 3 ACCOUNT, 2 ORGANISATION, "
         "2 DEVICE (plus 5 CASE nodes in the graph)",
         "Extraction is traceable to a document, never invented", CLS],
        ["Entity resolution", "Name variants Ravi Kumar / R. Kumar / Ravi K. sharing TN01AB1234",
         "Candidate match at 95.0 similarity, auto_merged = FALSE",
         "The platform never auto-merges an identity", CLS],
        ["Cross-case correlation", "TN01AB1234 documented in CASE-101, CASE-202, CASE-305",
         "3 cross-case associations, strongest XC-101-202 at 97.0",
         "The link rests on a shared documented identifier, not on a name", CLS],
        ["Knowledge graph", "28 evidence-backed relationships",
         "A graph of 37 entities + 5 case nodes; every edge cites the evidence id it "
         "came from, and the investigator sees only the cases they are authorised for",
         "No edge exists without a source document", CLS],
        ["Network analysis", "Graph above",
         "Degree and betweenness centrality, 7 communities, shortest path "
         "PER-001 -> LOC-001 -> PER-004",
         "Central is described as structurally important, never as a leader or a criminal", CLS],
        ["Timeline", "17 events, 10-27 Aug 2025",
         "Baseline 1.7 events/day with a spike on 12 Aug; temporal-spatial convergence at "
         "Chennai Central on 18 Aug",
         "Co-location is reported as co-location, not as a meeting", CLS],
        ["Anomaly detection", "63 transactions: baseline ~2/day plus a 50-transaction burst "
         "on 22 Aug 14:00-15:00",
         "1 anomaly flagged on ACC-001 at 2025-08-22 14:00 (Isolation Forest)",
         "An anomaly is a statistical outlier, never an accusation", CLS],
        ["Corroboration", "EV-2041 (Chennai Central) vs EV-2043 (Madurai), same 5-minute window",
         "corroborated 0, contradictory 3, partial 0, insufficient 2; CON-001 surfaced, "
         "not suppressed",
         "Contradictions are preserved and shown to the investigator", CLS],
        ["Information gaps", "No CDR for 15-19 Aug; no RTO ownership record; no identity document",
         "5 gaps ranked by information value; IG-001 HIGH",
         "The platform states what it does not know", CLS],
        ["Next-best action", "The gaps above",
         "Top action: Cross-reference authorised vehicle records (information value 0.92)",
         "Actions are lawful record checks, never surveillance or arrest advice", CLS],
        ["Human verification", "Unverified relationships and candidate identities",
         "Verify / reject with rationale; rejection preserves the original finding",
         "The human decides; the machine proposes", CLS],
        ["Integrity", "10 registered objects, 1 altered after registration (EV-2042)",
         "9 VERIFIED, 1 INTEGRITY_MISMATCH; ledger chain intact",
         "Tampering is detectable, on demand", CLS],
        ["Insufficient evidence", "CASE-512: one anonymous tip with no particulars",
         "INSUFFICIENT EVIDENCE plus the named missing elements; no network is drawn",
         "The platform refuses to guess", CLS],
    ]
    return to_csv(header, rows)
