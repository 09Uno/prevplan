from app.domain.schemas import CalculationSource
from app.ingestion.segmentation import resolve_segment_sources, split_process_document
from app.ingestion.types import PageText, ParsedDocument


def test_splits_pje_bundle_and_inherits_source_for_calculation_attachment():
    document = ParsedDocument(
        file_name="processo-completo.pdf",
        pages=[
            PageText(1, "Indice do processo"),
            PageText(
                2,
                """
                Num. 111 - Pág. 1
                IMPUGNANTE(S): INSTITUTO NACIONAL DO SEGURO SOCIAL - INSS
                IMPUGNAÇÃO À EXECUÇÃO
                ( X ) utilizou outra RMI, qual seja R$ 1.420,55
                """,
            ),
            PageText(
                3,
                """
                Num. 112 - Pág. 1
                RESUMO DO CÁLCULO
                RMI Jud....: R$ 1.420,55
                Total Atualizado: R$ 80.000,00
                """,
            ),
            PageText(
                4,
                """
                Num. 113 - Pág. 1
                D E C I S Ã O
                Defiro prazo.
                """,
            ),
        ],
    )

    segments = split_process_document(document)
    resolved = resolve_segment_sources(segments)

    assert len(segments) == 4
    assert len(resolved) == 2
    assert resolved[0][1] == CalculationSource.INSS
    assert resolved[1][1] == CalculationSource.INSS
    assert "doc 112" in resolved[1][0].file_name


def test_skips_unclassified_procedural_segments_in_bundle():
    document = ParsedDocument(
        file_name="processo-completo.pdf",
        pages=[
            PageText(1, "Indice do processo"),
            PageText(
                2,
                """
                Num. 201 - Pág. 1
                PREVJUD
                Tópico Síntese
                Renda Mensal Inicial
                DIP - Data de Início do Pagamento
                """,
            ),
            PageText(
                3,
                """
                Num. 202 - Pág. 1
                Assinado eletronicamente por: BRENO BORGES DE CAMARGO
                manifestar-se em discordância a impugnação do executado
                RMI de R$ 4.817,89
                """,
            ),
        ],
    )

    resolved = resolve_segment_sources(split_process_document(document))

    assert len(resolved) == 1
    assert resolved[0][1] == CalculationSource.OFFICE
