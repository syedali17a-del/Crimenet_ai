"""PII PRESENTATION POLICY - masking of structured identifiers in API responses.

THE PROBLEM THIS SOLVES
    Phone numbers and account numbers are stored with authenticated field encryption
    (`app/security/crypto.py`, AES-256-GCM) in the `attributes` of the PHONE / ACCOUNT
    nodes. But the SAME digits were also the node's human-readable `label`, its
    `normalized` value, and part of every graph, entity-list and relationship response -
    so the ciphertext protected a copy nobody read, while the real value travelled in
    plaintext through the API and into the UI. Encryption that is bypassed by the
    presentation layer is not protecting anything.

THE POLICY (option (a) of the two offered: mask by default, reveal on demand)
    * PHONE      -> country code + first five digits + last digit:  +91 98400 ••••5
                    Enough for an investigator to recognise a number they already hold,
                    not enough to dial it or to harvest identifiers from the graph.
    * ACCOUNT    -> last four digits only:                          A/C ••••1122
    * DEVICE     -> last four digits only:                          IMEI ••••3809
    * VEHICLE    -> NOT masked. A registration mark is a public identifier printed on
                    the vehicle and quoted in FIR text; masking it would make the graph
                    unusable for its actual investigative purpose. This is a deliberate,
                    stated exception rather than an oversight.
    * PERSON / ORGANIZATION / LOCATION -> not identifiers, not masked.

    The FULL value is available through one dedicated, audited action:
    `GET /api/entities/{entity_id}/reveal` (permission `evidence:read`, case-level
    authorization, and an `IDENTIFIER_REVEALED` audit record on every call).

WHAT IS NOT MASKED, AND WHY
    Evidence TEXT is not masked. A document is the thing an investigator must be able to
    read, it is the reason the system exists, and the digits in it are the same digits
    the graph was built from. Access to it is case-authorized and audited (see
    `EVIDENCE_VIEWED` in app/api/evidence.py). The inconsistency being fixed here was
    that the STRUCTURED identifier was encrypted at rest and simultaneously published in
    every graph label - not that evidence remains readable.

Masking is applied at the presentation layer only. Internal matching keys
(`app/agents/graph_ops.match_key`) and the stored `normalized` values keep the full
digits, so entity resolution and identifier folding are unaffected.
"""
from __future__ import annotations

import re
from typing import Any

MASKED_TYPES = ("PHONE", "ACCOUNT", "DEVICE")
MASK_CHAR = "•"
REVEAL_PERMISSION = "evidence:read"

_DIGITS = re.compile(r"\d")
_COUNTRY_PREFIX = re.compile(r"^\s*(\+\d{1,3})[\s-]*")


def _mask_phone(value: str) -> str:
    """+919840012345 -> '+91 98400 ••••5'.

    The country code is split off by making the subscriber number 10 digits (the Indian
    national length) where possible, so '+919840012345' does not come out as '+919 84001'.
    """
    digits = re.sub(r"\D", "", value)
    country = ""
    national = digits
    if value.strip().startswith("+"):
        for cc_len in (2, 1, 3):     # +91 first, then +1, then a 3-digit code
            if len(digits) - cc_len == 10:
                country, national = "+" + digits[:cc_len], digits[cc_len:]
                break
        else:
            country, national = "+" + digits[:2], digits[2:]
    if len(national) < 7:
        return f"{country} {MASK_CHAR * 4}{national[-1:]}".strip() if national \
            else f"{country} {MASK_CHAR * 4}".strip()
    return f"{country} {national[:5]} {MASK_CHAR * 4}{national[-1:]}".strip()


def _mask_tail(value: str, keep: int = 4) -> str:
    """'A/C 33901122' -> 'A/C ••••1122' (prefix words kept, digits replaced)."""
    digits = re.sub(r"\D", "", value)
    if len(digits) <= keep:
        return f"{MASK_CHAR * 4}{digits}"
    masked_tail = f"{MASK_CHAR * 4}{digits[-keep:]}"
    head = value[: value.find(digits[0])].strip() if digits and digits[0] in value else ""
    return f"{head} {masked_tail}".strip() if head else masked_tail


def mask_identifier(entity_type: str | None, value: str | None) -> str:
    """Apply the policy to one value. Unknown types are returned unchanged."""
    if not value:
        return value or ""
    if entity_type == "PHONE":
        return _mask_phone(value)
    if entity_type in ("ACCOUNT", "DEVICE"):
        return _mask_tail(value)
    return value


def is_maskable(entity_type: str | None) -> bool:
    return (entity_type or "").upper() in MASKED_TYPES


