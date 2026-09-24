"""Pydantic request/response schemas for the CrimeNet AI API."""
from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# --- auth ------------------------------------------------------------------
class LoginRequest(BaseModel):
    user_id: str = Field(min_length=3, max_length=32, description="Officer / User ID")
    password: str = Field(min_length=4, max_length=128)
    remember: bool = False


class UserProfile(BaseModel):
    user_id: str
    display_name: str
    role: str
    unit: str = ""
    badge: str = ""
    case_access: list[str] = []
    permissions: list[str] = []


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    expires_in: int
    user: UserProfile
    classification: str


# --- cases -----------------------------------------------------------------
class CaseCreate(BaseModel):
    case_id: Optional[str] = Field(default=None, pattern=r"^CASE-\d{3,4}$")
    title: str = Field(min_length=3, max_length=140)
    case_type: str = Field(min_length=2, max_length=60)
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "MEDIUM"
    description: str = Field(default="", max_length=2000)
    investigator: Optional[str] = None
    status: Literal["OPEN", "ACTIVE", "UNDER_REVIEW", "CLOSED"] = "OPEN"


class CaseUpdate(BaseModel):
    title: Optional[str] = None
    priority: Optional[Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]] = None
    status: Optional[Literal["OPEN", "ACTIVE", "UNDER_REVIEW", "CLOSED"]] = None
    investigator: Optional[str] = None
    description: Optional[str] = None


class CaseOut(BaseModel):
    case_id: str
    title: str
    case_type: str
    priority: str
    description: str
    investigator: str
    created_date: str
    status: str
    classification: str = "SYNTHETIC DEMONSTRATION DATA"
    evidence_count: int = 0
    entity_count: int = 0
    relationship_count: int = 0
    open_gaps: int = 0


# --- evidence --------------------------------------------------------------
class EvidenceCreate(BaseModel):
    case_id: str
    evidence_type: Literal["FIR", "POLICE_REPORT", "CDR", "FINANCIAL_RECORD",
                           "SURVEILLANCE_REPORT", "INTELLIGENCE_REPORT", "IMAGE", "PDF", "CSV"]
    source: str = Field(min_length=2, max_length=120)
    timestamp: Optional[str] = None
    text_content: Optional[str] = Field(default=None, max_length=20000,
                                        description="Native or preprocessed text for the evidence item")
    use_synthetic_sample: bool = False
    notes: str = ""
    source_trust: Optional[Literal["OFFICER_UPLOAD", "BULK_IMPORT", "EXTERNAL_SUBMISSION"]] = Field(
        default=None,
        description="How the document arrived. Derived from the intake path when omitted; "
                    "weighs how much corroboration this evidence can carry.")


class EvidenceOut(BaseModel):
    evidence_id: str
    case_id: str
    evidence_type: str
    source: str
    timestamp: str
    uploaded_by: str
    sha256: str
    integrity_status: str
    verification_status: str
    processing_status: str
    text_origin: str
    ocr_applied: bool
    provenance: list[dict[str, Any]] = []
    notes: str = ""
    classification: str = "SYNTHETIC DEMONSTRATION DATA"
    size_bytes: int = 0
    source_trust: Optional[str] = None
    source_trust_weight: Optional[float] = None
    source_trust_explanation: Optional[str] = None


class ProcessRequest(BaseModel):
    override_text: Optional[str] = None


# --- analysis --------------------------------------------------------------
class AnalysisRequest(BaseModel):
    case_ids: list[str] = Field(default_factory=list,
                                description="Empty = all cases the caller is authorized for")


class ShortestPathRequest(BaseModel):
    source: str
    target: str
    case_ids: list[str] = Field(default_factory=list)


class ResolutionRequest(BaseModel):
    case_ids: list[str] = Field(default_factory=list)
    min_support: Literal["INSUFFICIENT", "LOW", "MEDIUM", "HIGH"] = "LOW"


class TemporalRequest(BaseModel):
    case_ids: list[str] = Field(default_factory=list)
    entity_id: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None


class ManagerRequest(BaseModel):
    objective: Literal["CROSS_CASE_LINK", "FULL_CASE_ANALYSIS", "EVIDENCE_INTEGRITY_SWEEP"] = \
        "FULL_CASE_ANALYSIS"
    case_ids: list[str] = Field(default_factory=list)


# --- human in the loop ------------------------------------------------------
class VerificationRequest(BaseModel):
    object_type: Literal["ENTITY", "RELATIONSHIP", "CROSS_CASE_LINK", "IDENTITY_MATCH",
                         "EVIDENCE", "CONVERGENCE", "HYPOTHESIS"] = "ENTITY"
    case_id: Optional[str] = None
    rationale: str = Field(default="", max_length=1000)
    evidence_ids: list[str] = Field(default_factory=list)


class AnnotationRequest(BaseModel):
    object_type: str = "ENTITY"
    case_id: Optional[str] = None
    text: str = Field(min_length=1, max_length=2000)


# --- admin -----------------------------------------------------------------
class UserCreate(BaseModel):
    user_id: str = Field(min_length=3, max_length=32)
    display_name: str = Field(min_length=2, max_length=80)
    role: Literal["INVESTIGATOR", "ANALYST", "SUPERVISOR", "ADMIN"]
    password: str = Field(min_length=6, max_length=128)
    unit: str = ""
    case_access: list[str] = Field(default_factory=list)


class UserPatch(BaseModel):
    role: Optional[Literal["INVESTIGATOR", "ANALYST", "SUPERVISOR", "ADMIN"]] = None
    active: Optional[bool] = None
    case_access: Optional[list[str]] = None


class ErrorResponse(BaseModel):
    detail: str
    code: str = "ERROR"


class EvidenceSupportRequest(BaseModel):
    """Evidence identifiers whose combined corroboration weight should be assessed."""
    evidence_ids: list[str] = Field(min_length=1, max_length=50)
