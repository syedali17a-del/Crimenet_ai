"""Folder layout + evidence-to-source-file mapping for the dataset pack."""
from __future__ import annotations

FOLDERS = {
    "fir": "01_FIR",
    "police": "02_POLICE_REPORT",
    "cdr": "03_CDR_CALL_DETAIL_RECORDS",
    "finance": "04_FINANCIAL_RECORDS",
    "surveillance": "05_SURVEILLANCE_REPORTS",
    "intel": "06_INTELLIGENCE_REPORTS",
    "image": "07_IMAGE_EVIDENCE",
    "pdf": "08_PDF_CASE_BUNDLES",
    "csv": "09_CSV_STRUCTURED_DATASETS",
    "custody": "10_CHAIN_OF_CUSTODY_AND_CERTIFICATES",
}

# evidence_id -> the primary source file in this pack that backs it
SOURCE_FILE_FOR = {
    "EV-1024": "01_FIR/FIR_0412-2025_CASE-101_Chennai-Central.txt",
    "EV-1025": "03_CDR_CALL_DETAIL_RECORDS/CDR_9840012345_2025-08-10_to_2025-08-14.csv",
    "EV-1026": "05_SURVEILLANCE_REPORTS/SURVEILLANCE-REPORT_OP-KAVAL-07_CASE-101_Guindy.txt",
    "EV-2041": "02_POLICE_REPORT/POLICE-REPORT_Cr-0518-2025_CASE-202_Chennai-Central.txt",
    "EV-2042": "07_IMAGE_EVIDENCE/EV-2042_CCTV-still_Chennai-Central_2025-08-18T1007Z.png",
    "EV-2043": "06_INTELLIGENCE_REPORTS/INTELLIGENCE-REPORT_INT-2025-0442_CASE-202.txt",
    "EV-3070": "04_FINANCIAL_RECORDS/BANK-STATEMENT_AC-33901122_Suresh-Balan_Aug2025.csv",
    "EV-3071": "06_INTELLIGENCE_REPORTS/INTELLIGENCE-REPORT_INT-2025-0517_CASE-305.txt",
    "EV-4090": "02_POLICE_REPORT/POLICE-REPORT_Enq-0134-2025_CASE-407_Coimbatore.txt",
    "EV-5120": "01_FIR/FIR_0731-2025_CASE-512_Anonymous-Tip.txt",
}

TYPE_LABEL = {
    "fir": "FIR / First Information Report",
    "police": "Police report",
    "cdr": "Call Detail Record (CDR)",
    "finance": "Financial record",
    "surveillance": "Surveillance report",
    "intel": "Intelligence report",
    "image": "Image evidence",
    "pdf": "PDF case bundle",
    "csv": "Structured CSV dataset",
    "custody": "Chain of custody / legal certificate",
}
