from datetime import date
from decimal import Decimal

from app.planning.engine import build_planning_case
from app.planning.normative import employee_progressive_contribution
from app.planning.schemas import DocumentInsight, DocumentType, Gender, InsuredProfile


def test_employee_progressive_contribution_uses_2026_ceiling():
    assert employee_progressive_contribution(Decimal("8475.55")) == Decimal("988.09")
    assert employee_progressive_contribution(Decimal("10000.00")) == Decimal("988.09")


def test_builds_rgps_scenarios_and_critical_cnis_pending_issue():
    profile = InsuredProfile(
        name="Joao Previdenciario",
        gender=Gender.MALE,
        birth_date=date(1970, 1, 15),
        analysis_date=date(2026, 6, 4),
        current_contribution_years=34,
        current_contribution_months=0,
        current_contribution_days=0,
        contribution_base=Decimal("8475.55"),
    )

    planning = build_planning_case(profile, documents=[])

    assert planning.scenarios
    assert planning.scenarios[0].eligibility_date is not None
    assert planning.scenarios[0].estimated_rmi > Decimal("0")
    assert planning.scenarios[0].estimated_rmi <= Decimal("8475.55")
    assert any(issue.title == "CNIS nao identificado" for issue in planning.pending_issues)
    assert "PARECER PREVIDENCIARIO" in planning.report_markdown


def test_enriches_profile_from_document_name():
    profile = InsuredProfile(name="Segurado(a) em validacao")
    document = DocumentInsight(
        file_name="parecer.pdf",
        document_type=DocumentType.REPORT,
        extracted_name="Maria Clara Previdenciaria",
    )

    planning = build_planning_case(profile, [document])

    assert planning.profile.name == "Maria Clara Previdenciaria"
