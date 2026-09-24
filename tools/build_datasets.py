"""Build the CrimeNet AI synthetic dataset pack.

    python3 -m tools.build_datasets

Produces /home/user/datasets/ - one folder per dataset type, every file in the
format the real artefact uses, every fact identical to the application seed data,
plus a SHA-256 manifest and an index for presentation.
"""
from __future__ import annotations

import hashlib
import shutil
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as pdfcanvas

from . import ds_documents as D
from . import ds_source as S
from . import ds_tables as T
from .ds_index import FOLDERS, SOURCE_FILE_FOR, TYPE_LABEL

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "datasets"
CLS = S.CLASSIFICATION
FONT_DIR = Path("/usr/share/fonts/truetype/dejavu")


# ---------------------------------------------------------------------------
class Pack:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def write(self, folder: str, name: str, content: str | bytes, *,
              dtype: str, evidence: str = "", case: str = "", desc: str = "") -> Path:
        d = OUT / FOLDERS[folder]
        d.mkdir(parents=True, exist_ok=True)
        p = d / name
        data = content.encode("utf-8") if isinstance(content, str) else content
        p.write_bytes(data)
        self.record(p, dtype, evidence, case, desc)
        return p

    def record(self, p: Path, dtype: str, evidence: str = "", case: str = "",
               desc: str = "") -> None:
        data = p.read_bytes()
        self.rows.append({
            "path": str(p.relative_to(OUT)).replace("\\", "/"),
            "folder": p.parent.name,
            "type": TYPE_LABEL.get(dtype, dtype),
            "format": p.suffix.lstrip(".").upper(),
            "evidence": evidence, "case": case,
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "desc": desc,
        })


pack = Pack()


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------
def render_pdf(lines: list[str], out: Path, title: str, subtitle: str = "") -> None:
    c = pdfcanvas.Canvas(str(out), pagesize=A4)
    W, H = A4
    left, top = 18 * mm, H - 20 * mm
    size, lead = 8.6, 10.6
    per_page = int((top - 22 * mm) / lead)
    pages = [lines[i:i + per_page] for i in range(0, len(lines), per_page)] or [[]]

    for pno, chunk in enumerate(pages, 1):
        # watermark
        c.saveState()
        c.setFont("Helvetica-Bold", 44)
        c.setFillGray(0.90)
        c.translate(W / 2, H / 2)
        c.rotate(38)
        c.drawCentredString(0, 30, "SYNTHETIC")
        c.drawCentredString(0, -30, "DEMONSTRATION DATA")
        c.restoreState()

        # header rule
        c.setStrokeGray(0.6)
        c.setLineWidth(0.5)
        c.line(left, top + 6 * mm, W - left, top + 6 * mm)
        c.setFont("Helvetica-Bold", 7.5)
        c.setFillGray(0.25)
        c.drawString(left, top + 7.6 * mm, title[:96])
        c.drawRightString(W - left, top + 7.6 * mm, "CrimeNet AI - synthetic dataset pack")

        c.setFillGray(0)
        c.setFont("Courier", size)
        y = top
        for ln in chunk:
            c.drawString(left, y, ln.replace("\t", "    ")[:95])
            y -= lead

        c.setFont("Helvetica", 6.8)
        c.setFillGray(0.35)
        c.line(left, 15 * mm, W - left, 15 * mm)
        c.drawString(left, 11.5 * mm, f"{CLS} - fictional record, not evidence")
        c.drawRightString(W - left, 11.5 * mm, f"Page {pno} of {len(pages)}")
        if subtitle:
            c.drawCentredString(W / 2, 11.5 * mm, subtitle[:70])
        c.showPage()
    c.save()


def text_to_pdf(folder: str, txt_name: str, text: str, title: str, *,
                dtype: str, evidence: str = "", case: str = "", desc: str = "") -> None:
    out = OUT / FOLDERS[folder] / (Path(txt_name).stem + ".pdf")
    render_pdf(text.splitlines(), out, title, subtitle=evidence)
    pack.record(out, dtype, evidence, case, desc)


# ---------------------------------------------------------------------------
# IMAGES
# ---------------------------------------------------------------------------
def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_DIR / name), size)


def osd_overlay(src: Path, out: Path, camera: str, ts: str, location: str,
                extra: str = "") -> None:
    img = Image.open(src).convert("RGB").resize((1280, 720), Image.LANCZOS)
    # CCTV degradation
    img = img.filter(ImageFilter.GaussianBlur(0.4))
    d = ImageDraw.Draw(img)
    mono = _font("DejaVuSansMono-Bold.ttf", 22)
    small = _font("DejaVuSansMono.ttf", 17)
    tiny = _font("DejaVuSansMono-Bold.ttf", 19)

    def shadow(xy, text, font, fill=(255, 255, 255)):
        x, y = xy
        d.text((x + 1, y + 1), text, font=font, fill=(0, 0, 0))
        d.text((x, y), text, font=font, fill=fill)

    shadow((18, 14), camera, mono)
    shadow((18, 44), location, small, (220, 220, 220))
    w = d.textlength(ts, font=mono)
    shadow((1280 - w - 18, 14), ts, mono)
    shadow((1280 - d.textlength("REC", font=mono) - 18, 44), "REC", mono, (255, 90, 90))
    d.ellipse([1280 - d.textlength("REC", font=mono) - 40, 48, 1280 - d.textlength("REC", font=mono) - 26, 62],
              fill=(220, 40, 40))

    # bottom synthetic banner
    d.rectangle([0, 662, 1280, 720], fill=(12, 22, 40))
    shadow((18, 670), "SYNTHETIC DEMONSTRATION DATA - AI-GENERATED IMAGE, NOT A PHOTOGRAPH",
           tiny, (255, 214, 102))
    shadow((18, 694), extra or "No OCR performed. No facial recognition performed. Not evidence.",
           small, (200, 210, 230))
    img.save(out)


