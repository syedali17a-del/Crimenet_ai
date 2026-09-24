"""Evidence management, document intelligence pipeline and integrity API."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from ..agents import document_agent, entity_agent, evidence_agent, graph_ops, parsers
from ..analytics import trust
from ..audit import audit_log, ledger
from ..config import DATA_CLASSIFICATION
from ..database.neo4j_graph import graph_store
from ..database.object_storage import object_storage
from ..database.postgres import relational
from ..database.redis_cache import cache
from ..models.domain import now_iso
from ..schemas.api import AnnotationRequest, EvidenceCreate, EvidenceOut, ProcessRequest, VerificationRequest
from ..security.deps import Principal, authorize_case, authorized_case_ids, get_principal, require_permission

router = APIRouter(prefix="/api/evidence", tags=["evidence"])

SAMPLE_TEXTS: dict[str, str] = {
    "FIR": ("SYNTHETIC DEMONSTRATION DATA - FIR EXTRACT\n\n"
            "Ravi Kumar was observed near Chennai Central using vehicle TN01AB1234 on 10 August. "
            "Contact number +919840012345 was recorded during the complaint. The vehicle later moved "
            "towards Guindy Industrial Estate."),
    "POLICE_REPORT": ("SYNTHETIC DEMONSTRATION DATA - POLICE REPORT\n\n"
                      "On 18 August at 10:05, vehicle TN01AB1234 was observed at Chennai Central. "
                      "R. Kumar was recorded as the person using the vehicle. Arun Selvam was observed "
                      "at Chennai Central at 10:12 the same day."),
    "CDR": ("SYNTHETIC DEMONSTRATION DATA - CALL DETAIL RECORD\n\n"
            "Subscriber +919840012345 contacted +919840099887 on 12 August at 10:15 for 96 seconds. "
            "Cell reference resolves to Guindy Industrial Estate."),
    "FINANCIAL_RECORD": ("SYNTHETIC DEMONSTRATION DATA - ACCOUNT EXTRACT\n\n"
                         "Account A/C 33901122 shows 50 transactions on 22 August between 14:00 and 15:00. "
                         "Counterparty A/C 44120987. Baseline activity is about two transactions per day."),
    "SURVEILLANCE_REPORT": ("SYNTHETIC DEMONSTRATION DATA - FIELD OBSERVATION\n\n"
                            "On 25 August at 15:10, vehicle TN01AB1234 was observed at Chennai Port. "
                            "Arun Selvam was observed at Chennai Port at 15:20."),
    "INTELLIGENCE_REPORT": ("SYNTHETIC DEMONSTRATION DATA - INTELLIGENCE NOTE\n\n"
                            "An unverified note reports Ravi K. near Chennai Port on 25 August in the "
                            "company of vehicle TN01AB1234. The note is uncorroborated."),
    "IMAGE": ("SYNTHETIC DEMONSTRATION DATA - IMAGE EVIDENCE PLACEHOLDER\n"
              "No OCR engine is installed in this environment; the following preprocessed synthetic "
              "description is used instead of a machine-read transcription.\n"
              "Preprocessed description: vehicle TN01AB1234 at Chennai Central, 18 August 10:07."),
    "PDF": ("SYNTHETIC DEMONSTRATION DATA - PDF EVIDENCE PLACEHOLDER\n"
            "No OCR/PDF text layer extraction is available in this environment; preprocessed synthetic "
            "text is used.\nPreprocessed description: transport document naming Sanjay Prabhu and "
            "vehicle TN22CD3311 dated 27 August at Coimbatore RS Puram."),
    "CSV": ("SYNTHETIC DEMONSTRATION DATA - CSV EVIDENCE\n"
            "txn_id,account,timestamp,amount,counterparty\n"
            "T1,33901122,2025-08-22T14:00:00Z,4500,44120987\n"
            "T2,33901122,2025-08-22T14:01:10Z,7800,44120987"),
}

TYPE_EXT = {"IMAGE": "png", "PDF": "pdf", "CSV": "csv"}


def _out(ev: dict[str, Any]) -> EvidenceOut:
    # Older rows (seeded before source-trust existed) derive their category from the
    # intake path rather than returning None, so every consumer sees the same shape.
    category = trust.trust_of(ev)
    return EvidenceOut(
        evidence_id=ev["evidence_id"], case_id=ev["case_id"], evidence_type=ev["evidence_type"],
        source=ev.get("source", ""), timestamp=ev.get("timestamp", ""),
        uploaded_by=ev.get("uploaded_by", "system"),
        sha256=ev.get("sha256", ""), integrity_status=ev.get("integrity_status", "UNCHECKED"),
        verification_status=ev.get("verification_status", "UNVERIFIED"),
        processing_status=ev.get("processing_status", "UPLOADED"),
        text_origin=ev.get("text_origin", "NATIVE_TEXT"), ocr_applied=ev.get("ocr_applied", False),
        provenance=ev.get("provenance", []), notes=ev.get("notes", ""),
        classification=ev.get("classification", DATA_CLASSIFICATION),
        size_bytes=ev.get("size_bytes", object_storage.size(ev.get("object_key", ""))),
        source_trust=category,
        source_trust_weight=trust.weight(category),
        source_trust_explanation=trust.SOURCE_TRUST_EXPLANATION[category],
    )


def _next_evidence_id() -> str:
    nums = [int(m.group(1)) for e in relational.all("evidence")
            if (m := re.match(r"EV-(\d+)$", e["evidence_id"]))]
    return f"EV-{max(nums or [9000]) + 1}"


@router.get("", response_model=list[EvidenceOut])
def list_evidence(case_id: Optional[str] = None,
                  principal: Principal = Depends(require_permission("evidence:read"))) -> list[EvidenceOut]:
    allowed = set(authorized_case_ids(principal))
    rows = [e for e in relational.all("evidence")
            if e["case_id"] in allowed and not e.get("demo_probe")]
    if case_id:
        authorize_case(principal, case_id)
        rows = [e for e in rows if e["case_id"] == case_id]
    rows.sort(key=lambda e: e["timestamp"], reverse=True)
    return [_out(e) for e in rows]


@router.get("/{evidence_id}")
def get_evidence(evidence_id: str,
                 principal: Principal = Depends(require_permission("evidence:read"))) -> dict[str, Any]:
    ev = relational.get("evidence", evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found.")
    authorize_case(principal, ev["case_id"])
    text = object_storage.get_text(ev["object_key"]) or ""
    # READ ACCESS IS AUDITED. The list route (GET /api/evidence) is deliberately NOT
    # audited - browsing a list is noise. Opening one specific evidence record is the
    # meaningful signal: an evidence-handling system must be able to show who looked at
    # a piece of content, not only who changed it.
    audit_log.record(principal.user_id, principal.role, "EVIDENCE_VIEWED",
                     case_id=ev["case_id"], object_id=evidence_id,
                     detail=f"Opened evidence content ({ev.get('evidence_type')}, "
                            f"{len(text)} characters) for case {ev['case_id']}.")
    return {
        "evidence": _out(ev).model_dump(),
        "content_preview": text[:4000],
        "content_length": len(text),
        "extraction": ev.get("extraction"),
        "ledger": ledger.blocks_for_evidence(evidence_id),
        "related_relationships": [r for r in graph_store.relationships()
                                  if r.get("evidence_id") == evidence_id and not r.get("hidden")],
    }


@router.get("/samples/catalogue")
def sample_catalogue(principal: Principal = Depends(get_principal)) -> dict[str, Any]:
    return {"samples": [{"evidence_type": k, "preview": v[:160] + "..."} for k, v in SAMPLE_TEXTS.items()],
            "classification": DATA_CLASSIFICATION}


@router.post("", response_model=EvidenceOut, status_code=201)
def create_evidence(payload: EvidenceCreate,
                    principal: Principal = Depends(require_permission("evidence:upload"))) -> EvidenceOut:
    authorize_case(principal, payload.case_id)
    text = payload.text_content
    if payload.use_synthetic_sample or not text:
        text = SAMPLE_TEXTS.get(payload.evidence_type)
    if not text or not text.strip():
        raise HTTPException(status_code=400,
                            detail="No content supplied. Provide text content or select a synthetic sample.")
    return _register(payload.case_id, payload.evidence_type, payload.source, text.encode("utf-8"),
                     principal, payload.timestamp, payload.notes,
                     source_trust=payload.source_trust)


@router.post("/upload", response_model=EvidenceOut, status_code=201)
async def upload_evidence(
    case_id: str = Form(...),
    evidence_type: str = Form(...),
    source: str = Form("Uploaded File"),
    notes: str = Form(""),
    source_trust: Optional[str] = Form(None),
    file: UploadFile = File(...),
    principal: Principal = Depends(require_permission("evidence:upload")),
) -> EvidenceOut:
    authorize_case(principal, case_id)
    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="The selected file is empty.")
    if len(raw) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File exceeds the 5 MB demonstration limit.")
    return _register(case_id, evidence_type.upper(), source or file.filename or "Uploaded File",
                     raw, principal, None, notes, filename=file.filename,
                     source_trust=source_trust)


def _register(case_id: str, evidence_type: str, source: str, content: bytes,
              principal: Principal, timestamp: Optional[str], notes: str,
              filename: Optional[str] = None,
              source_trust: Optional[str] = None) -> EvidenceOut:
    if evidence_type not in SAMPLE_TEXTS:
        raise HTTPException(status_code=400, detail=f"Unsupported evidence type '{evidence_type}'.")
    evidence_id = _next_evidence_id()
    # SOURCE TRUST: how much corroboration weight this document can carry. Derived from
    # the intake path unless the caller declares it; see app/analytics/trust.py.
    detected = None
    if evidence_type.upper() in {"CSV"} or (filename or "").lower().endswith(".csv"):
        detected = "csv"
    trust_category = trust.derive_source_trust(source_trust, evidence_type=evidence_type,
                                               structured_kind=detected)
    ext = TYPE_EXT.get(evidence_type, "txt")
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()[:5]
    record = {
        "evidence_id": evidence_id, "case_id": case_id, "evidence_type": evidence_type,
        "source": source.strip(), "timestamp": timestamp or now_iso(),
        "uploaded_by": principal.user_id, "object_key": f"{case_id}/{evidence_id}.{ext}",
        "sha256": "", "integrity_status": "UNCHECKED", "verification_status": "UNVERIFIED",
        "processing_status": "UPLOADED", "source_trust": trust_category,
        "source_trust_explanation": trust.SOURCE_TRUST_EXPLANATION[trust_category],
        "source_trust_weight": trust.weight(trust_category),
        "text_origin": "PREPROCESSED_SYNTHETIC_TEXT" if evidence_type in {"IMAGE", "PDF"} else "NATIVE_TEXT",
        "ocr_applied": False, "provenance": [], "language": "en", "notes": notes,
        "classification": DATA_CLASSIFICATION, "size_bytes": len(content),
        "original_filename": filename,
    }
    evidence_agent.register_evidence(record, content, actor=principal.user_id)
    audit_log.record(principal.user_id, principal.role, "EVIDENCE_UPLOADED", case_id=case_id,
                     object_id=evidence_id,
                     detail=f"{evidence_type} from {source} [{trust_category}]; "
                            f"SHA-256 {record['sha256'][:16]}...")
    cache.invalidate("analysis:")
    return _out(relational.get("evidence", evidence_id))


@router.post("/{evidence_id}/process")
def process_evidence(evidence_id: str, payload: ProcessRequest | None = None,
                     principal: Principal = Depends(require_permission("evidence:process"))
                     ) -> dict[str, Any]:
    ev = relational.get("evidence", evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found.")
    authorize_case(principal, ev["case_id"])

    ev["processing_status"] = "PROCESSING"
    relational.upsert("evidence", evidence_id, ev)

    override = payload.override_text if payload else None
    raw = object_storage.get_bytes(ev["object_key"])
    if override is None and raw:
        kind = parsers.detect_format(raw, ev.get("original_filename") or "",
                                     ev.get("evidence_type") or "")
        if kind:
            return _process_structured(ev, raw, kind, principal)

    doc = document_agent.process_document(ev, override)
    if not doc["sufficient"]:
        ev["processing_status"] = "UPLOADED"
        relational.upsert("evidence", evidence_id, ev)
        audit_log.record(principal.user_id, principal.role, "EVIDENCE_PROCESSING_INSUFFICIENT",
                         case_id=ev["case_id"], object_id=evidence_id, status="INSUFFICIENT",
                         detail="No readable text could be derived from the evidence object.")
        return {"evidence_id": evidence_id, "document": doc, "entities": [], "events": [],
                "status": "INSUFFICIENT EVIDENCE",
                "message": "No readable text could be derived. Entity extraction was not attempted."}

    # Vocabulary handed to the extractor: the entities already known to this case
    # graph. For Indic-script text this doubles as the transliteration target set,
    # which is how "चेन्नई सेंट्रल" resolves to the existing node "Chennai Central".
    nodes = graph_store.nodes()
    gaz: dict[str, list[str]] = {
        "LOCATION": [n["label"] for n in nodes if n.get("entity_type") == "LOCATION"],
        "ORGANIZATION": [n["label"] for n in nodes if n.get("entity_type") == "ORGANIZATION"],
        "PERSON": [n["label"] for n in nodes if n.get("entity_type") in {"PERSON", "ALIAS"}],
        "VEHICLE": [n["label"] for n in nodes if n.get("entity_type") == "VEHICLE"],
    }
    for node in nodes:
        for alias in (node.get("attributes") or {}).get("aliases") or []:
            gaz.setdefault("PERSON", []).append(str(alias))
    gaz = {k: sorted(set(v)) for k, v in gaz.items() if v}
    extraction = entity_agent.run(doc["clean_text"], gaz)

    created = _materialise(ev, extraction, principal)

    ev.update({
        "processing_status": "RELATIONSHIPS_CANDIDATE" if created["relationships"] else
                             ("ENTITIES_FOUND" if extraction["entities"] else "EXTRACTED"),
        "text_origin": doc["text_origin"], "ocr_applied": doc["ocr_applied"],
        "language": doc["language"]["language"],
        "extraction": {"counts": extraction["counts"], "backend": extraction["backend"],
                       "entities": extraction["entities"][:60], "events": extraction["events"][:20]},
    })
    evidence_agent.add_provenance(evidence_id, "DOCUMENT_PIPELINE", principal.user_id,
                                  f"Text extracted ({doc['text_origin']}), "
                                  f"{len(extraction['entities'])} entities, "
                                  f"{len(extraction['events'])} events.")
    relational.upsert("evidence", evidence_id, ev)
    audit_log.record(principal.user_id, principal.role, "ENTITY_EXTRACTION_COMPLETED",
                     case_id=ev["case_id"], object_id=evidence_id,
                     detail=f"{len(extraction['entities'])} entities, "
                            f"{len(created['nodes'])} graph nodes, "
                            f"{len(created['relationships'])} candidate relationships.")
    ledger.append("EVIDENCE_PROCESSED",
                  {"evidence_id": evidence_id, "entities": len(extraction["entities"]),
                   "text_origin": doc["text_origin"]},
                  evidence_id=evidence_id, case_id=ev["case_id"])
    cache.invalidate("analysis:")

    return {
        "evidence_id": evidence_id,
        "status": ev["processing_status"],
        "pipeline": ["UPLOADED", "PROCESSING", "EXTRACTED", "ENTITIES_FOUND", "RELATIONSHIPS_CANDIDATE"],
        "document": doc,
        "extraction": extraction,
        "graph_updates": created,
        "evidence": _out(ev).model_dump(),
    }


def _materialise(ev: dict[str, Any], extraction: dict[str, Any],
                 principal: Principal) -> dict[str, Any]:
    """Create/extend candidate graph nodes and relationships from extracted entities.

    All created relationships are LOW support and UNVERIFIED: extraction produces
    candidates, never facts.
    """
    type_prefix = {"PERSON": "PER", "ALIAS": "PER", "VEHICLE": "VEH", "PHONE": "PHN",
                   "ACCOUNT": "ACC", "LOCATION": "LOC", "ORGANIZATION": "ORG", "DEVICE": "DEV"}
    case_id = ev["case_id"]
    created_nodes: list[str] = []
    created_rels: list[str] = []
    index: dict[str, str] = {}

    existing = graph_store.nodes()
    for ent in extraction["entities"]:
        etype = ent["entity_type"]
        if etype not in type_prefix:
            continue
        norm = ent["normalized"].upper()
        match = next((n for n in existing
                      if n.get("entity_type") in ({"PERSON", "ALIAS"} if etype in {"PERSON", "ALIAS"}
                                                  else {etype})
                      and (n.get("normalized") or "").upper() == norm), None)
        if match:
            node_id = match["id"]
            cases = sorted(set((match.get("cases") or []) + [case_id]))
            evids = sorted(set((match.get("evidence_ids") or []) + [ev["evidence_id"]]))
            graph_store.update_node(node_id, {"cases": cases, "evidence_ids": evids})
        else:
            seq = sum(1 for n in graph_store.nodes() if n.get("entity_type") == etype) + 1
            node_id = f"{type_prefix[etype]}-X{seq:03d}"
            while graph_store.node(node_id):
                seq += 1
                node_id = f"{type_prefix[etype]}-X{seq:03d}"
            graph_store.merge_node(node_id, [etype], {
                "entity_id": node_id, "entity_type": etype, "label": ent["surface"],
                "normalized": norm, "cases": [case_id],
                "attributes": {"extraction_methods": ent["methods"], "mentions": ent["mentions"]},
                "evidence_ids": [ev["evidence_id"]], "verification_status": "UNVERIFIED",
                "support_level": "LOW", "lat": None, "lon": None,
                "classification": DATA_CLASSIFICATION,
            })
            created_nodes.append(node_id)
        index[norm] = node_id

    def link(src: str, tgt: str, rtype: str, ts: str) -> None:
        rel_id = f"REL-X-{ev['evidence_id']}-{src}-{tgt}-{rtype}"
        if graph_store.relationship(rel_id):
            return
        graph_store.merge_relationship(rel_id, src, tgt, rtype, {
            "relationship_id": rel_id, "rel_type": rtype, "timestamp": ts,
            "evidence_id": ev["evidence_id"], "case_id": case_id, "support_level": "LOW",
            "verification_status": "UNVERIFIED", "source_document": ev["source"],
            "notes": "Candidate relationship derived from evidence text extraction.",
            "classification": DATA_CLASSIFICATION,
        })
        created_rels.append(rel_id)

    ts = ev["timestamp"]
    for event in extraction["events"]:
        actors = [index.get(a.upper()) for a in event["actors"]]
        actors = [a for a in actors if a]
        locs = [index.get(l.upper()) for l in event["locations"]]
        locs = [l for l in locs if l]
        persons = [a for a in actors if a.startswith("PER")]
        vehicles = [a for a in actors if a.startswith("VEH")]
        phones = [a for a in actors if a.startswith("PHN")]
        accounts = [a for a in actors if a.startswith("ACC")]
        for p in persons:
            for v in vehicles:
                link(p, v, "USED", ts)
            for ph in phones:
                link(p, ph, "USED", ts)
            for ac in accounts:
                link(p, ac, "USED", ts)
            for l in locs:
                link(p, l, "OBSERVED_AT", ts)
        for v in vehicles:
            for l in locs:
                link(v, l, "LOCATED_AT", ts)
        if len(phones) >= 2:
            link(phones[0], phones[1], "CONNECTED_TO", ts)
        # organisations and devices named alongside a person/location are candidate
        # associations in their own right (a facility at a location, a handset
        # recorded with a person).
        for o in [a for a in actors if a.startswith("ORG")]:
            for p in persons:
                link(p, o, "ASSOCIATED_WITH", ts)
            for l in locs:
                link(o, l, "LOCATED_AT", ts)
        for d in [a for a in actors if a.startswith("DEV")]:
            for p in persons:
                link(d, p, "ASSOCIATED_WITH", ts)

    # Every extracted entity is provenance-linked to its evidence source case node
    for node_id in index.values():
        link(node_id, case_id, "MENTIONED_IN", ts)

    return {"nodes": created_nodes, "relationships": created_rels,
            "linked_entities": sorted(set(index.values()))}


# --------------------------------------------------------------------------
# Structured-record ingestion (CDR / bank statement)
# --------------------------------------------------------------------------
def _graph_context() -> dict[str, Any]:
    nodes = graph_store.nodes()
    return {
        "phones": {n["normalized"]: n["id"] for n in nodes
                   if n.get("entity_type") == "PHONE" and n.get("normalized")},
        "accounts": {n["normalized"]: n["id"] for n in nodes
                     if n.get("entity_type") == "ACCOUNT" and n.get("normalized")},
        "locations": [(n["id"], n["label"], n.get("lat"), n.get("lon")) for n in nodes
                      if n.get("entity_type") == "LOCATION"],
    }


def _match_location(address: str, ctx: dict[str, Any]) -> Optional[tuple[str, bool]]:
    """Reuse an existing location node when a cell-site address contains its name
    ("Poonamallee High Road, Chennai Central, Chennai 600003" -> Chennai Central)."""
    if not address:
        return None
    low = address.lower()
    best: Optional[tuple[int, str]] = None
    for node_id, label, _lat, _lon in ctx["locations"]:
        if label and label.lower() in low:
            if best is None or len(label) > best[0]:
                best = (len(label), node_id)
    return (best[1], False) if best else None


def _process_structured(ev: dict[str, Any], raw: bytes, kind: str,
                        principal: Principal) -> dict[str, Any]:
    """Parse a tabular evidence file into events / transactions and project both
    into the knowledge graph through the shared graph_ops path."""
    case_id, evidence_id, ts = ev["case_id"], ev["evidence_id"], ev["timestamp"]
    filename = ev.get("original_filename") or ev.get("source") or ""
    parsed = (parsers.parse_cdr(raw, case_id, evidence_id, filename) if kind == "CDR"
              else parsers.parse_bank(raw, case_id, evidence_id, filename))

    if not parsed["ok"]:
        ev["processing_status"] = "UPLOADED"
        relational.upsert("evidence", evidence_id, ev)
        audit_log.record(principal.user_id, principal.role, "EVIDENCE_PROCESSING_INSUFFICIENT",
                         case_id=case_id, object_id=evidence_id, status="INSUFFICIENT",
                         detail="; ".join(parsed.get("errors", []))[:400] or "No rows parsed.")
        return {"evidence_id": evidence_id, "format": kind, "status": "INSUFFICIENT EVIDENCE",
                "parsed": parsed,
                "message": ("No record in this file could be interpreted. The reason is reported "
                            "in parsed.errors; nothing was inferred.")}

    ctx = _graph_context()
    created_nodes: list[str] = []
    created_rels: list[str] = []
    events_written = 0
    transactions_written = 0

    if kind == "CDR":
        for phone in parsed["phone_numbers"]:
            node_id, created = graph_ops.ensure_entity_node(
                "PHONE", phone, phone, case_id, evidence_id,
                attributes={"role_in_case": "subscriber or contact on furnished call records",
                            "source": "CDR"})
            if created:
                created_nodes.append(node_id)
            ctx["phones"][phone.upper()] = node_id

        cell_node: dict[str, str] = {}
        for cell in parsed["cell_sites"]:
            match = _match_location(cell.get("address") or "", ctx)
            if match:
                cell_node[cell["cgi"]] = match[0]
                continue
            label = (cell.get("address") or cell["cgi"])[:80]
            node_id, created = graph_ops.ensure_entity_node(
                "LOCATION", label, label, case_id, evidence_id,
                attributes={"cell_global_identity": cell["cgi"], "source": "CDR cell site"},
                lat=cell.get("lat"), lon=cell.get("lon"))
            cell_node[cell["cgi"]] = node_id
            if created:
                created_nodes.append(node_id)

        for index, rec in enumerate(parsed["records"], start=1):
            a = ctx["phones"].get(rec["a_party"].upper())
            b = ctx["phones"].get(rec["b_party"].upper())
            if not a or not b:
                continue
            rel = graph_ops.link(a, b, rec["rel_type"], rec["timestamp"], evidence_id, case_id,
                                 support_level="MEDIUM",
                                 notes=f"{rec['event_type']} per furnished CDR "
                                       f"({rec['call_type'] or 'CALL'}, {rec['duration_sec']}s)")
            if rel:
                created_rels.append(rel)
            site = cell_node.get(rec["cgi"] or "")
            for phone_node in (a, b):
                if site:
                    location_rel = graph_ops.link(
                        phone_node, site, "OBSERVED_AT", rec["timestamp"], evidence_id, case_id,
                        support_level="MEDIUM",
                        notes=f"Cell site {rec['cgi']} served this party at the record time")
                    if location_rel:
                        created_rels.append(location_rel)
            event_id = f"EVT-{evidence_id}-{index:04d}"
            title = (f"{rec['event_type'].title()} between {rec['a_party']} and {rec['b_party']}"
                     + (f" at {rec['cell_address']}" if rec["cell_address"] else ""))
            relational.insert("events", event_id, {
                "event_id": event_id, "case_id": case_id, "title": title,
                "timestamp": rec["timestamp"], "location_id": site,
                "entity_ids": [a, b], "evidence_id": evidence_id,
                "event_type": rec["event_type"], "description": title,
                "duration_sec": rec["duration_sec"], "cell_id": rec["cgi"],
                "b_party": rec["b_party"], "a_party": rec["a_party"],
                "source_record_id": rec["record_id"], "classification": DATA_CLASSIFICATION,
            })
            events_written += 1
        summary_key = "records_parsed"
    else:
        own_digits = parsed.get("own_account")
        own_label = own_digits or "ACCOUNT-UNRESOLVED"
        own_node, created = graph_ops.ensure_entity_node(
            "ACCOUNT", own_label, own_label, case_id, evidence_id,
            attributes={"role_in_case": "account whose statement was furnished",
                        "account_number_source": parsed.get("own_account_source", "")})
        if created:
            created_nodes.append(own_node)
        ctx["accounts"][own_label.upper()] = own_node

        for index, txn in enumerate(parsed["transactions"], start=1):
            cp = txn["counterparty"]
            cp_node = ctx["accounts"].get(cp.upper())
            if not cp_node:
                cp_node, created = graph_ops.ensure_entity_node(
                    "ACCOUNT", cp, cp, case_id, evidence_id,
                    attributes={"role_in_case": "counterparty account on furnished statement"})
                ctx["accounts"][cp.upper()] = cp_node
                if created:
                    created_nodes.append(cp_node)
            person_node = None
            if txn.get("counterparty_name"):
                person_node, created = graph_ops.ensure_entity_node(
                    "PERSON", txn["counterparty_name"], txn["counterparty_name"],
                    case_id, evidence_id,
                    attributes={"role_in_case": "named counterparty account holder",
                                "source": "bank statement"})
                if created:
                    created_nodes.append(person_node)
            rel = graph_ops.link(own_node, cp_node, "TRANSACTED_WITH", txn["timestamp"],
                                 evidence_id, case_id, support_level="MEDIUM",
                                 notes=f"{txn['direction']} of INR {txn['amount']:.2f} "
                                       f"({txn.get('channel') or 'no narration'})")
            if rel:
                created_rels.append(rel)
            if person_node:
                held = graph_ops.link(person_node, cp_node, "USED", txn["timestamp"],
                                      evidence_id, case_id, support_level="LOW",
                                      notes="Named counterparty account holder per statement")
                if held:
                    created_rels.append(held)

            # Same table analytics/anomaly.py::_feature_frame() reads, so uploaded
            # statements join the behavioural baseline instead of only seeded rows.
            relational.insert("transactions", txn["txn_id"], {
                "txn_id": txn["txn_id"], "account_id": own_node, "case_id": case_id,
                "timestamp": txn["timestamp"], "amount": txn["amount"],
                "counterparty": cp_node, "direction": txn["direction"],
                "counterparty_name": txn.get("counterparty_name"),
                "balance": txn.get("balance"), "channel": txn.get("channel"),
                "evidence_id": txn["evidence_id"],
                "linked_evidence_id": txn.get("linked_evidence_id"),
                "classification": DATA_CLASSIFICATION,
            })
            transactions_written += 1
        summary_key = "transactions_parsed"

    ev.update({
        "processing_status": "RELATIONSHIPS_CANDIDATE" if created_rels else "EXTRACTED",
        "language": "en",
        "extraction": {
            "mode": f"STRUCTURED_{kind}_PARSER",
            "counts": {kind: parsed["summary"][summary_key]},
            "summary": parsed["summary"], "errors": parsed["errors"][:20],
            "columns_resolved": {k: v for k, v in parsed.get("columns_resolved", {}).items()},
        },
    })
    evidence_agent.add_provenance(
        evidence_id, f"{kind}_PARSING", principal.user_id,
        f"{parsed['summary'][summary_key]} records parsed from a {kind} file; "
        f"{len(created_nodes)} graph nodes, {len(created_rels)} candidate relationships, "
        f"{events_written or transactions_written} records written.")
    relational.upsert("evidence", evidence_id, ev)
    audit_log.record(principal.user_id, principal.role, f"STRUCTURED_{kind}_PARSED",
                     case_id=case_id, object_id=evidence_id,
                     detail=f"{parsed['summary'][summary_key]} {kind} records, "
                            f"{len(created_rels)} candidate relationships.")
    ledger.append("EVIDENCE_PROCESSED",
                  {"evidence_id": evidence_id, "structured_format": kind,
                   "records": parsed["summary"][summary_key],
                   "events": events_written, "transactions": transactions_written},
                  evidence_id=evidence_id, case_id=case_id)
    cache.invalidate("analysis:")

    return {
        "evidence_id": evidence_id,
        "status": ev["processing_status"],
        "format": kind,
        "pipeline": ["UPLOADED", "PROCESSING", "PARSED", "GRAPH_UPDATED",
                     "RELATIONSHIPS_CANDIDATE"],
        "parsed": parsed,
        "graph_updates": {"nodes": created_nodes, "relationships": created_rels},
        "records_written": {"events": events_written, "transactions": transactions_written},
        "evidence": _out(ev).model_dump(),
    }

@router.post("/{evidence_id}/integrity-check")
def integrity_check(evidence_id: str,
                    principal: Principal = Depends(require_permission("evidence:integrity"))
                    ) -> dict[str, Any]:
    ev = relational.get("evidence", evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found.")
    authorize_case(principal, ev["case_id"])
    result = evidence_agent.integrity_check(evidence_id, actor=principal.user_id)
    audit_log.record(principal.user_id, principal.role, "INTEGRITY_CHECK", case_id=ev["case_id"],
                     object_id=evidence_id, status=result["status"],
                     detail=f"SHA-256 verification: {result['status']}.")
    return result


@router.post("/{evidence_id}/verify")
def verify_evidence(evidence_id: str, payload: VerificationRequest,
                    principal: Principal = Depends(require_permission("verification:decide"))
                    ) -> dict[str, Any]:
    return _decide(evidence_id, payload, principal, "HUMAN_VERIFIED")


@router.post("/{evidence_id}/reject")
def reject_evidence(evidence_id: str, payload: VerificationRequest,
                    principal: Principal = Depends(require_permission("verification:decide"))
                    ) -> dict[str, Any]:
    return _decide(evidence_id, payload, principal, "REJECTED")


def _decide(evidence_id: str, payload: VerificationRequest, principal: Principal,
            decision: str) -> dict[str, Any]:
    ev = relational.get("evidence", evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found.")
    authorize_case(principal, ev["case_id"])
    ev["verification_status"] = decision
    relational.upsert("evidence", evidence_id, ev)
    record = {
        "record_id": f"VER-{relational.count('verifications') + 1:04d}", "object_id": evidence_id,
        "object_type": "EVIDENCE", "case_id": ev["case_id"], "decision": decision,
        "verified_by": principal.user_id, "role": principal.role, "timestamp": now_iso(),
        "rationale": payload.rationale, "evidence_ids": [evidence_id],
    }
    relational.insert("verifications", f"EVIDENCE::{evidence_id}", record)
    audit_log.record(principal.user_id, principal.role, f"EVIDENCE_{decision}",
                     case_id=ev["case_id"], object_id=evidence_id, detail=payload.rationale)
    ledger.append(f"EVIDENCE_{decision}", record, evidence_id=evidence_id, case_id=ev["case_id"])
    return {"evidence": _out(ev).model_dump(), "verification": record,
            "note": "The original analytical finding is retained; only its verification status changed."}


@router.post("/{evidence_id}/annotate")
def annotate_evidence(evidence_id: str, payload: AnnotationRequest,
                      principal: Principal = Depends(require_permission("entity:annotate"))
                      ) -> dict[str, Any]:
    ev = relational.get("evidence", evidence_id)
    if not ev:
        raise HTTPException(status_code=404, detail=f"Evidence {evidence_id} not found.")
    authorize_case(principal, ev["case_id"])
    ann = {
        "annotation_id": f"ANN-{relational.count('annotations') + 1:04d}", "object_id": evidence_id,
        "object_type": "EVIDENCE", "case_id": ev["case_id"], "author": principal.user_id,
        "timestamp": now_iso(), "text": payload.text.strip(),
    }
    relational.insert("annotations", ann["annotation_id"], ann)
    audit_log.record(principal.user_id, principal.role, "EVIDENCE_ANNOTATED", case_id=ev["case_id"],
                     object_id=evidence_id, detail=payload.text[:180])
    return {"annotation": ann}


@router.get("/{evidence_id}/annotations")
def evidence_annotations(evidence_id: str,
                         principal: Principal = Depends(require_permission("evidence:read"))
                         ) -> dict[str, Any]:
    rows = [a for a in relational.all("annotations") if a["object_id"] == evidence_id]
    return {"annotations": sorted(rows, key=lambda a: a["timestamp"], reverse=True)}
