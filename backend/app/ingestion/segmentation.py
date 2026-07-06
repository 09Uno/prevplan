from __future__ import annotations

import re
import unicodedata

from app.domain.schemas import CalculationSource
from app.ingestion.classifier import classify_source
from app.ingestion.types import PageText, ParsedDocument

PJE_DOC_START_RE = re.compile(r"\bNum\.\s*(\d+)\s*-\s*P[áa]g\.\s*1\b", re.IGNORECASE)
PJE_DOC_ID_RE = re.compile(r"\bNum\.\s*(\d+)\s*-\s*P[áa]g\.", re.IGNORECASE)

CALCULATION_TERMS = [
    "resumo do calculo",
    "sistema de calculo",
    "demonstrativo discriminado",
    "memoria de calculo",
    "memoria discriminada",
    "planilha de calculo",
    "calculo de liquidacao",
    "resultado atrasados",
    "resultado honorarios",
    "total principal corrigido",
    "total atualizado",
    "rmi jud",
    "inicio do beneficio",
    "valor dos juros",
    "honorarios sobre a base",
]

PIECE_TERMS = [
    "impugnacao a execucao",
    "impugnacao a liquidacao",
    "discordancia a impugnacao",
    "excesso de execucao",
    "discordancia acerca do calculo",
    "discordancia aos calculos",
    "calculo apresentado pelo inss",
    "calculos apresentados pela contadoria",
    "parecer contabil",
    "contadoria judicial",
]

MONEY_MARKER_RE = re.compile(r"R\$\s*[0-9]", re.IGNORECASE)
PROCEDURAL_TERMS = [
    "d e c i s a o",
    "despacho",
    "certidao",
    "ato ordinatorio",
    "mandado",
    "intimacao",
    "prevjud",
    "notificacao de envio de intimacao judicial",
    "servico solicitado",
    "topico sintese",
    "ordem judicial",
]
CORE_FIELD_TERMS = [
    "rmi",
    "dib",
    "juros",
    "honorarios",
    "correcao monetaria",
    "total atualizado",
    "atrasados",
    "abatimento",
    "desconto",
]


def split_process_document(document: ParsedDocument) -> list[ParsedDocument]:
    """Divide um PDF completo do PJe em documentos internos por marcador de pagina 1.

    O PJe exporta processos como um PDF unico em que cada documento costuma iniciar com
    "Num. <id> - Pag. 1". Quando esse padrao nao existe, a funcao devolve o documento
    original para preservar o comportamento antigo.
    """

    starts: list[int] = []
    doc_ids: dict[int, str] = {}
    for index, page in enumerate(document.pages):
        match = PJE_DOC_START_RE.search(page.text)
        if match:
            starts.append(index)
            doc_ids[index] = match.group(1)

    if len(starts) < 2:
        return [document]

    segments: list[ParsedDocument] = []
    if starts[0] > 0:
        segments.append(
            ParsedDocument(
                file_name=f"{document.file_name} :: indice pp.1-{starts[0]}",
                pages=document.pages[: starts[0]],
                mime_type=document.mime_type,
            )
        )

    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(document.pages)
        segment_pages = document.pages[start:end]
        doc_id = doc_ids.get(start) or infer_document_id(segment_pages)
        page_label = f"pp.{segment_pages[0].page_number}-{segment_pages[-1].page_number}"
        suffix = f"doc {doc_id} {page_label}" if doc_id else page_label
        segments.append(
            ParsedDocument(
                file_name=f"{document.file_name} :: {suffix}",
                pages=segment_pages,
                mime_type=document.mime_type,
            )
        )
    return segments


def is_process_bundle(document: ParsedDocument) -> bool:
    starts = sum(1 for page in document.pages if PJE_DOC_START_RE.search(page.text))
    return starts >= 2


def is_relevant_for_calculation(document: ParsedDocument) -> bool:
    if " :: indice " in normalize(document.file_name):
        return False
    text = normalize(document.full_text[:20000])
    has_calculation_term = any(term in text for term in CALCULATION_TERMS)
    has_piece_term = any(term in text for term in PIECE_TERMS)
    core_hits = sum(1 for term in CORE_FIELD_TERMS if term in text)
    has_money = bool(MONEY_MARKER_RE.search(text))
    is_procedural = any(term in text for term in PROCEDURAL_TERMS)

    if is_procedural and not has_money and not has_piece_term:
        return False
    if has_calculation_term or has_piece_term:
        return True
    return has_money and core_hits >= 2


def is_calculation_attachment(document: ParsedDocument) -> bool:
    text = normalize(document.full_text[:12000])
    return any(term in text for term in CALCULATION_TERMS)


def resolve_segment_sources(
    segments: list[ParsedDocument], explicit_source: CalculationSource | None = None
) -> list[tuple[ParsedDocument, CalculationSource | None]]:
    resolved: list[tuple[ParsedDocument, CalculationSource | None]] = []
    context_source = explicit_source
    is_bundle = len(segments) > 1

    for segment in segments:
        classified = explicit_source or classify_source(segment.file_name, segment.full_text)
        segment_source: CalculationSource | None = classified

        if classified == CalculationSource.UNKNOWN and is_calculation_attachment(segment):
            segment_source = context_source

        if classified != CalculationSource.UNKNOWN:
            context_source = classified

        if is_relevant_for_calculation(segment) and (
            segment_source != CalculationSource.UNKNOWN or not is_bundle
        ):
            resolved.append((segment, segment_source))

    if not resolved and len(segments) == 1:
        return [(segments[0], explicit_source)]
    return resolved


def infer_document_id(pages: list[PageText]) -> str | None:
    for page in pages[:2]:
        match = PJE_DOC_ID_RE.search(page.text)
        if match:
            return match.group(1)
    return None


def normalize(value: str) -> str:
    without_accents = "".join(
        c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents.lower()).strip()