def plate_crop(src: Path, out: Path, plate: str) -> None:
    """ANPR review crop: the vehicle front at 4x, a region-of-interest box over the
    number plate area, and an enlarged synthetic read-out inset - the layout an ANPR
    review console uses. The plate text is drawn, never read: no OCR is performed."""
    img = Image.open(src).convert("RGB").resize((1280, 720), Image.LANCZOS)
    box = (600, 425, 880, 565)          # front of the white car in the 1280x720 frame
    scale = 4
    cw, ch = (box[2] - box[0]) * scale, (box[3] - box[1]) * scale
    crop = img.crop(box).resize((cw, ch), Image.LANCZOS).filter(ImageFilter.GaussianBlur(1.1))
    d = ImageDraw.Draw(crop)

    amber = (255, 196, 61)
    navy = (12, 22, 40)

    # --- region of interest over the plate area of the bumper -----------------
    roi = (566, 150, 700, 232)
    d.rectangle(roi, outline=amber, width=3)
    for cx, cy in [(roi[0], roi[1]), (roi[2], roi[1]), (roi[0], roi[3]), (roi[2], roi[3])]:
        d.line([cx - 9, cy, cx + 9, cy], fill=amber, width=3)
        d.line([cx, cy - 9, cx, cy + 9], fill=amber, width=3)
    d.text((roi[0], roi[1] - 26), "ROI 01", font=_font("DejaVuSansMono-Bold.ttf", 19),
           fill=amber)

    # --- enlarged read-out inset ---------------------------------------------
    ix0, iy0, ix1, iy1 = 700, 296, 1094, 470
    d.line([roi[2], roi[3], ix0, iy0], fill=amber, width=2)
    d.line([roi[2], roi[1], ix1, iy0], fill=amber, width=2)
    d.rectangle([ix0, iy0, ix1, iy1], fill=navy, outline=amber, width=3)

    pw, ph = 300, 84
    px, py = ix0 + (ix1 - ix0 - pw) // 2, iy0 + 20
    d.rectangle([px - 3, py - 3, px + pw + 3, py + ph + 3], fill=(28, 28, 28))
    d.rectangle([px, py, px + pw, py + ph], fill=(238, 238, 232))
    f = _font("DejaVuSansMono-Bold.ttf", 42)
    txt = f"{plate[:4]} {plate[4:]}"
    tw = d.textlength(txt, font=f)
    d.text((px + (pw - tw) / 2, py + 18), txt, font=f, fill=(16, 16, 16))

    cap = _font("DejaVuSansMono-Bold.ttf", 18)
    capl = _font("DejaVuSansMono.ttf", 17)
    d.text((ix0 + 18, iy0 + 116), "PLATE READ (SYNTHETIC)", font=cap, fill=amber)
    d.text((ix0 + 18, iy0 + 140), "CONF 0.96   CLASS LMV   HOTLIST Y", font=capl,
           fill=(214, 224, 240))

    # --- OSD bars -------------------------------------------------------------
    small = _font("DejaVuSansMono-Bold.ttf", 18)
    tiny = _font("DejaVuSansMono.ttf", 16)
    d.rectangle([0, 0, cw, 34], fill=navy)
    d.text((12, 8), "CAM-CHN-CENTRAL-04   ANPR PLATE CROP   2025-08-18 10:07:00 IST",
           font=small, fill=(255, 255, 255))
    d.rectangle([0, ch - 52, cw, ch], fill=navy)
    d.text((12, ch - 46), "SYNTHETIC DEMONSTRATION DATA - COMPOSITED CROP, NOT A PHOTOGRAPH",
           font=small, fill=amber)
    d.text((12, ch - 24),
           "Plate text drawn synthetically. No OCR or plate recognition was performed.",
           font=tiny, fill=(200, 210, 230))
    crop.save(out)


