from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.planning.normative import (
    TETO_RGPS_2026,
    employee_progressive_contribution,
    individual_contribution,
    normative_references,
)
from app.planning.schemas import (
    AuditStep,
    DocumentInsight,
    DocumentType,
    Gender,
    InsuredProfile,
    PendingIssue,
    PendingSeverity,
    PlanningCase,
    RetirementScenario,
)


def build_planning_case(profile: InsuredProfile, documents: list[DocumentInsight]) -> PlanningCase:
    profile = enrich_profile(profile, documents)
    scenarios = calculate_rgps_scenarios(profile)
    pending_issues = detect_pending_issues(documents, scenarios)
    recommendation = build_recommendation(scenarios, pending_issues)
    report_markdown = render_report(profile, documents, scenarios, pending_issues, recommendation)
    return PlanningCase(
        profile=profile,
        documents=documents,
        normative_references=normative_references(),
        scenarios=scenarios,
        pending_issues=pending_issues,
        recommendation=recommendation,
        report_markdown=report_markdown,
    )


def enrich_profile(profile: InsuredProfile, documents: list[DocumentInsight]) -> InsuredProfile:
    update = {}
    if profile.name == "Segurado(a) em validacao":
        for document in documents:
            if document.extracted_name:
                update["name"] = document.extracted_name
                break
    if profile.birth_date == date(1973, 3, 5):
        for document in documents:
            if document.extracted_birth_date:
                update["birth_date"] = document.extracted_birth_date
                break
    return profile.model_copy(update=update) if update else profile


def calculate_rgps_scenarios(profile: InsuredProfile) -> list[RetirementScenario]:
    current_months = duration_to_months(
        profile.current_contribution_years,
        profile.current_contribution_months,
        profile.current_contribution_days,
    )
    converted_special_months = calculate_special_bonus(profile)
    base_months = current_months + converted_special_months
    monthly_contribution = monthly_future_contribution(profile)
    rules = [
        rule_points(profile),
        rule_progressive_age(profile),
        rule_age_transition(profile),
        rule_toll_50(profile, current_months),
        rule_toll_100(profile, current_months),
    ]
    scenarios: list[RetirementScenario] = []
    earliest_rmi: Decimal | None = None
    for rule in rules:
        scenario = project_rule(profile, rule, base_months, monthly_contribution)
        if scenario.status != "not_applicable" and earliest_rmi is None:
            earliest_rmi = scenario.estimated_rmi
        scenarios.append(scenario)

    available = [scenario for scenario in scenarios if scenario.status != "not_applicable"]
    available.sort(key=lambda item: (item.eligibility_date or date.max, -item.recommendation_score))
    unavailable = [scenario for scenario in scenarios if scenario.status == "not_applicable"]
    return available + unavailable


def rule_points(profile: InsuredProfile) -> dict[str, object]:
    return {
        "code": "art15_points",
        "title": "Aposentadoria por tempo de contribuicao - regra de pontos",
        "basis": "Art. 15 da EC 103/2019; pontuacao progressiva.",
        "required_months": 420 if profile.gender == Gender.MALE else 360,
        "required_age_months": 0,
        "required_points": Decimal("105") if profile.gender == Gender.MALE else Decimal("100"),
        "status": "projected",
    }


def rule_progressive_age(profile: InsuredProfile) -> dict[str, object]:
    return {
        "code": "art16_progressive_age",
        "title": "Aposentadoria por tempo de contribuicao - idade minima progressiva",
        "basis": "Art. 16 da EC 103/2019; em 2026: 64 anos e 6 meses homem, 59 anos e 6 meses mulher.",
        "required_months": 420 if profile.gender == Gender.MALE else 360,
        "required_age_months": 780 if profile.gender == Gender.MALE else 744,
        "required_points": None,
        "status": "projected",
    }


def rule_age_transition(profile: InsuredProfile) -> dict[str, object]:
    return {
        "code": "art18_age",
        "title": "Aposentadoria por idade - regra de transicao",
        "basis": "Art. 18 da EC 103/2019; idade de 65 anos homem ou 62 anos mulher e carencia minima.",
        "required_months": 180,
        "required_age_months": 780 if profile.gender == Gender.MALE else 744,
        "required_points": None,
        "status": "projected",
    }


