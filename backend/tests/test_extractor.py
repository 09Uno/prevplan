from decimal import Decimal

from app.domain.schemas import CalculationSource
from app.ingestion.extractor import extract_calculation
from app.ingestion.types import PageText, ParsedDocument


def test_extracts_core_fields_from_text():
    document = ParsedDocument(
        file_name="calculo.pdf",
        pages=[
            PageText(
                page_number=1,
                text="""
                Numero: 5004689-28.2018.4.03.6183
                Início do Benefício (DIB): 17/09/2015
                RMI Jud....: R$ 1.431,17
                Correção Monetária: IPCA-E
                Valor dos Juros: 0,5% ao mês
                Total Atualizado: R$ 92.641,46
                Honorários Sobre a Base de Cálculo Atualizada: R$ 10.999,37
                """,
            )
        ],
    )

    calculation = extract_calculation(document, CalculationSource.OFFICE)

    assert calculation.process_number.normalized == "5004689-28.2018.4.03.6183"
    assert calculation.dib.normalized == "2015-09-17"
    assert calculation.rmi.normalized == Decimal("1431.17")
    assert calculation.correction_index.normalized == "IPCA-E"
    assert calculation.total.normalized == Decimal("92641.46")