# ---------------------------------------------------------------------------
def build() -> None:
    # AI source frames live OUTSIDE the pack so the presented folder stays clean
    raw = ROOT / "tools" / "_image_sources"
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)

    # ---- 01 FIR ----------------------------------------------------------
    for fn, body, ev, case, desc in [
        (*D.fir_case_101(), "EV-1024", "CASE-101",
         "First Information Report, Form IF1 layout, vehicle theft, Chennai Central"),
        (*D.fir_case_512(), "EV-5120", "CASE-512",
         "Anonymous tip register entry with no particulars - drives the INSUFFICIENT "
         "EVIDENCE pathway"),
    ]:
        pack.write("fir", fn, body, dtype="fir", evidence=ev, case=case, desc=desc)
        text_to_pdf("fir", fn, body, f"{fn}  ({ev} / {case})", dtype="fir",
                    evidence=ev, case=case, desc=desc + " (PDF rendering)")

    # ---- 02 POLICE REPORTS ----------------------------------------------
    for fn, body, ev, case, desc in [
        (*D.police_report_case_202(), "EV-2041", "CASE-202",
         "Case diary extract recording the 18 Aug Chennai Central observations"),
        (*D.police_report_case_407(), "EV-4090", "CASE-407",
         "Preliminary enquiry note, Coimbatore document irregularity"),
    ]:
        pack.write("police", fn, body, dtype="police", evidence=ev, case=case, desc=desc)
        text_to_pdf("police", fn, body, f"{fn}  ({ev} / {case})", dtype="police",
                    evidence=ev, case=case, desc=desc + " (PDF rendering)")

    # ---- 03 CDR ----------------------------------------------------------
    fn, body = D.cdr_requisition()
    pack.write("cdr", fn, body, dtype="cdr", evidence="EV-1025", case="CASE-101",
               desc="Requisition to the telecom nodal officer under s.94 BNSS")
    text_to_pdf("cdr", fn, body, fn, dtype="cdr", evidence="EV-1025", case="CASE-101",
                desc="Requisition letter (PDF rendering)")

    pack.write("cdr", "CDR-COVERING-LETTER_STL-2025-2214.txt", T.cdr_covering_letter(),
               dtype="cdr", evidence="EV-1025", case="CASE-101",
               desc="Operator covering letter; states the 15-19 Aug records were NOT "
                    "furnished - this is the deliberate information gap")
    text_to_pdf("cdr", "CDR-COVERING-LETTER_STL-2025-2214.txt", T.cdr_covering_letter(),
                "CDR covering letter - Synthetic Telecom Ltd", dtype="cdr",
                evidence="EV-1025", case="CASE-101", desc="Covering letter (PDF rendering)")

    pack.write("cdr", "CDR_9840012345_2025-08-10_to_2025-08-14.csv",
               T.cdr_csv("+919840012345"), dtype="cdr", evidence="EV-1025", case="CASE-101",
               desc="Call detail records for +919840012345 (PHN-001), LEA dump layout")
    pack.write("cdr", "CDR_9840099887_2025-08-10_to_2025-08-14.csv",
               T.cdr_csv("+919840099887"), dtype="cdr", evidence="EV-1025", case="CASE-101",
               desc="Call detail records for +919840099887 (PHN-002), LEA dump layout")
    pack.write("cdr", "CELL-SITE-MASTER.csv", T.cell_site_master_csv(), dtype="cdr",
               evidence="EV-1025", case="CASE-101",
               desc="CGI to tower address / lat-lon mapping for every cell in the CDRs")

    # ---- 04 FINANCIAL ----------------------------------------------------
    fn, body = D.bank_requisition()
    pack.write("finance", fn, body, dtype="finance", evidence="EV-3070", case="CASE-305",
               desc="Requisition to the bank nodal officer under s.94 BNSS")
    for acc, label in [("ACC-001", "AC-33901122_Suresh-Balan"),
                       ("ACC-002", "AC-44120987_Divya-Nair")]:
        head = T.bank_statement_header_text(acc)
        pack.write("finance", f"BANK-STATEMENT-COVER_{label}_Aug2025.txt", head,
                   dtype="finance", evidence="EV-3070", case="CASE-305",
                   desc=f"Certified statement cover page for {acc}")
        pack.write("finance", f"BANK-STATEMENT_{label}_Aug2025.csv",
                   T.bank_statement_csv(acc), dtype="finance", evidence="EV-3070",
                   case="CASE-305",
                   desc=f"Transaction rows for {acc} with running balance - the exact "
                        f"rows the platform analyses")
        text_to_pdf("finance", f"BANK-STATEMENT-COVER_{label}_Aug2025.txt", head,
                    f"Bank statement cover - {label}", dtype="finance",
                    evidence="EV-3070", case="CASE-305", desc="Statement cover (PDF)")

    # ---- 05 SURVEILLANCE -------------------------------------------------
    fn, body = D.surveillance_report_case_101()
    pack.write("surveillance", fn, body, dtype="surveillance", evidence="EV-1026",
               case="CASE-101", desc="Static field observation log, Guindy Industrial Estate")
    text_to_pdf("surveillance", fn, body, f"{fn}  (EV-1026 / CASE-101)",
                dtype="surveillance", evidence="EV-1026", case="CASE-101",
                desc="Field observation log (PDF rendering)")
    pack.write("surveillance", "ANPR-CAMERA-LOG_Aug2025.csv", T.anpr_csv(),
               dtype="surveillance", evidence="EV-1026", case="MULTI",
               desc="Automatic number plate reader log across 5 camera sites; 8 evidenced "
                    "reads plus routine traffic")

    # ---- 06 INTELLIGENCE -------------------------------------------------
    for fn, body, ev, case, desc in [
        (*D.intel_report_case_202(), "EV-2043", "CASE-202",
         "5x5x5-graded note carrying the deliberate Madurai / Chennai Central contradiction"),
        (*D.intel_report_case_305(), "EV-3071", "CASE-305",
         "5x5x5-graded note placing TN01AB1234 at Chennai Port"),
    ]:
        pack.write("intel", fn, body, dtype="intel", evidence=ev, case=case, desc=desc)
        text_to_pdf("intel", fn, body, f"{fn}  ({ev} / {case})", dtype="intel",
                    evidence=ev, case=case, desc=desc + " (PDF rendering)")

    # ---- 07 IMAGE --------------------------------------------------------
    imgdir = OUT / FOLDERS["image"]
    imgdir.mkdir(parents=True, exist_ok=True)
    cctv_raw = raw / "raw_cctv_chennai_central.png"
    surv_raw = raw / "raw_surveillance_guindy.png"
    if cctv_raw.exists():
        out = imgdir / "EV-2042_CCTV-still_Chennai-Central_2025-08-18T1007Z.png"
        osd_overlay(cctv_raw, out, "CAM-CHN-CENTRAL-04",
                    "2025-08-18  10:07:00 IST", "CHENNAI CENTRAL APPROACH RD  LOC-001",
                    "EV-2042 / CASE-202 - registered object was altered after registration "
                    "(integrity demo)")
        pack.record(out, "image", "EV-2042", "CASE-202",
                    "CCTV still backing EV-2042. The registered copy of this object is the "
                    "one deliberately altered so the SHA-256 check reports a mismatch")
        out2 = imgdir / "EV-2042b_ANPR-plate-crop_Chennai-Central_2025-08-18T1007Z.png"
        plate_crop(cctv_raw, out2, "TN01AB1234")
        pack.record(out2, "image", "EV-2042", "CASE-202",
                    "Composited ANPR plate crop showing TN01AB1234 - the identifier that "
                    "links CASE-101, CASE-202 and CASE-305")
    if surv_raw.exists():
        out3 = imgdir / "EV-1026_surveillance-still_Guindy_2025-08-12T1230Z.png"
        osd_overlay(surv_raw, out3, "DC-114 DEPARTMENTAL CAMERA",
                    "2025-08-12  12:30:00 IST", "GUINDY INDUSTRIAL ESTATE  LOC-003",
                    "EV-1026 / CASE-101 - still accompanying the field observation log")
        pack.record(out3, "image", "EV-1026", "CASE-101",
                    "Illustrative surveillance still accompanying the Guindy observation log")
    pack.write("image", "IMAGE-EVIDENCE-METADATA.csv", T.image_metadata_csv(),
               dtype="image", evidence="EV-2042", case="CASE-202",
               desc="EXIF-style metadata for every image, including the explicit "
                    "'no OCR was performed' declaration")
    pack.write("image", "README_IMAGE_HONESTY_NOTE.txt", IMAGE_NOTE, dtype="image",
               desc="Plain statement of what the images are and are not")

    # ---- 09 CSV ----------------------------------------------------------
    csvs = [
        ("CASES.csv", T.cases_csv(), "5 cases including the deliberately evidence-poor CASE-512"),
        ("USERS_AND_RBAC.csv", T.users_csv(), "4 demo accounts, roles and case-level access"),
        ("EVIDENCE_REGISTER.csv", T.evidence_register_csv(),
         "10 evidence items mapped to the source file in this pack that backs each one"),
        ("ENTITIES_MASTER.csv", T.entities_master_csv(),
         "All 37 entities of all 7 types in one register"),
        ("ENTITIES_PERSONS.csv", T.persons_csv(), "15 persons with their identifiers"),
        ("ENTITIES_VEHICLES.csv", T.vehicles_csv(), "5 vehicles and their case spread"),
        ("ENTITIES_LOCATIONS.csv", T.locations_csv(), "6 locations with coordinates"),
        ("ENTITIES_PHONES.csv", T.phones_csv(), "4 phone numbers and CDR availability"),
        ("ENTITIES_ACCOUNTS.csv", T.accounts_csv(), "3 bank accounts"),
        ("ENTITIES_ORGS_AND_DEVICES.csv", T.orgs_devices_csv(), "2 organisations, 2 devices"),
        ("RELATIONSHIPS.csv", T.relationships_csv(),
         "28 relationships, each citing the evidence id that supports it"),
        ("EVENTS_TIMELINE.csv", T.events_csv(), "17 timeline events, 10-27 Aug 2025"),
        ("TRANSACTIONS.csv", T.transactions_csv(),
         "63 transactions: baseline plus the 50-transaction burst that the anomaly "
         "detector flags"),
        ("CONTRADICTIONS.csv", T.contradictions_csv(), "The open contradiction CON-001"),
        ("CROSS_CASE_OVERLAPS.csv", T.cross_case_overlap_csv(),
         "Every shared identifier between cases, with the basis for the link"),
        ("EXPECTED_ANALYSIS_OUTCOMES.csv", T.expected_outcomes_csv(),
         "What the platform should output for each stage - use this to check the demo live"),
    ]
    for name, content, desc in csvs:
        pack.write("csv", name, content, dtype="csv", desc=desc)

    # ---- 10 CUSTODY ------------------------------------------------------
    for ev in ["EV-1024", "EV-1025", "EV-2041", "EV-2042", "EV-3070"]:
        fn, body = D.chain_of_custody(ev)
        pack.write("custody", fn, body, dtype="custody", evidence=ev,
                   case=S.EVIDENCE_BY_ID[ev]["case_id"],
                   desc=f"Chain of custody / evidence movement register for {ev}")
    for subject, ref, ev, case, custodian, device, on in [
        ("Call detail records of +919840012345 and +919840099887",
         "STL/CERT/2025/2214", "EV-1025", "CASE-101",
         "Nodal Officer (LEA), Synthetic Telecom Ltd", "STL mediation and billing system",
         "14/08/2025"),
        ("Statement of account A/C 33901122 and A/C 44120987",
         "BCBK/CERT/2025/0881", "EV-3070", "CASE-305",
         "Nodal Officer, Bharat Coastal Bank (synthetic)", "Core banking system",
         "25/08/2025"),
        ("CCTV still from camera CAM-CHN-CENTRAL-04",
         "CCTV/CERT/2025/0119", "EV-2042", "CASE-202",
         "Control Room In-charge, City Surveillance (synthetic)",
         "City surveillance DVR, channel 04", "18/08/2025"),
    ]:
        fn, body = D.certificate_63(subject, ref, ev, case, custodian, device, on)
        pack.write("custody", fn, body, dtype="custody", evidence=ev, case=case,
                   desc=f"s.63(4)(c) BSA 2023 electronic-record certificate for {ev}")

    # ---- 08 PDF CASE BUNDLES --------------------------------------------
    build_case_bundles()

    # ---- manifest + index ------------------------------------------------
    write_manifest()
    write_index()


