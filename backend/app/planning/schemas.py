from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field

from app.domain.schemas import EvidenceRef


class Gender(str, Enum):
    FEMALE = "female"
    MALE = "male"


class DocumentType(str, Enum):
    CNIS = "cnis"
    CTPS = "ctps"
    PPP = "ppp"
    LTCAT = "ltcat"
    CTC = "ctc"
    REPORT = "report"
    ID = "id"
    OTHER = "other"


class PendingSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class InsuredProfile(BaseModel):
    name: str = "Segurado(a) em validacao"
    gender: Gender = Gender.MALE
    birth_date: date = date(1973, 3, 5)
    analysis_date: date = date(2026, 6, 4)
    current_contribution_years: int = 32
    current_contribution_months: int = 6
    current_contribution_days: int = 0
    contribution_base: Decimal = Decimal("8475.55")
    contributor_type: Literal["employee", "individual"] = "employee"
    special_months_before_2019: int = 0
    special_factor: Decimal = Decimal("1.4")
    target_monthly_income: Decimal | None = None


class DocumentInsight(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    file_name: str
    document_type: DocumentType
    pages: int = 1
    confidence: float = 0.0
    extracted_name: str | None = None
    extracted_birth_date: date | None = None
    contribution_duration_text: str | None = None
    detected_signals: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class NormativeReference(BaseModel):
    code: str
    title: str
    effective_from: date
    summary: str
    source_url: str
    tags: list[str] = Field(default_factory=list)


class AuditStep(BaseModel):
    label: str
    value: str
    basis: str


class RetirementScenario(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    rule_code: str
    title: str
    status: Literal["available", "projected", "needs_review", "not_applicable"]
    eligibility_date: date | None
    age_at_der: str
    contribution_time: str
    points: Decimal | None = None
    estimated_rmi: Decimal
    coefficient: Decimal
    future_contribution_months: int
    future_investment: Decimal
    recovery_months: Decimal | None = None
    roi_estimate: Decimal
    recommendation_score: Decimal
    legal_basis: str
    caveats: list[str] = Field(default_factory=list)
    audit: list[AuditStep] = Field(default_factory=list)


class PendingIssue(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    severity: PendingSeverity
    title: str
    description: str
    document_type: DocumentType | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class PlanningCase(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    profile: InsuredProfile
    documents: list[DocumentInsight]
    normative_references: list[NormativeReference]
    scenarios: list[RetirementScenario]
    pending_issues: list[PendingIssue]
    recommendation: str
    report_markdown: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PlanningRequest(BaseModel):
    profile: InsuredProfile | None = None
    documents: list[DocumentInsight] = Field(default_factory=list)


class ReportResult(BaseModel):
    text: str
    warnings: list[str] = Field(default_factory=list)
