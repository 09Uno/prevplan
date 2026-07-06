from __future__ import annotations

import os

from app.domain.schemas import ComparisonResult, DraftResult


def build_template_draft(comparison: ComparisonResult, target: str = "both") -> DraftResult:
    process = comparison.process_number or "[numero do processo]"
    relevant = comparison.divergences
    lines = [
        "EXCELENTISSIMO(A) SENHOR(A) JUIZ(A) FEDERAL DA VARA PREVIDENCIARIA",
        "",
        f"Processo n. {process}",
        "",
        "A parte exequente, por seus advogados, vem, respeitosamente, manifestar discordancia",
        "em relacao aos calculos apresentados, pelas razoes tecnicas a seguir expostas.",
        "",
        "1. Sintese das divergencias apuradas",
    ]
    if not relevant:
        lines.append("Nao foram identificadas divergencias materiais pelo comparador deterministico.")
    for index, divergence in enumerate(relevant, start=1):
        lines.extend(
            [
                "",
                f"1.{index}. {divergence.title}",
                divergence.description,
            ]
        )
        if divergence.legal_basis:
            lines.append(f"Fundamento/criterio de conferencia: {divergence.legal_basis}")
        if divergence.magnitude_money is not None:
            lines.append(
                f"Diferenca estimada: R$ {divergence.magnitude_money} "
                f"({divergence.magnitude_percent}% sobre a maior base comparada)."
            )

    lines.extend(
        [
            "",
            "2. Pedido",
            "Diante do exposto, requer seja afastado o criterio divergente apontado, com a",
            "adequacao dos calculos aos parametros do titulo executivo e aos criterios legais",
            "aplicaveis, remetendo-se os autos a nova conferencia, se necessario.",
            "",
            "Termos em que, pede deferimento.",
        ]
    )
    return DraftResult(
        mode="template",
        text="\n".join(lines),
        warnings=[
            "Minuta deterministica preliminar. Revisar fatos, IDs processuais e fundamentos antes do protocolo."
        ],
    )


async def build_ai_draft(comparison: ComparisonResult, target: str = "both") -> DraftResult:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        result = build_template_draft(comparison, target)
        result.warnings.append("ANTHROPIC_API_KEY ausente; foi gerada minuta por template.")
        return result

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=api_key)
    prompt = (
        "Voce redige minutas previdenciarias para cumprimento de sentenca. "
        "Nao recalcule valores, nao crie divergencias e nao altere numeros. "
        "Use apenas o JSON estruturado abaixo como fonte.\n\n"
        f"{comparison.model_dump_json(indent=2)}"
    )
    response = await client.messages.create(
        model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"),
        max_tokens=3000,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    text = "\n".join(block.text for block in response.content if getattr(block, "type", "") == "text")
    return DraftResult(mode="anthropic", text=text, model=response.model)