IMAGE_NOTE = """SYNTHETIC DEMONSTRATION DATA - IMAGE EVIDENCE HONESTY NOTE
================================================================================

WHAT THESE IMAGES ARE
  * AI-generated pictures produced for this prototype, then overlaid with a
    synthetic camera OSD (camera id, timestamp, location) using a drawing
    library. The number plate in the ANPR crop was drawn on, not photographed.

WHAT THESE IMAGES ARE NOT
  * They are not photographs.
  * They are not CCTV footage.
  * They do not depict any real person, vehicle, place or event.
  * No face in any image is a real person's face and no facial recognition,
    face matching or person identification has been performed on them.

WHAT THE PLATFORM DOES WITH THEM
  * It registers the object, computes its SHA-256 digest and stores the digest
    in an append-only ledger.
  * It does NOT run OCR. No OCR engine is installed in this environment, and the
    platform says so explicitly on the evidence record
    (ocr_applied = FALSE, text_origin = PREPROCESSED_SYNTHETIC_TEXT).
  * The text associated with an image item is a human-written synthetic
    description, and it is labelled as such rather than presented as a machine
    reading of the picture.

THE INTEGRITY DEMONSTRATION
  * EV-2042 is deliberately altered in storage AFTER its hash was registered.
  * Running the integrity check on EV-2042 therefore reports INTEGRITY_MISMATCH
    while the other nine items report VERIFIED.
  * This is the intended behaviour and is the point of the demonstration.
"""


