from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.planning.schemas import NormativeReference

SALARIO_MINIMO_2026 = Decimal("1621.00")
TETO_RGPS_2026 = Decimal("8475.55")

EMPLOYEE_BRACKETS_2026 = [
    (Decimal("1621.00"), Decimal("0.075")),
    (Decimal("2902.84"), Decimal("0.09")),
    (Decimal("4354.27"), Decimal("0.12")),
    (TETO_RGPS_2026, Decimal("0.14")),
]


def normative_references() -> list[NormativeReference]:
    return [
        NormativeReference(
            code="EC103-2019",
            title="Emenda Constitucional 103/2019",
            effective_from=date(2019, 11, 13),
            summary="Reforma da Previdencia, regras permanentes e transicoes do RGPS.",
            source_url="https://www.planalto.gov.br/ccivil_03/constituicao/emendas/emc/emc103.htm",
            tags=["rgps", "transicao", "calculo"],
        ),
        NormativeReference(
            code="INSS-TABELA-2026",
            title="Tabela de contribuicao mensal INSS 2026",
            effective_from=date(2026, 1, 1),
            summary="Piso de R$ 1.621,00, teto de R$ 8.475,55 e aliquotas progressivas.",
            source_url="https://www.gov.br/inss/pt-br/direitos-e-deveres/inscricao-e-contribuicao/tabela-de-contribuicao-mensal",
            tags=["rgps", "contribuicao", "2026"],
        ),
        NormativeReference(
            code="IN128-2022",
            title="Instrucao Normativa PRES/INSS 128/2022",
            effective_from=date(2022, 3, 28),
            summary="Procedimentos de reconhecimento, manutencao, revisao e acerto de CNIS.",
            source_url="https://www.gov.br/inss/pt-br/centrais-de-conteudo/legislacao/instrucao-normativa/2022",
            tags=["cnis", "procedimento", "documentos"],
        ),
        NormativeReference(
            code="LC142-2013",
            title="Lei Complementar 142/2013",
            effective_from=date(2013, 5, 8),
            summary="Aposentadoria da pessoa com deficiencia no RGPS.",
            source_url="https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp142.htm",
            tags=["pcd", "fase-2"],
        ),
        NormativeReference(
            code="STF-ADI6309",
            title="ADI 6309/STF",
            effective_from=date(2026, 6, 3),
            summary="Invalidou a idade minima na aposentadoria especial; calculo e vedacao de conversao posterior a EC 103 permanecem como pontos de revisao.",
            source_url="https://noticias.stf.jus.br/postsnoticias/stf-invalida-idade-minima-para-aposentadoria-especial-em-atividades-insalubres/",
            tags=["especial", "jurisprudencia", "alerta"],
        ),
        NormativeReference(
            code="STJ-T1307",
            title="Tema Repetitivo 1.307/STJ",
            effective_from=date(2026, 6, 3),
            summary="Admite especialidade por penosidade para motorista/cobrador, mediante pericia individualizada.",
            source_url="https://www.stj.jus.br/sites/portalp/Paginas/Comunicacao/Noticias/2026/03062026-Motoristas-e-cobradores-STJ-permite-reconhecimento-de-aposentadoria-especial-por-trabalho-penoso.aspx",
            tags=["especial", "penosidade", "jurisprudencia"],
        ),
    ]


def employee_progressive_contribution(base: Decimal) -> Decimal:
    capped = min(max(base, Decimal("0")), TETO_RGPS_2026)
    previous = Decimal("0")
    total = Decimal("0")
    for limit, rate in EMPLOYEE_BRACKETS_2026:
        taxable = min(capped, limit) - previous
        if taxable > 0:
            total += taxable * rate
        previous = limit
        if capped <= limit:
            break
    return total.quantize(Decimal("0.01"))


def individual_contribution(base: Decimal) -> Decimal:
    return (min(max(base, SALARIO_MINIMO_2026), TETO_RGPS_2026) * Decimal("0.20")).quantize(
        Decimal("0.01")
    )
