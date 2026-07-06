from __future__ import annotations

from app.domain.schemas import (
    CalculationSource,
    Divergence,
    DivergenceType,
    ExtractedCalculation,
    Severity,
)


def run_legal_rules(calculations: list[ExtractedCalculation]) -> list[Divergence]:
    divergences: list[Divergence] = []
    for calculation in calculations:
        divergences.extend(rule_ec_113_selic(calculation))
        divergences.extend(rule_negative_interest(calculation))
        divergences.extend(rule_honoraries_offset(calculation))
    return divergences


def rule_ec_113_selic(calculation: ExtractedCalculation) -> list[Divergence]:
    flags = set(calculation.flags)
    text_evidence = _first_available_evidence(calculation)
    results: list[Divergence] = []

    if "mentions_tr" in flags and "mentions_ec_113_2021" in flags:
        results.append(
            Divergence(
                type=DivergenceType.INDEX,
                field="correction_index",
                title="Possivel uso de TR em periodo regido pela EC 113/2021",
                description=(
                    "O documento menciona TR/taxa referencial em contexto de EC 113/2021. "
                    "Validar se houve aplicacao indevida apos 09/12/2021."
                ),
                sources=[calculation.source],
                values={calculation.source.value: calculation.correction_index.normalized if calculation.correction_index else None},
                favored_party="inss" if calculation.source == CalculationSource.INSS else "unknown",
                severity=Severity.CRITICAL,
                legal_basis="EC 113/2021; regra parametrizavel em docs/rules.md.",
                evidence=[text_evidence] if text_evidence else [],
            )
        )

    if "mentions_selic" in flags and calculation.correction_index and "IPCA-E" in str(calculation.correction_index.normalized):
        results.append(
            Divergence(
                type=DivergenceType.INDEX,
                field="correction_index",
                title="Convivencia de IPCA-E e SELIC exige corte temporal",
                description=(
                    "O documento menciona IPCA-E e SELIC. A regra nao presume erro, mas exige "
                    "conferencia do corte temporal antes/depois da EC 113/2021."
                ),
                sources=[calculation.source],
                values={calculation.source.value: calculation.correction_index.normalized},
                favored_party="unknown",
                severity=Severity.WARNING,
                legal_basis="EC 113/2021; parametrizar marco e indice em tabela normativa.",
                evidence=[calculation.correction_index.evidence] if calculation.correction_index.evidence else [],
            )
        )
    return results


def rule_negative_interest(calculation: ExtractedCalculation) -> list[Divergence]:
    if "mentions_negative_interest" not in calculation.flags:
        return []
    evidence = _first_available_evidence(calculation)
    return [
        Divergence(
            type=DivergenceType.INTEREST,
            field="interest_rate",
            title="Juros negativos identificados",
            description=(
                "O documento menciona juros negativos. A regra sinaliza a materia para conferencia "
                "tecnica, especialmente em abatimentos ou pagamentos administrativos."
            ),
            sources=[calculation.source],
            values={calculation.source.value: calculation.interest_rate.normalized if calculation.interest_rate else None},
            favored_party="inss",
            severity=Severity.WARNING,
            legal_basis="Tema 1.207/STJ, quando aplicavel ao caso concreto.",
            evidence=[evidence] if evidence else [],
        )
    ]


def rule_honoraries_offset(calculation: ExtractedCalculation) -> list[Divergence]:
    if "mentions_unemployment_insurance_offset" not in calculation.flags or "mentions_honoraries" not in calculation.flags:
        return []
    evidence = _first_available_evidence(calculation)
    return [
        Divergence(
            type=DivergenceType.ABATEMENT,
            field="abatements",
            title="Abatimento pode afetar base de honorarios",
            description=(
                "O documento relaciona seguro-desemprego/abatimentos e honorarios. Conferir se o "
                "desconto foi aplicado indevidamente sobre a base honoraria."
            ),
            sources=[calculation.source],
            values={calculation.source.value: calculation.abatements.normalized if calculation.abatements else None},
            favored_party="unknown",
            severity=Severity.WARNING,
            legal_basis="Regra interna parametrizavel conforme titulo executivo e decisao do caso.",
            evidence=[evidence] if evidence else [],
        )
    ]


def _first_available_evidence(calculation: ExtractedCalculation):
    for field in (
        calculation.correction_index,
        calculation.interest_rate,
        calculation.abatements,
        calculation.honoraries,
        calculation.total,
    ):
        if field and field.evidence:
            return field.evidence
    return None

