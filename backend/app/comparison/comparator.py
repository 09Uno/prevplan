from __future__ import annotations

from decimal import Decimal
from itertools import combinations

from app.comparison.rules import run_legal_rules
from app.domain.schemas import (
    CalculationSource,
    ComparisonResult,
    Divergence,
    DivergenceType,
    EvidenceRef,
    ExtractedCalculation,
    ExtractedValue,
    Severity,
)

FIELD_TYPES: dict[str, DivergenceType] = {
    "rmi": DivergenceType.RMI,
    "dib": DivergenceType.MARCO,
    "dip": DivergenceType.MARCO,
    "calculation_until": DivergenceType.MARCO,
    "correction_index": DivergenceType.INDEX,
    "interest_rate": DivergenceType.INTEREST,
    "principal": DivergenceType.TOTAL,
    "arrears": DivergenceType.TOTAL,
    "abatements": DivergenceType.ABATEMENT,
    "honoraries": DivergenceType.HONORARIES,
    "total": DivergenceType.TOTAL,
}

MONEY_FIELDS = {"rmi", "principal", "arrears", "abatements", "honoraries", "total"}
SOURCE_LABELS = {
    CalculationSource.OFFICE: "escritorio/autor",
    CalculationSource.INSS: "INSS",
    CalculationSource.COURT_ACCOUNTING: "contadoria judicial",
    CalculationSource.UNKNOWN: "fonte nao identificada",
}


def compare_calculations(calculations: list[ExtractedCalculation]) -> ComparisonResult:
    divergences: list[Divergence] = []
    for left, right in combinations(calculations, 2):
        if (
            left.source == CalculationSource.UNKNOWN
            or right.source == CalculationSource.UNKNOWN
            or left.source == right.source
        ):
            continue
        for field in FIELD_TYPES:
            divergence = compare_field(left, right, field)
            if divergence:
                divergences.append(divergence)

    known_calculations = [
        calculation for calculation in calculations if calculation.source != CalculationSource.UNKNOWN
    ]
    divergences.extend(run_legal_rules(known_calculations))
    process_number = first_process_number(calculations)
    summary = build_summary(calculations, divergences)
    return ComparisonResult(
        process_number=process_number,
        calculations=calculations,
        divergences=divergences,
        summary=summary,
    )


def compare_field(
    left: ExtractedCalculation, right: ExtractedCalculation, field: str
) -> Divergence | None:
    left_value = getattr(left, field, None)
    right_value = getattr(right, field, None)
    if not comparable(left_value) or not comparable(right_value):
        return None

    if values_equal(left_value.normalized, right_value.normalized, field):
        return None

    magnitude_money: Decimal | None = None
    magnitude_percent: Decimal | None = None
    severity = Severity.WARNING
    if field in MONEY_FIELDS and isinstance(left_value.normalized, Decimal) and isinstance(right_value.normalized, Decimal):
        magnitude_money = abs(left_value.normalized - right_value.normalized)
        base = max(abs(left_value.normalized), abs(right_value.normalized), Decimal("0.01"))
        magnitude_percent = (magnitude_money / base * Decimal("100")).quantize(Decimal("0.01"))
        if magnitude_money >= Decimal("10000"):
            severity = Severity.CRITICAL

    favored_party = infer_favored_party(field, left, right, left_value, right_value)
    return Divergence(
        type=FIELD_TYPES[field],
        field=field,
        title=human_title(field),
        description=build_description(field, left, right, left_value, right_value),
        sources=[left.source, right.source],
        values={left.source.value: left_value.normalized, right.source.value: right_value.normalized},
        magnitude_money=magnitude_money,
        magnitude_percent=magnitude_percent,
        favored_party=favored_party,
        severity=severity,
        evidence=collect_evidence(left_value, right_value),
    )


def comparable(value: ExtractedValue | None) -> bool:
    return value is not None and value.normalized not in (None, "")


def values_equal(left: object, right: object, field: str) -> bool:
    if field in MONEY_FIELDS and isinstance(left, Decimal) and isinstance(right, Decimal):
        return abs(left - right) <= Decimal("0.01")
    return str(left).strip().lower() == str(right).strip().lower()


def infer_favored_party(
    field: str,
    left: ExtractedCalculation,
    right: ExtractedCalculation,
    left_value: ExtractedValue,
    right_value: ExtractedValue,
) -> str:
    if field not in {"rmi", "principal", "arrears", "honoraries", "total", "abatements"}:
        return "unknown"
    if not isinstance(left_value.normalized, Decimal) or not isinstance(right_value.normalized, Decimal):
        return "unknown"

    higher_source = left.source if left_value.normalized > right_value.normalized else right.source
    if field == "abatements":
        return "inss" if higher_source in {CalculationSource.INSS, CalculationSource.COURT_ACCOUNTING} else "unknown"
    return "segurado" if higher_source == CalculationSource.OFFICE else "inss"


def collect_evidence(*values: ExtractedValue) -> list[EvidenceRef]:
    evidence: list[EvidenceRef] = []
    for value in values:
        if value and value.evidence:
            evidence.append(value.evidence)
    return evidence


def human_title(field: str) -> str:
    labels = {
        "rmi": "Divergencia de RMI",
        "dib": "Divergencia de DIB",
        "dip": "Divergencia de DIP",
        "calculation_until": "Marco final divergente",
        "correction_index": "Indice de correcao divergente",
        "interest_rate": "Juros divergentes",
        "principal": "Principal divergente",
        "arrears": "Atrasados divergentes",
        "abatements": "Abatimentos divergentes",
        "honoraries": "Honorarios divergentes",
        "total": "Total apurado divergente",
    }
    return labels.get(field, f"Divergencia em {field}")


def build_description(
    field: str,
    left: ExtractedCalculation,
    right: ExtractedCalculation,
    left_value: ExtractedValue,
    right_value: ExtractedValue,
) -> str:
    return (
        f"{human_title(field)} entre {SOURCE_LABELS[left.source]} ({left_value.normalized}) "
        f"e {SOURCE_LABELS[right.source]} ({right_value.normalized})."
    )


def first_process_number(calculations: list[ExtractedCalculation]) -> str | None:
    for calculation in calculations:
        if calculation.process_number and calculation.process_number.normalized:
            return str(calculation.process_number.normalized)
    return None


def build_summary(calculations: list[ExtractedCalculation], divergences: list[Divergence]) -> dict[str, object]:
    by_type: dict[str, int] = {}
    for divergence in divergences:
        by_type[divergence.type.value] = by_type.get(divergence.type.value, 0) + 1
    known_sources = {
        calculation.source.value
        for calculation in calculations
        if calculation.source != CalculationSource.UNKNOWN
    }
    return {
        "calculation_count": len(calculations),
        "divergence_count": len(divergences),
        "divergences_by_type": by_type,
        "sources": sorted(known_sources),
    }