def build_case_bundles() -> None:
    order = {
        "CASE-101": ["01_FIR/FIR_0412-2025_CASE-101_Chennai-Central.txt",
                     "03_CDR_CALL_DETAIL_RECORDS/CDR-REQUISITION_Cr-0412-2025_CASE-101.txt",
                     "03_CDR_CALL_DETAIL_RECORDS/CDR-COVERING-LETTER_STL-2025-2214.txt",
                     "05_SURVEILLANCE_REPORTS/SURVEILLANCE-REPORT_OP-KAVAL-07_CASE-101_Guindy.txt",
                     "10_CHAIN_OF_CUSTODY_AND_CERTIFICATES/CHAIN-OF-CUSTODY_EV-1024.txt"],
        "CASE-202": ["02_POLICE_REPORT/POLICE-REPORT_Cr-0518-2025_CASE-202_Chennai-Central.txt",
                     "06_INTELLIGENCE_REPORTS/INTELLIGENCE-REPORT_INT-2025-0442_CASE-202.txt",
                     "10_CHAIN_OF_CUSTODY_AND_CERTIFICATES/CHAIN-OF-CUSTODY_EV-2042.txt",
                     "10_CHAIN_OF_CUSTODY_AND_CERTIFICATES/"
                     "CERTIFICATE-63-BSA_CCTV-CERT-2025-0119_EV-2042.txt"],
        "CASE-305": ["04_FINANCIAL_RECORDS/BANK-REQUISITION_CASE-305.txt",
                     "04_FINANCIAL_RECORDS/BANK-STATEMENT-COVER_AC-33901122_Suresh-Balan_Aug2025.txt",
                     "06_INTELLIGENCE_REPORTS/INTELLIGENCE-REPORT_INT-2025-0517_CASE-305.txt",
                     "10_CHAIN_OF_CUSTODY_AND_CERTIFICATES/CHAIN-OF-CUSTODY_EV-3070.txt"],
        "CASE-407": ["02_POLICE_REPORT/POLICE-REPORT_Enq-0134-2025_CASE-407_Coimbatore.txt"],
        "CASE-512": ["01_FIR/FIR_0731-2025_CASE-512_Anonymous-Tip.txt"],
    }
    for case_id, files in order.items():
        case = S.CASE_BY_ID[case_id]
        lines = [
            "=" * 80,
            f"CASE FILE BUNDLE - {case_id}".center(80),
            case["title"].center(80),
            "SYNTHETIC DEMONSTRATION DATA".center(80),
            "=" * 80, "",
            D.kv(" Case", f"{case_id} - {case['title']}"),
            D.kv(" Type / priority / status",
                 f"{case['case_type']} / {case['priority']} / {case['status']}"),
            D.kv(" Opened", case["created_date"]),
            D.kv(" Officer of record", case["investigator"]),
            D.kv(" Jurisdiction", "Synthetic Jurisdiction"),
            "", " Description:",
        ]
        for w in _wrap(case["description"], 74):
            lines.append("   " + w)
        evs = [e for e in S.EVIDENCE_DOCS if e["case_id"] == case_id]
        lines += ["", " Evidence items registered in CrimeNet AI for this case:", ""]
        for e in evs:
            lines.append(f"   {e['evidence_id']}  {e['evidence_type']:<22} {e['timestamp']}")
            lines.append(f"              source: {e['source']}")
            lines.append(f"              file  : {SOURCE_FILE_FOR.get(e['evidence_id'], '-')}")
        lines += ["", " Documents contained in this bundle:", ""]
        for f in files:
            lines.append("   - " + f)
        lines += ["", "=" * 80, ""]
        for f in files:
            p = OUT / f
            if not p.exists():
                continue
            lines += ["", "#" * 80, f"# DOCUMENT: {Path(f).name}", "#" * 80, ""]
            lines += p.read_text(encoding="utf-8").splitlines()
        out = OUT / FOLDERS["pdf"] / f"{case_id}_EVIDENCE-BUNDLE.pdf"
        out.parent.mkdir(parents=True, exist_ok=True)
        render_pdf(lines, out, f"{case_id} evidence bundle - {case['title']}", case_id)
        pack.record(out, "pdf", "", case_id,
                    f"Every narrative document for {case_id} in one printable PDF "
                    f"({len(evs)} evidence items)")