def rule_toll_50(profile: InsuredProfile, current_months: int) -> dict[str, object]:
    months_since_reform = months_between(date(2019, 11, 13), profile.analysis_date)
    estimated_2019_months = max(0, current_months - months_since_reform)
    target = 420 if profile.gender == Gender.MALE else 360
    missing = target - estimated_2019_months
    status = "projected" if 0 < missing <= 24 else "not_applicable"
    return {
        "code": "art17_toll_50",
        "title": "Aposentadoria por tempo de contribuicao - pedagio de 50%",
        "basis": "Art. 17 da EC 103/2019; aplicavel a quem estava a ate 2 anos do tempo minimo em 13/11/2019.",
        "required_months": target + max(0, int(missing * 0.5)),
        "required_age_months": 0,
        "required_points": None,
        "status": status,
        "caveat": "Exige conferencia do tempo existente em 13/11/2019 e pode demandar fator previdenciario.",
    }


def rule_toll_100(profile: InsuredProfile, current_months: int) -> dict[str, object]:
    months_since_reform = months_between(date(2019, 11, 13), profile.analysis_date)
    estimated_2019_months = max(0, current_months - months_since_reform)
    target = 420 if profile.gender == Gender.MALE else 360
    missing = max(0, target - estimated_2019_months)
    return {
        "code": "art20_toll_100",
        "title": "Aposentadoria por tempo de contribuicao - pedagio de 100%",
        "basis": "Art. 20 da EC 103/2019; tempo minimo, idade minima e pedagio integral.",
        "required_months": target + missing,
        "required_age_months": 720 if profile.gender == Gender.MALE else 684,
        "required_points": None,
        "status": "projected",
    }


def project_rule(
    profile: InsuredProfile,
    rule: dict[str, object],
    base_months: int,
    monthly_contribution: Decimal,
) -> RetirementScenario:
    if rule["status"] == "not_applicable":
        return RetirementScenario(
            rule_code=str(rule["code"]),
            title=str(rule["title"]),
            status="not_applicable",
            eligibility_date=None,
            age_at_der="-",
            contribution_time=months_to_duration(base_months),
            estimated_rmi=Decimal("0.00"),
            coefficient=Decimal("0.00"),
            future_contribution_months=0,
            future_investment=Decimal("0.00"),
            roi_estimate=Decimal("0.00"),
            recommendation_score=Decimal("-9999"),
            legal_basis=str(rule["basis"]),
            caveats=[str(rule.get("caveat", "Regra nao aplicavel com os dados atuais."))],
        )

    required_months = int(rule["required_months"])
    required_age_months = int(rule["required_age_months"])
    required_points = rule["required_points"]
    future_months = 0
    while future_months <= 300:
        projected_date = add_months(profile.analysis_date, future_months)
        projected_contribution = base_months + future_months
        age_months = months_between(profile.birth_date, projected_date)
        points = Decimal(projected_contribution) / Decimal("12") + Decimal(age_months) / Decimal("12")
        if (
            projected_contribution >= required_months
            and age_months >= required_age_months
            and (required_points is None or points >= required_points)
        ):
            break
        future_months += 1

    eligibility_date = add_months(profile.analysis_date, future_months)
    total_months = base_months + future_months
    age_months = months_between(profile.birth_date, eligibility_date)
    points = Decimal(total_months) / Decimal("12") + Decimal(age_months) / Decimal("12")
    coefficient = benefit_coefficient(profile, total_months, str(rule["code"]))
    estimated_rmi = estimate_rmi(profile, coefficient)
    future_investment = (monthly_contribution * Decimal(future_months)).quantize(Decimal("0.01"))
    recovery_months = None
    reference_income = profile.target_monthly_income or min(profile.contribution_base, TETO_RGPS_2026)
    if estimated_rmi > reference_income and future_investment > 0:
        recovery_months = (future_investment / (estimated_rmi - reference_income)).quantize(Decimal("0.1"))
    roi = estimate_roi(estimated_rmi, future_investment, age_months)
    caveats = []
    if rule.get("caveat"):
        caveats.append(str(rule["caveat"]))
    if profile.special_months_before_2019:
        caveats.append("Tempo especial convertido somente como simulacao; exige PPP/LTCAT e revisao juridica.")
    return RetirementScenario(
        rule_code=str(rule["code"]),
        title=str(rule["title"]),
        status="available" if future_months == 0 else "projected",
        eligibility_date=eligibility_date,
        age_at_der=months_to_duration(age_months),
        contribution_time=months_to_duration(total_months),
        points=points.quantize(Decimal("0.01")),
        estimated_rmi=estimated_rmi,
        coefficient=coefficient,
        future_contribution_months=future_months,
        future_investment=future_investment,
        recovery_months=recovery_months,
        roi_estimate=roi,
        recommendation_score=(roi - future_investment).quantize(Decimal("0.01")),
        legal_basis=str(rule["basis"]),
        caveats=caveats,
        audit=[
            AuditStep(
                label="Tempo atual informado",
                value=months_to_duration(base_months),
                basis="Perfil do segurado acrescido da conversao especial simulada, quando preenchida.",
            ),
            AuditStep(
                label="Contribuicao futura mensal",
                value=f"R$ {monthly_contribution}",
                basis="Tabela INSS 2026, limitada ao teto do RGPS.",
            ),
            AuditStep(
                label="Coeficiente de calculo",
                value=f"{coefficient}%",
                basis="60% + 2 pontos por ano excedente, conforme regra geral da EC 103/2019.",
            ),
        ],
    )


