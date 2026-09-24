"""Domain models (Pydantic) shared by storage adapters and API schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["INVESTIGATOR", "ANALYST", "SUPERVISOR", "ADMIN"]
SupportLevel = Literal["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]
VerificationStatus = Literal["UNVERIFIED", "HUMAN_VERIFIED", "REJECTED", "UNDER_REVIEW"]


class User(BaseModel):
    user_id: str
    display_name: str
    role: Role
    badge: str
    unit: str
    password_hash: str
    case_access: list[str] = Field(default_factory=list)  # ["*"] = all cases
    active: bool = True


class Case(BaseModel):
    case_id: str
    title: str
    case_type: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    description: str
    investigator: str
    created_date: str
    status: Literal["OPEN", "ACTIVE", "UNDER_REVIEW", "CLOSED"]
    jurisdiction: str = "Chennai City (synthetic)"
    classification: str = "SYNTHETIC DEMONSTRATION DATA"


class Evidence(BaseModel):
    evidence_id: str
    case_id: str
    evidence_type: str  # FIR / CDR / FINANCIAL_RECORD / SURVEILLANCE_REPORT ...
    source: str
    timestamp: str
    uploaded_by: str
    object_key: str
    sha256: str  # hash registered at intake (immutable)
    integrity_status: Literal["VERIFIED", "MISMATCH", "UNCHECKED"] = "UNCHECKED"
    verification_status: VerificationStatus = "UNVERIFIED"
    processing_status: Literal[
        "UPLOADED", "PROCESSING", "EXTRACTED", "ENTITIES_FOUND", "RELATIONSHIPS_CANDIDATE"
    ] = "UPLOADED"
    provenance: list[dict[str, Any]] = Field(default_factory=list)
    language: str = "en"
    ocr_applied: bool = False
    text_origin: Literal["NATIVE_TEXT", "OCR", "PREPROCESSED_SYNTHETIC_TEXT"] = "NATIVE_TEXT"
    notes: str = ""
    classification: str = "SYNTHETIC DEMONSTRATION DATA"


class EntityRecord(BaseModel):
    entity_id: str
    entity_type: Literal[
        "PERSON", "ALIAS", "PHONE", "VEHICLE", "ACCOUNT", "LOCATION",
        "ORGANIZATION", "DEVICE", "EVENT", "CASE", "EVIDENCE",
    ]
    label: str
    normalized: str
    cases: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    evidence_ids: list[str] = Field(default_factory=list)
    verification_status: VerificationStatus = "UNVERIFIED"
    support_level: SupportLevel = "LOW"
    lat: Optional[float] = None
    lon: Optional[float] = None


class Relationship(BaseModel):
    relationship_id: str
    source: str
    target: str
    relationship_type: Literal[
        "ASSOCIATED_WITH", "USED", "LOCATED_AT", "CONNECTED_TO", "PART_OF",
        "MENTIONED_IN", "TRANSACTED_WITH", "OBSERVED_AT", "RELATED_TO",
    ]
    timestamp: str
    source_document: str
    evidence_id: str
    case_id: str
    support_level: SupportLevel = "LOW"
    verification_status: VerificationStatus = "UNVERIFIED"
    notes: str = ""


class CaseEvent(BaseModel):
    event_id: str
    case_id: str
    title: str
    timestamp: str
    location_id: Optional[str] = None
    entity_ids: list[str] = Field(default_factory=list)
    evidence_id: Optional[str] = None
    event_type: str = "OBSERVATION"
    description: str = ""


class Transaction(BaseModel):
    txn_id: str
    account_id: str
    case_id: str
    timestamp: str
    amount: float
    counterparty: str
    evidence_id: str


class AuditRecord(BaseModel):
    audit_id: str
    timestamp: str
    user_id: str
    role: str
    action: str
    case_id: Optional[str] = None
    object_id: Optional[str] = None
    status: str = "SUCCESS"
    detail: str = ""
    hash: Optional[str] = None
    # PHASE 4: each audit record is chained to its predecessor so that deleting or
    # editing any single record breaks the recomputation of every later record.
    prev_hash: Optional[str] = None
    chain_hash: Optional[str] = None


class LedgerBlock(BaseModel):
    index: int
    timestamp: str
    event_type: str
    evidence_id: Optional[str] = None
    case_id: Optional[str] = None
    payload_hash: str
    previous_hash: str
    block_hash: str
    integrity_status: str = "SEALED"
    recorded_by: str = "system"


class TaskRecord(BaseModel):
    task_id: str
    plan_id: str
    name: str
    agent: str
    status: Literal["PENDING", "RUNNING", "COMPLETE", "SKIPPED", "FAILED"] = "PENDING"
    depends_on: list[str] = Field(default_factory=list)
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    summary: str = ""
    result: dict[str, Any] = Field(default_factory=dict)


class Annotation(BaseModel):
    annotation_id: str
    object_id: str
    object_type: str
    case_id: Optional[str]
    author: str
    timestamp: str
    text: str


class VerificationRecord(BaseModel):
    record_id: str
    object_id: str
    object_type: str
    case_id: Optional[str]
    decision: Literal["HUMAN_VERIFIED", "REJECTED", "UNDER_REVIEW"]
    verified_by: str
    role: str
    timestamp: str
    rationale: str = ""
    evidence_ids: list[str] = Field(default_factory=list)


def now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