def mask_node(node: dict[str, Any] | None) -> dict[str, Any] | None:
    """Presentation copy of a graph node with its identifier masked.

    Adds `identifier_masked` and `reveal_endpoint` so a caller can see that a value was
    withheld and where the audited reveal lives, instead of assuming the digits are gone.
    """
    if not node:
        return node
    entity_type = node.get("entity_type") or node.get("type")
    if not is_maskable(entity_type):
        return node
    out = dict(node)
    out["label"] = mask_identifier(entity_type, node.get("label"))
    if node.get("normalized"):
        out["normalized"] = mask_identifier(entity_type, node["normalized"])
    out["identifier_masked"] = True
    out["masking_policy"] = ("Phone / account / device identifiers are masked in API "
                             "responses; the full value is returned only by the audited "
                             "reveal action.")
    out["reveal_endpoint"] = f"/api/entities/{node.get('id') or node.get('entity_id')}/reveal"
    return out


def mask_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [mask_node(n) or {} for n in nodes]


def reveal(node: dict[str, Any] | None) -> dict[str, Any] | None:
    """The unmasked value of an identifier node, for the audited reveal action."""
    if not node:
        return None
    entity_type = node.get("entity_type")
    if not is_maskable(entity_type):
        return None
    stored = (node.get("attributes") or {})
    cipher_field = {"PHONE": "msisdn_encrypted", "ACCOUNT": "account_encrypted"}.get(entity_type)
    return {
        "entity_id": node.get("id") or node.get("entity_id"),
        "entity_type": entity_type,
        "label": node.get("label"),
        "normalized": node.get("normalized"),
        "at_rest": {
            "field": cipher_field,
            "encrypted": bool(cipher_field and stored.get(cipher_field)),
            "note": ("The stored copy is AES-256-GCM ciphertext; it is decrypted only for "
                     "authorized access, and every access is audited."
                     if cipher_field else
                     "No encrypted copy is stored for this identifier type in the seeded "
                     "dataset."),
        },
        "masked_form": mask_identifier(entity_type, node.get("label")),
    }

# ---------------------------------------------------------------------------
# PROSE / PAYLOAD MASKING
#   The policy above covers a node's label. The same digits also travelled in
#   generated prose and structured records: CDR event titles ("Call between
#   +91... and +91..."), cross-case association signals, lead rationales and
#   resolver candidate records. An identifier that is masked on a node label but
#   printed in the sentence next to it is not masked at all, so the masking is
#   applied to those payloads as well.
#
#   EXEMPT BY DESIGN: fields that hold DOCUMENT TEXT (`content_preview`, `text`,
#   `evidence_text`, `text_content`, `notes`). The document is what an
#   investigator has to read, it is where the identifier came from, and it is
#   case-authorized and audited (EVIDENCE_VIEWED). Masking inside it would hide
#   the evidence, not protect it.
# ---------------------------------------------------------------------------

#: payload keys that carry raw document text and are therefore exempt
# Free-text document bodies are returned as stored (they are the investigator's own
# evidence and are encrypted at rest at the object layer). Everything else - labels,
# sources, interpretations, and the echoed search query - goes through mask_text.
TEXT_EXEMPT_KEYS = frozenset({"content_preview", "text", "evidence_text", "text_content", "notes"})

_PHONE_TOKEN = re.compile(r"(?<![\d])(\+?91[\s-]?)?(\d{10})(?![\d])")
_PREFIXED_TOKEN = re.compile(r"\b(A/C|AC|A\.C\.|IMEI|DEVICE)\s*[:#-]?\s*(\d[\d\s-]{4,}\d)", re.IGNORECASE)


def mask_text(value: str | None) -> str:
    """Mask every identifier-shaped token inside a piece of generated prose."""
    if not value:
        return value or ""
    out = _PREFIXED_TOKEN.sub(lambda m: _mask_tail(m.group(0)), value)

    def _phone(m: re.Match) -> str:
        return _mask_phone(("+91" + m.group(2)) if m.group(1) else m.group(2))

    return _PHONE_TOKEN.sub(_phone, out)


def mask_payload(obj: Any) -> Any:
    """Recursively mask identifier-shaped tokens in a JSON-shaped payload.

    Document-text fields listed in `TEXT_EXEMPT_KEYS` are returned untouched.
    """
    if isinstance(obj, dict):
        return {k: (v if k in TEXT_EXEMPT_KEYS else mask_payload(v)) for k, v in obj.items()}
    if isinstance(obj, list):
        return [mask_payload(v) for v in obj]
    if isinstance(obj, str):
        return mask_text(obj)
    return obj