def detect_pending_issues(
    documents: list[DocumentInsight], scenarios: list[RetirementScenario]
) -> list[PendingIssue]:
    issues: list[PendingIssue] = []
    types = {document.document_type for document in documents}
    if DocumentType.CNIS not in types:
        issues.append(
            PendingIssue(
                severity=PendingSeverity.CRITICAL,
                title="CNIS nao identificado",
                description="Suba o extrato CNIS completo para validar vinculos, remuneracoes, indicadores e carencia.",
                document_type=DocumentType.CNIS,
            )
        )
    if any("atividade especial" in document.detected_signals for document in documents) and DocumentType.PPP not in types:
        issues.append(
            PendingIssue(
                severity=PendingSeverity.WARNING,
                title="Atividade especial sem PPP identificado",
                description="Ha mencao a atividade especial, mas o sistema nao encontrou PPP para conferir agentes nocivos.",
                document_type=DocumentType.PPP,
            )
        )
    if any(scenario.rule_code == "art17_toll_50" and scenario.status != "not_applicable" for scenario in scenarios):
        issues.append(
            PendingIssue(
                severity=PendingSeverity.WARNING,
                title="Pedagio de 50% exige marco historico",
                description="Conferir tempo exato existente em 13/11/2019 e eventual fator previdenciario antes de recomendar.",
            )
        )
    for document in documents:
        if "lacunas" in document.detected_signals:
            issues.append(
                PendingIssue(
                    severity=PendingSeverity.WARNING,
                    title="Lacunas de contribuicao mencionadas",
                    description="Documento indica possiveis lacunas; validar recolhimento, indenizacao ou acerto de CNIS.",
                    document_type=document.document_type,
                    evidence=document.evidence[:2],
                )
            )
        if "remuneracao pos fim do vinculo" in document.detected_signals:
            issues.append(
                PendingIssue(
                    severity=PendingSeverity.INFO,
                    title="Indicador de remuneracao pos-fim",
                    description="Conferir se a remuneracao posterior ao fim do vinculo foi considerada ou deve ser ajustada.",
                    document_type=document.document_type,
                    evidence=document.evidence[:2],
                )
            )
    return issues


def build_recommendation(scenarios: list[RetirementScenario], issues: list[PendingIssue]) -> str:
    candidates = [scenario for scenario in scenarios if scenario.status != "not_applicable"]
    if not candidates:
        return "Nao ha cenario recomendavel com os dados atuais; complete o CNIS e revise o perfil."
    best = max(candidates, key=lambda item: item.recommendation_score)
    blocker = any(issue.severity == PendingSeverity.CRITICAL for issue in issues)
    prefix = "Preliminarmente, " if blocker else ""
    return (
        f"{prefix}o cenario mais vantajoso e {best.title}, com DER projetada em "
        f"{best.eligibility_date.strftime('%d/%m/%Y') if best.eligibility_date else 'a confirmar'} "
        f"e RMI estimada de R$ {best.estimated_rmi}. Revisao humana obrigatoria antes da entrega."
    )


