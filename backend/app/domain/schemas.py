from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


class CalculationSource(str, Enum):
    OFFICE = "office"
    INSS = "inss"
    COURT_ACCOUNTING = "court_accounting"
    UNKNOWN = "unknown"


class DivergenceType(str, Enum):
    INDEX = "index"
    MARCO = "marco"
    ABATEMENT = "abatement"
    INTEREST = "interest"
    HONORARIES = "honoraries"
    RMI = "rmi"
    TOTAL = "total"
    OTHER = "other"


class Severity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EvidenceRef(BaseModel):
    file_name: str
    page: int | None = None
    text: str
    locator: str | None = None


class ExtractedValue(BaseModel):
    value: Any = None
    normalized: Any = None
    confidence: float = 0.0
    evidence: EvidenceRef | None = None


class ExtractedCalculation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    source: CalculationSource
    file_name: str
    process_number: ExtractedValue | None = None
    beneficiary_name: ExtractedValue | None = None
    rmi: ExtractedValue | None = None
    dib: ExtractedValue | None = None
    dip: ExtractedValue | None = None
    calculation_until: ExtractedValue | None = None
    correction_index: ExtractedValue | None = None
    interest_rate: ExtractedValue | None = None
    principal: ExtractedValue | None = None
    arrears: ExtractedValue | None = None
    abatements: ExtractedValue | None = None
    honoraries: ExtractedValue | None = None
    total: ExtractedValue | None = None
    flags: list[str] = Field(default_factory=list)
    raw_text_sha256: str | None = None
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Divergence(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: DivergenceType
    field: str
    title: str
    description: str
    sources: list[CalculationSource]
    values: dict[str, Any]
    magnitude_money: Decimal | None = None
    magnitude_percent: Decimal | None = None
    favored_party: Literal["segurado", "inss", "neutral", "unknown"] = "unknown"
    severity: Severity = Severity.WARNING
    legal_basis: str | None = None
    evidence: list[EvidenceRef] = Field(default_factory=list)


class ComparisonResult(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    process_number: str | None = None
    calculations: list[ExtractedCalculation]
    divergences: list[Divergence]
    summary: dict[str, Any]
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DraftRequest(BaseModel):
    comparison: ComparisonResult
    target: Literal["inss", "court_accounting", "both"] = "both"
    use_ai: bool = False


class DraftResult(BaseModel):
    mode: Literal["template", "anthropic"]
    text: str
    model: str | None = None
    warnings: list[str] = Field(default_factory=list)
