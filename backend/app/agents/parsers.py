"""STRUCTURED-RECORD PARSERS - CDR telephony and bank-statement ingestion.

Why this module exists
----------------------
Before this module, an uploaded CSV fell through to the free-text NER path: the
raw CSV was treated as prose, so column headers became "entities"
(TARGET_MSISDN -> PERSON, IMSI -> ORGANIZATION) and rows produced no events and
no transactions at all. These parsers read the actual tabular structure:

  * CDR CSV    -> one CALL/SMS event per row between two PHONE entities, with the
                  cell-site location attached, written to the `events` table and
                  projected into the knowledge graph as PHONE -[:CONNECTED_TO]-> PHONE
                  edges that carry the source evidence id.
  * BANK CSV   -> one row in the `transactions` table (the same table
                  `analytics/anomaly.py::_feature_frame()` reads), so uploaded
                  statements participate in behavioural-baseline analysis instead
                  of only the hand-seeded rows.

Both parsers are header-driven: they resolve columns through alias sets rather
than fixed positions, so a differently-formatted-but-valid export still parses.
Nothing is invented: a row that cannot be interpreted is reported in `errors`
rather than silently coerced.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import datetime
from typing import Any, Optional

AGENT_NAME = "DOCUMENT_INTELLIGENCE_AGENT"

# --------------------------------------------------------------------------
# Header-driven column resolution
# --------------------------------------------------------------------------
CDR_COLUMNS: dict[str, tuple[str, ...]] = {
    "record_id": ("RECORD_ID", "RECORDID", "CDR_ID", "ID"),
    "target_msisdn": ("TARGET_MSISDN", "TARGET_NUMBER", "TARGET_NO", "SUBSCRIBER"),
    "call_type": ("CALL_TYPE", "TYPE", "SERVICE_TYPE_DIRECTION", "DIRECTION"),
    "a_party": ("A_PARTY", "APARTY", "A_NUMBER", "CALLING_NUMBER", "ORIGINATING_NUMBER",
                "CALLER", "MSISDN_A"),
    "b_party": ("B_PARTY", "BPARTY", "B_NUMBER", "CALLED_NUMBER", "TERMINATING_NUMBER",
                "CALLEE", "MSISDN_B"),
    "call_date": ("CALL_DATE", "DATE", "START_DATE"),
    "call_time": ("CALL_TIME", "TIME", "START_TIME"),
    "duration": ("DURATION_SEC", "DURATION", "DURATION_SECONDS", "CALL_DURATION"),
    "first_cgi": ("FIRST_CGI", "CGI", "CELL_ID", "FIRST_CELL_ID", "LAC_CELL"),
    "first_cell_address": ("FIRST_CELL_ADDRESS", "CELL_ADDRESS", "CELL_SITE_ADDRESS",
                           "LOCATION", "FIRST_CELL"),
    "last_cell_address": ("LAST_CELL_ADDRESS", "LAST_CELL"),
    "latitude": ("LATITUDE", "LAT"),
    "longitude": ("LONGITUDE", "LON", "LONG"),
    "imei": ("IMEI",),
    "imsi": ("IMSI",),
}

BANK_COLUMNS: dict[str, tuple[str, ...]] = {
    "txn_id": ("TXN_ID", "TRANSACTION_ID", "TXN_REF", "REF_NO", "UTR", "REFERENCE"),
    "value_date": ("VALUE_DATE", "TXN_DATE", "TRANSACTION_DATE", "DATE"),
    "posting_date": ("POSTING_DATE",),
    "posting_time": ("POSTING_TIME", "TXN_TIME", "TIME"),
    "narration": ("NARRATION", "DESCRIPTION", "PARTICULARS", "REMARKS"),
    "debit": ("DEBIT_INR", "DEBIT", "WITHDRAWAL", "DEBIT_AMOUNT", "DR"),
    "credit": ("CREDIT_INR", "CREDIT", "DEPOSIT", "CREDIT_AMOUNT", "CR"),
    "balance": ("BALANCE_INR", "BALANCE", "CLOSING_BALANCE"),
    "counterparty_account": ("COUNTERPARTY_ACCOUNT", "COUNTERPARTY", "BENEFICIARY_ACCOUNT",
                             "PAYEE_ACCOUNT", "OTHER_ACCOUNT"),
    "counterparty_name": ("COUNTERPARTY_NAME", "BENEFICIARY_NAME", "PAYEE_NAME", "NAME"),
    "counterparty_ifsc": ("COUNTERPARTY_IFSC", "IFSC", "BENEFICIARY_IFSC"),
    "linked_evidence": ("LINKED_EVIDENCE", "EVIDENCE_ID"),
    "own_account": ("ACCOUNT_NO", "ACCOUNT_NUMBER", "OWN_ACCOUNT", "ACCOUNT_ID", "ACCOUNT"),
}


def _resolve_headers(fieldnames: list[str], aliases: dict[str, tuple[str, ...]]) -> dict[str, str]:
    upper = {h.strip().upper(): h for h in (fieldnames or []) if h}
    resolved: dict[str, str] = {}
    for field, names in aliases.items():
        for name in names:
            if name in upper:
                resolved[field] = upper[name]
                break
    return resolved


def _cell(row: dict[str, str], headers: dict[str, str], field: str) -> str:
    key = headers.get(field)
    return (row.get(key) or "").strip() if key else ""


# --------------------------------------------------------------------------
# Value normalisation
# --------------------------------------------------------------------------
_PHONE_DIGITS = re.compile(r"\D")


def normalise_phone(value: str) -> Optional[str]:
    digits = _PHONE_DIGITS.sub("", value or "")
    if not digits:
        return None
    if len(digits) > 10:
        digits = digits[-10:]
    if len(digits) != 10 or digits[0] not in "6789":
        return None
    return "+91" + digits


def parse_amount(value: str) -> Optional[float]:
    if value is None:
        return None
    cleaned = re.sub(r"[^0-9.\-]", "", str(value).replace(",", ""))
    if cleaned in {"", "-", "."}:
        return None
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None


_DATE_FORMATS = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d",
                 "%d/%m/%y", "%d-%b-%Y", "%d %b %Y")
_TIME_FORMATS = ("%H:%M:%S", "%H:%M", "%H.%M.%S", "%I:%M %p")


def parse_datetime(date_value: str, time_value: str = "") -> Optional[str]:
    """Tolerant date/time parsing. Indian banking and telecom exports are
    day-first (dd/mm/yyyy), so that is tried before the ISO form."""
    date_value, time_value = (date_value or "").strip(), (time_value or "").strip()
    if not date_value:
        return None
    day = None
    for fmt in _DATE_FORMATS:
        try:
            day = datetime.strptime(date_value, fmt)
            break
        except ValueError:
            continue
    if day is None:
        return None
    clock = None
    for fmt in _TIME_FORMATS:
        try:
            clock = datetime.strptime(time_value, fmt)
            break
        except ValueError:
            continue
    if clock:
        day = day.replace(hour=clock.hour, minute=clock.minute, second=clock.second)
    return day.strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# Sniffing
# --------------------------------------------------------------------------
def _read_rows(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader.fieldnames or []), [dict(r) for r in reader]


def detect_format(raw: bytes, filename: str = "", declared_type: str = "") -> Optional[str]:
    """Classify a structured upload. Returns CDR / BANK / None."""
    name = (filename or "").lower()
    if not (raw[:4096].lstrip()[:1].isalnum() or b"," in raw[:4096]):
        return None
    fieldnames, _ = _read_rows(raw)
    if not fieldnames:
        return None
    upper = {f.strip().upper() for f in fieldnames if f}
    cdr_hits = sum(1 for names in CDR_COLUMNS.values() for n in names if n in upper)
    bank_hits = sum(1 for names in BANK_COLUMNS.values() for n in names if n in upper)
    has_call_shape = bool(upper & {"A_PARTY", "B_PARTY", "CALL_TYPE", "TARGET_MSISDN"})
    has_money_shape = bool(upper & {"DEBIT_INR", "CREDIT_INR", "NARRATION", "BALANCE_INR"})
    if has_call_shape and cdr_hits >= 4:
        return "CDR"
    if has_money_shape and bank_hits >= 4:
        return "BANK"
    if declared_type.upper() == "CDR" and cdr_hits >= 3:
        return "CDR"
    if declared_type.upper() == "FINANCIAL_RECORD" and bank_hits >= 3:
        return "BANK"
    if "cdr" in name and cdr_hits >= 3:
        return "CDR"
    if ("bank" in name or "statement" in name) and bank_hits >= 3:
        return "BANK"
    return None


# --------------------------------------------------------------------------
# CDR parser
# --------------------------------------------------------------------------
def parse_cdr(raw: bytes, case_id: str, evidence_id: str,
              filename: str = "") -> dict[str, Any]:
    fieldnames, rows = _read_rows(raw)
    headers = _resolve_headers(fieldnames, CDR_COLUMNS)
    missing = [f for f in ("a_party", "b_party") if f not in headers]
    if not headers.get("call_date") or missing:
        return {"format": "CDR", "ok": False, "records": [], "errors": [
            f"CDR headers not recognised. Missing required column(s): "
            f"{', '.join(missing + ([] if headers.get('call_date') else ['call_date']))}. "
            f"Found: {', '.join(fieldnames)}"], "phone_numbers": [], "cell_sites": []}

    records: list[dict[str, Any]] = []
    errors: list[str] = []
    phone_seen: set[str] = set()
    cell_seen: dict[str, dict[str, Any]] = {}

    for index, row in enumerate(rows, start=2):
        a = normalise_phone(_cell(row, headers, "a_party"))
        b = normalise_phone(_cell(row, headers, "b_party"))
        ts = parse_datetime(_cell(row, headers, "call_date"), _cell(row, headers, "call_time"))
        if not a or not b or not ts:
            errors.append(f"Row {index}: skipped (a_party={a!r}, b_party={b!r}, timestamp={ts!r})")
            continue
        call_type = (_cell(row, headers, "call_type") or "").upper()
        if "SMS" in call_type:
            event_type, rel_type = "MESSAGE", "CONNECTED_TO"
        elif "DATA" in call_type or "GPRS" in call_type:
            event_type, rel_type = "DATA_SESSION", "CONNECTED_TO"
        else:
            event_type, rel_type = "COMMUNICATION", "CONNECTED_TO"
        duration = parse_amount(_cell(row, headers, "duration"))
        cell = (_cell(row, headers, "first_cell_address")
                or _cell(row, headers, "last_cell_address"))
        cgi = _cell(row, headers, "first_cgi")
        lat, lon = parse_amount(_cell(row, headers, "latitude")), parse_amount(_cell(row, headers, "longitude"))
        if cgi:
            cell_seen.setdefault(cgi, {"cgi": cgi, "address": cell, "lat": lat, "lon": lon})
        phone_seen.update({a, b})
        records.append({
            "record_id": _cell(row, headers, "record_id") or f"{evidence_id}-R{index}",
            "a_party": a, "b_party": b, "event_type": event_type, "rel_type": rel_type,
            "timestamp": ts, "duration_sec": duration, "call_type": call_type,
            "cell_address": cell, "cgi": cgi, "lat": lat, "lon": lon,
            "imei": _cell(row, headers, "imei"), "imsi": _cell(row, headers, "imsi"),
            "case_id": case_id, "evidence_id": evidence_id,
        })

    return {
        "format": "CDR", "ok": bool(records), "agent": AGENT_NAME,
        "records": records, "errors": errors,
        "columns_resolved": headers, "columns_present": fieldnames,
        "phone_numbers": sorted(phone_seen),
        "cell_sites": sorted(cell_seen.values(), key=lambda c: c["cgi"]),
        "summary": {
            "rows_read": len(rows), "records_parsed": len(records),
            "rows_skipped": len(errors),
            "calls": sum(1 for r in records if r["event_type"] == "COMMUNICATION"),
            "messages": sum(1 for r in records if r["event_type"] == "MESSAGE"),
            "distinct_numbers": len(phone_seen),
            "distinct_cell_sites": len(cell_seen),
            "window": {
                "from": min((r["timestamp"] for r in records), default=None),
                "to": max((r["timestamp"] for r in records), default=None),
            },
        },
    }


# --------------------------------------------------------------------------
# Bank statement parser
# --------------------------------------------------------------------------
_ACCOUNT_IN_NAME = re.compile(r"(?:AC|A/?C|ACCOUNT)[-_ ]?(\d{6,16})", re.I)


def detect_own_account(filename: str, headers: dict[str, str], rows: list[dict[str, str]]) -> tuple[Optional[str], str]:
    """Determine which account the statement belongs to.

    A statement export normally names the holder's account in an account column,
    the file name, or a header block. The counterparty column is explicitly NOT
    used, because that is the other side of the transaction.
    """
    if "own_account" in headers:
        candidate = _PHONE_DIGITS.sub("", _cell(rows[0], headers, "own_account") if rows else "")
        if 6 <= len(candidate) <= 16:
            return candidate, "account column in the statement"
    match = _ACCOUNT_IN_NAME.search(filename or "")
    if match:
        return match.group(1), "account number in the file name"
    if rows:
        candidate = _PHONE_DIGITS.sub("", _cell(rows[0], headers, "counterparty_ifsc"))
        if candidate:
            pass  # IFSC is a branch code, not an account - deliberately not used
    return None, "not stated in the file"


def parse_bank(raw: bytes, case_id: str, evidence_id: str,
               filename: str = "") -> dict[str, Any]:
    fieldnames, rows = _read_rows(raw)
    headers = _resolve_headers(fieldnames, BANK_COLUMNS)
    if "value_date" not in headers or not ({"debit", "credit"} & set(headers)):
        return {"format": "BANK", "ok": False, "transactions": [], "errors": [
            f"Bank statement headers not recognised. Need a date column and a "
            f"debit/credit column. Found: {', '.join(fieldnames)}"],
            "accounts": []}

    own_account, account_source = detect_own_account(filename, headers, rows)
    transactions: list[dict[str, Any]] = []
    errors: list[str] = []
    accounts: set[str] = set()
    names: set[str] = set()

    for index, row in enumerate(rows, start=2):
        debit = parse_amount(_cell(row, headers, "debit"))
        credit = parse_amount(_cell(row, headers, "credit"))
        amount = debit if debit is not None else credit
        direction = "DEBIT" if debit is not None else ("CREDIT" if credit is not None else None)
        ts = parse_datetime(_cell(row, headers, "posting_date") or _cell(row, headers, "value_date"),
                           _cell(row, headers, "posting_time"))
        counterparty = (_PHONE_DIGITS.sub("", _cell(row, headers, "counterparty_account"))
                        or _cell(row, headers, "counterparty_name"))
        if amount is None or not ts or not counterparty:
            errors.append(f"Row {index}: skipped (amount={amount!r}, timestamp={ts!r}, "
                          f"counterparty={counterparty!r})")
            continue
        accounts.add(counterparty)
        if _cell(row, headers, "counterparty_name"):
            names.add(_cell(row, headers, "counterparty_name"))
        txn_id = _cell(row, headers, "txn_id") or f"TXN-{evidence_id}-{index}"
        transactions.append({
            "txn_id": f"{txn_id}-{evidence_id}" if not txn_id.startswith(evidence_id) else txn_id,
            "account_id": own_account or "ACCOUNT-UNRESOLVED",
            "case_id": case_id,
            "timestamp": ts,
            "amount": amount,
            "direction": direction,
            "counterparty": counterparty,
            "counterparty_name": _cell(row, headers, "counterparty_name"),
            "channel": _cell(row, headers, "narration")[:120] or _cell(row, headers, "counterparty_ifsc"),
            "balance": parse_amount(_cell(row, headers, "balance")),
            # Provenance points at the evidence OBJECT this row was derived from
            # (the uploaded file). The statement's own cross-reference is preserved
            # separately rather than overwriting chain-of-custody provenance.
            "evidence_id": evidence_id,
            "linked_evidence_id": _cell(row, headers, "linked_evidence") or None,
        })

    dates = sorted({t["timestamp"][:10] for t in transactions})
    return {
        "format": "BANK", "ok": bool(transactions), "agent": AGENT_NAME,
        "transactions": transactions, "errors": errors,
        "own_account": own_account, "own_account_source": account_source,
        "counterparty_accounts": sorted(accounts), "counterparty_names": sorted(names),
        "columns_resolved": headers, "columns_present": fieldnames,
        "summary": {
            "rows_read": len(rows), "transactions_parsed": len(transactions),
            "rows_skipped": len(errors),
            "debits": sum(1 for t in transactions if t["direction"] == "DEBIT"),
            "credits": sum(1 for t in transactions if t["direction"] == "CREDIT"),
            "distinct_counterparties": len(accounts),
            "date_range": {"from": dates[0] if dates else None, "to": dates[-1] if dates else None},
            "total_value": round(sum(t["amount"] for t in transactions), 2),
        },
    }