def _wrap(text: str, width: int) -> list[str]:
    words, out, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > width:
            out.append(cur)
            cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        out.append(cur)
    return out


def write_manifest() -> None:
    rows = sorted(pack.rows, key=lambda r: r["path"])
    header = ["FILE_PATH", "FOLDER", "DATASET_TYPE", "FORMAT", "EVIDENCE_ID", "CASE_ID",
              "SIZE_BYTES", "SHA256", "DESCRIPTION", "CLASSIFICATION"]
    body = [[r["path"], r["folder"], r["type"], r["format"], r["evidence"], r["case"],
             r["bytes"], r["sha256"], r["desc"], CLS] for r in rows]
    (OUT / "DATASET_MANIFEST.csv").write_text(T.to_csv(header, body), encoding="utf-8")


def _today() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d %B %Y")
    except Exception:
        return datetime.now().strftime("%d %B %Y")


def write_index() -> None:
    rows = sorted(pack.rows, key=lambda r: r["path"])
    by_folder: dict[str, list[dict]] = {}
    for r in rows:
        by_folder.setdefault(r["folder"], []).append(r)
    total_bytes = sum(r["bytes"] for r in rows)
    txns = S.transactions()

    L: list[str] = []
    a = L.append
    a("# CrimeNet AI — Synthetic Dataset Pack")
    a("")
    a("**Evidence → Relationships → Analysis → Validation**")
    a("")
    a(f"> **{CLS}.** Every file in this pack is fictional. No real person, vehicle, "
      f"phone number, bank account, case, police station, bank or telecom operator is "
      f"represented. Nothing here is evidence and nothing here may be used "
      f"operationally.")
    a("")
    a(f"Generated {_today()} · "
      f"{len(rows)} files · {total_bytes/1024:.0f} KB · "
      f"{len(by_folder)} folders")
    a("")
    a("---")
    a("")
    a("## 1. Is every dataset type present?")
    a("")
    a("| # | Dataset type asked for | Present | Where | Format(s) |")
    a("|---|---|---|---|---|")
    checklist = [
        ("FIR", "01_FIR", "2 files (CASE-101 vehicle theft, CASE-512 anonymous tip)",
         "TXT + PDF"),
        ("Police report", "02_POLICE_REPORT", "2 files (CASE-202 case diary, CASE-407 enquiry)",
         "TXT + PDF"),
        ("CDR", "03_CDR_CALL_DETAIL_RECORDS",
         "2 subscriber dumps + cell-site master + requisition + covering letter",
         "CSV + TXT + PDF"),
        ("Financial record", "04_FINANCIAL_RECORDS",
         "2 certified bank statements + requisition", "CSV + TXT + PDF"),
        ("Surveillance report", "05_SURVEILLANCE_REPORTS",
         "Field observation log + ANPR camera log", "TXT + PDF + CSV"),
        ("Intelligence report", "06_INTELLIGENCE_REPORTS",
         "2 notes graded on the 5×5×5 scale", "TXT + PDF"),
        ("Image", "07_IMAGE_EVIDENCE",
         "3 stills with camera OSD + EXIF-style metadata", "PNG + CSV + TXT"),
        ("PDF", "08_PDF_CASE_BUNDLES",
         "5 per-case printable bundles, plus a PDF of every narrative document in its own "
         "folder", "PDF"),
        ("CSV", "09_CSV_STRUCTURED_DATASETS",
         "16 machine-readable registers (cases, entities, relationships, events, "
         "transactions…)", "CSV"),
    ]
    for i, (name, folder, what, fmt) in enumerate(checklist, 1):
        a(f"| {i} | **{name}** | ✅ | `{folder}/` — {what} | {fmt} |")
    a("| + | Chain of custody & s.63 BSA certificates | ✅ (bonus) | "
      "`10_CHAIN_OF_CUSTODY_AND_CERTIFICATES/` — 5 custody registers, 3 certificates | TXT |")
    a("")
    a("Every dataset type you listed is present, in the format that artefact really uses.")
    a("")
    a("---")
    a("")
    a("## 2. Why these files look real")
    a("")
    a("| Artefact | Real-world layout it follows |")
    a("|---|---|")
    a("| FIR | Form **IF1** (Integrated Investigation Form 1) — all 15 numbered items, "
      "sections cited under BNS 2023 with the erstwhile IPC equivalents, GD entry "
      "reference, delay explanation, property table, despatch-to-court entry |")
    a("| Police report | Case diary extract, Part I — Cr. No., sections, IO, timed "
      "observation table, assessment, action taken, countersignature |")
    a("| CDR | LEA dump column set — `TARGET_MSISDN, CALL_TYPE, A_PARTY, B_PARTY, "
      "FIRST_CGI, LAST_CGI, IMEI, IMSI, CIRCLE, ROAMING` — with an MCC-MNC-LAC-CID CGI "
      "resolved against a cell-site master, requested under s.94 BNSS |")
    a("| Financial record | Certified statement of account — value date, posting date, "
      "narration in `UPI/DR/ref/PAYEE/IFSC` form, debit, credit, running balance, IFSC |")
    a("| Surveillance report | Static observation log — operation reference, written "
      "authority, observation post, timed entries, still-image references, no-intrusion "
      "caveat |")
    a("| Intelligence report | **5×5×5** national intelligence model — source evaluation "
      "A–E, intelligence evaluation 1–5, handling code |")
    a("| Image | Camera OSD burnt in (camera id, timestamp, location, REC indicator) plus "
      "EXIF-style metadata sidecar |")
    a("| Certificates | s.**63(4)(c) Bharatiya Sakshya Adhiniyam 2023** (erstwhile s.65B "
      "Evidence Act) electronic-record certificate, with the SHA-256 of the produced file |")
    a("")
    a("Realistic **layout**, entirely fictional **content** — and every page carries a "
      "synthetic-data banner and watermark so a printed copy can never be mistaken for a "
      "real document.")
    a("")
    a("---")
    a("")
    a("## 3. The dataset in numbers")
    a("")
    a("| Item | Count | Spec minimum | Met |")
    a("|---|---|---|---|")
    counts = [
        ("Cases", len(S.CASES), 5), ("Persons", len(S.PERSONS), 15),
        ("Vehicles", len(S.VEHICLES), 5), ("Locations", len(S.LOCATIONS), 5),
        ("Evidence items", len(S.EVIDENCE_DOCS), 5),
        ("Relationships", len(S.RELATIONSHIPS), 10),
    ]
    for name, got, need in counts:
        a(f"| {name} | {got} | {need} | {'✅' if got >= need else '❌'} |")
    a(f"| Phones / accounts / orgs / devices | {len(S.PHONES)} / {len(S.ACCOUNTS)} / "
      f"{len(S.ORGS)} / {len(S.DEVICES)} | — | ✅ |")
    a(f"| **Entities in total** | **{len(S.PERSONS)+len(S.VEHICLES)+len(S.LOCATIONS)+len(S.PHONES)+len(S.ACCOUNTS)+len(S.ORGS)+len(S.DEVICES)}** "
      f"(+ {len(S.CASES)} case nodes in the graph) | — | ✅ |")
    a(f"| Timeline events | {len(S.EVENTS)} | — | ✅ |")
    a(f"| Financial transactions | {len(txns)} | — | ✅ |")
    a("| Cross-case overlaps | 8 | ≥1 | ✅ |")
    a("| Anomalies | 1 (50-txn burst, 22 Aug 14:00) | ≥1 | ✅ |")
    a("| Contradictions | 1 (CON-001, Madurai vs Chennai Central) | ≥1 | ✅ |")
    a("| Information gaps | 5 (incl. the missing 15–19 Aug CDR) | ≥1 | ✅ |")
    a("| Evidence-poor case | CASE-512 → INSUFFICIENT EVIDENCE | ≥1 | ✅ |")
    a("")
    a("---")
    a("")
    a("## 4. The demonstration scenario, told through the files")
    a("")
    a("| Step | File to open | What it shows |")
    a("|---|---|---|")
    a("| 1 | `01_FIR/FIR_0412-2025_CASE-101…` | 10 Aug — **Ravi Kumar** with "
      "**TN01AB1234** at **Chennai Central** |")
    a("| 2 | `03_CDR…/CDR_9840012345…csv` | 12 Aug 10:15 — a 96-second call to "
      "+919840099887 off the Guindy cell |")
    a("| 3 | `05_SURVEILLANCE…/SURVEILLANCE-REPORT_OP-KAVAL-07…` | 12 Aug — TN07XY4455 "
      "and two persons at Guindy |")
    a("| 4 | `02_POLICE_REPORT/POLICE-REPORT_Cr-0518-2025…` | 18 Aug — **R. Kumar**, the "
      "**same vehicle**, the same location |")
    a("| 5 | `06_INTELLIGENCE…/INT-2025-0442…` | The **contradiction**: the same profile "
      "reported at Madurai five minutes earlier |")
    a("| 6 | `06_INTELLIGENCE…/INT-2025-0517…` | 25 Aug — **Ravi K.** and the same vehicle "
      "at Chennai Port |")
    a("| 7 | `09_CSV…/CROSS_CASE_OVERLAPS.csv` | The link across all three cases is the "
      "**registration number**, not the name |")
    a("| 8 | `04_FINANCIAL…/BANK-STATEMENT_AC-33901122…csv` | The 50-transaction burst on "
      "22 Aug that the anomaly detector flags |")
    a("| 9 | `03_CDR…/CDR-COVERING-LETTER…` | The **information gap**: no telecom records "
      "for 15–19 Aug, so 18 Aug cannot be resolved |")
    a("| 10 | `01_FIR/FIR_0731-2025_CASE-512…` | The tip with no particulars → "
      "**INSUFFICIENT EVIDENCE** |")
    a("")
    a("The three name variants — *Ravi Kumar*, *R. Kumar*, *Ravi K.* — are **never merged "
      "by the system**. They are raised as a candidate identity at 95.0 similarity and "
      "left for a human to decide, precisely because CON-001 is unresolved.")
    a("")
    a("---")
    a("")
    a("## 5. Full file inventory")
    a("")
    for folder in sorted(by_folder):
        a(f"### `{folder}/`")
        a("")
        a("| File | Format | Evidence | Case | What it is |")
        a("|---|---|---|---|---|")
        for r in by_folder[folder]:
            a(f"| `{Path(r['path']).name}` | {r['format']} | {r['evidence'] or '—'} | "
              f"{r['case'] or '—'} | {r['desc']} |")
        a("")
    a("---")
    a("")
    a("## 6. Integrity of the pack itself")
    a("")
    a("`DATASET_MANIFEST.csv` lists every file with its **SHA-256** digest, size, dataset "
      "type, and the evidence id and case it belongs to. To prove no file has been "
      "changed since generation:")
    a("")
    a("```bash")
    a("cd datasets")
    a("python3 - <<'PY'")
    a("import csv, hashlib, pathlib")
    a("bad = 0")
    a("for r in csv.DictReader(open('DATASET_MANIFEST.csv')):")
    a("    h = hashlib.sha256(pathlib.Path(r['FILE_PATH']).read_bytes()).hexdigest()")
    a("    if h != r['SHA256']:")
    a("        bad += 1; print('MISMATCH', r['FILE_PATH'])")
    a("print('OK' if not bad else f'{bad} mismatched')")
    a("PY")
    a("```")
    a("")
    a("This is the same principle the platform applies to evidence: hash at registration, "
      "re-hash on demand, report any difference rather than hide it.")
    a("")
    a("---")
    a("")
    a("## 7. How this pack relates to the running application")
    a("")
    a("These files are generated **from the application's own seed data** "
      "(`backend/app/database/seed.py`) by `tools/build_datasets.py`, which reads that file "
      "directly. So the paperwork and the running demo can never drift apart: every name, "
      "plate, number, amount and timestamp in this pack is the same value the application "
      "serves through its API.")
    a("")
    a("`09_CSV_STRUCTURED_DATASETS/EVIDENCE_REGISTER.csv` maps each of the 10 evidence "
      "items to the exact file here that backs it, and "
      "`EXPECTED_ANALYSIS_OUTCOMES.csv` states what the platform should output at each of "
      "the 13 pipeline stages — so the dataset can be checked against the live demo, "
      "stage by stage.")
    a("")
    a("Regenerate at any time with:")
    a("")
    a("```bash")
    a("python3 -m tools.build_datasets")
    a("```")
    a("")

    (OUT / "00_START_HERE_DATASET_INDEX.md").write_text("\n".join(L), encoding="utf-8")


if __name__ == "__main__":
    build()
    print(f"{len(pack.rows)} files written to {OUT}")
