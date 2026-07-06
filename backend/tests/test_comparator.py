from decimal import Decimal

from app.comparison.comparator import compare_calculations
from app.domain.schemas import CalculationSource, ExtractedCalculation, ExtractedValue


def value(item):
    return ExtractedValue(value=str(item), normalized=item, confidence=1)


def test_compares_rmi_and_total():
    office = ExtractedCalculation(
        source=CalculationSource.OFFICE,
        file_name="office.pdf",
        rmi=value(Decimal("1431.17")),
        total=value(Decimal("100000.00")),
    )
    inss = ExtractedCalculation(
        source=CalculationSource.INSS,
        file_name="inss.pdf",
        rmi=value(Decimal("1420.55")),
        total=value(Decimal("80000.00")),
    )

    result = compare_calculations([office, inss])

    assert result.summary["divergence_count"] == 2
    assert {item.field for item in result.divergences} == {"rmi", "total"}


def test_does_not_compare_unknown_or_same_source():
    office_a = ExtractedCalculation(
        source=CalculationSource.OFFICE,
        file_name="office-a.pdf",
        total=value(Decimal("100000.00")),
    )
    office_b = ExtractedCalculation(
        source=CalculationSource.OFFICE,
        file_name="office-b.pdf",
        total=value(Decimal("90000.00")),
    )
    unknown = ExtractedCalculation(
        source=CalculationSource.UNKNOWN,
        file_name="unknown.pdf",
        total=value(Decimal("1.00")),
    )

    result = compare_calculations([office_a, office_b, unknown])

    assert result.divergences == []
    assert result.summary["sources"] == ["office"]