def render_report(
    profile: InsuredProfile,
    documents: list[DocumentInsight],
    scenarios: list[RetirementScenario],
    issues: list[PendingIssue],
    recommendation: str,
) -> str:
    lines = [
        "# PARECER PREVIDENCIARIO",
        "",
        f"SEGURADO(A): {profile.name.upper()}",
        "BENEFICIOS: APOSENTADORIA POR TEMPO DE CONTRIBUICAO E/OU IDADE PELAS REGRAS DA EC 103/2019.",
        "",
        "## 1. Documentos analisados",
    ]
    if documents:
        for document in documents:
            lines.append(
                f"- {document.file_name}: {document.document_type.value.upper()} "
                f"({document.pages} pagina(s), confianca {document.confidence:.0%})."
            )
    else:
        lines.append("- Nenhum documento foi classificado; calculo baseado somente nos dados manuais.")

    lines.extend(["", "## 2. Caso concreto"])
    lines.append(
        f"Na data de analise ({profile.analysis_date.strftime('%d/%m/%Y')}), foi considerado o tempo "
        f"de contribuicao informado de {profile.current_contribution_years} anos, "
        f"{profile.current_contribution_months} meses e {profile.current_contribution_days} dias."
    )
    if profile.special_months_before_2019:
        lines.append(
            f"Foram simulados {profile.special_months_before_2019} meses especiais anteriores a 13/11/2019."
        )

    lines.extend(["", "## 3. Projecoes para concessao dos beneficios"])
    for scenario in scenarios:
        if scenario.status == "not_applicable":
            continue
        lines.extend(
            [
                f"### {scenario.title}",
                f"- DER projetada: {scenario.eligibility_date.strftime('%d/%m/%Y') if scenario.eligibility_date else 'a confirmar'}",
                f"- Tempo total: {scenario.contribution_time}",
                f"- Idade na DER: {scenario.age_at_der}",
                f"- Pontos: {scenario.points}",
                f"- RMI estimada: R$ {scenario.estimated_rmi}",
                f"- Investimento futuro: R$ {scenario.future_investment}",
                f"- Fundamento: {scenario.legal_basis}",
                "",
            ]
        )

    lines.extend(["## 4. Omissões e divergências"])
    if issues:
        for issue in issues:
            lines.append(f"- {issue.title}: {issue.description}")
    else:
        lines.append("- Nao foram identificadas pendencias impeditivas nesta leitura preliminar.")

    lines.extend(["", "## 5. Opiniao", recommendation])
    lines.append(
        "OBS.: Valores sujeitos a revisao conforme documentos originais, indices anuais, teto previdenciario e validacao juridica."
    )
    return "\n".join(lines)


def duration_to_months(years: int, months: int, days: int) -> int:
    return max(0, years * 12 + months + (1 if days >= 15 else 0))


def months_to_duration(months: int) -> str:
    years, remaining = divmod(max(0, months), 12)
    return f"{years} anos e {remaining} meses"


def months_between(start: date, end: date) -> int:
    months = (end.year - start.year) * 12 + (end.month - start.month)
    if end.day < start.day:
        months -= 1
    return max(0, months)


def add_months(value: date, months: int) -> date:
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, days_in_month(year, month))
    return date(year, month, day)


def days_in_month(year: int, month: int) -> int:
    if month == 2:
        return 29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28
    if month in {4, 6, 9, 11}:
        return 30
    return 31


def calculate_special_bonus(profile: InsuredProfile) -> int:
    if not profile.special_months_before_2019:
        return 0
    bonus = Decimal(profile.special_months_before_2019) * (profile.special_factor - Decimal("1"))
    return int(bonus)


def monthly_future_contribution(profile: InsuredProfile) -> Decimal:
    if profile.contributor_type == "individual":
        return individual_contribution(profile.contribution_base)
    return employee_progressive_contribution(profile.contribution_base)


def benefit_coefficient(profile: InsuredProfile, total_months: int, rule_code: str) -> Decimal:
    years = Decimal(total_months) / Decimal("12")
    threshold = Decimal("20") if profile.gender == Gender.MALE else Decimal("15")
    coefficient = Decimal("60") + max(Decimal("0"), years - threshold) * Decimal("2")
    if rule_code == "art20_toll_100":
        coefficient = max(coefficient, Decimal("100"))
    return min(coefficient, Decimal("120")).quantize(Decimal("0.01"))


def estimate_rmi(profile: InsuredProfile, coefficient: Decimal) -> Decimal:
    base = min(max(profile.contribution_base, Decimal("0")), TETO_RGPS_2026)
    return min(base * coefficient / Decimal("100"), TETO_RGPS_2026).quantize(Decimal("0.01"))


def estimate_roi(estimated_rmi: Decimal, future_investment: Decimal, age_months: int) -> Decimal:
    remaining_months_to_82 = max(0, 82 * 12 - age_months)
    gross = estimated_rmi * Decimal(remaining_months_to_82 + remaining_months_to_82 // 12)
    return (gross - future_investment).quantize(Decimal("0.01"))
