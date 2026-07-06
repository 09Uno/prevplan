from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date
from decimal import Decimal, InvalidOperation

from app.domain.schemas import CalculationSource, EvidenceRef, ExtractedCalculation, ExtractedValue
from app.ingestion.classifier import classify_source
from app.ingestion.types import ParsedDocument, PageText

MONEY_RE = re.compile(r"R\$\s*([0-9]{1,3}(?:\.[0-9]{3})*,[0-9]{2}|[0-9]+,[0-9]{2})")
DATE_RE = re.compile(r"(\d{2}/\d{2}/\d{4}|\d{2}/\d{4})")
PROCESS_RE = re.compile(r"\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b")


def strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn"
    )


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", strip_accents(value).lower()).strip()


def parse_brl(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.replace(".", "").replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def parse_date(raw: str) -> str | None:
    if not raw:
        return None
    if re.fullmatch(r"\d{2}/\d{4}", raw):
        return raw
    try:
        day, month, year = [int(part) for part in raw.split("/")]
        return date(year, month, day).isoformat()
    except ValueError:
        return raw


def extract_calculation(document: ParsedDocument, source: CalculationSource | None = None) -> ExtractedCalculation:
    full_text = document.full_text
    resolved_source = source or classify_source(document.file_name, full_text)
    calc = ExtractedCalculation(
        source=resolved_source,
        file_name=document.file_name,
        raw_text_sha256=hashlib.sha256(full_text.encode("utf-8", errors="ignore")).hexdigest(),
    )

    calc.process_number = find_regex_value(document, PROCESS_RE, "process_number", confidence=0.95)
    calc.beneficiary_name = find_beneficiary_name(document)
    calc.rmi = find_money_near(document, ["rmi", "renda mensal inicial"], "rmi")
    calc.dib = find_date_near(document, ["dib", "inicio do beneficio", "início do benefício"], "dib")
    calc.dip = find_date_near(document, ["dip", "inicio do pagamento", "início do pagamento"], "dip")
    calc.calculation_until = find_date_near(
        document,
        ["atualizados para", "atualizado para", "calculo ate", "cálculo até"],
        "calculation_until",
    )
    calc.correction_index = find_index(document)
    calc.interest_rate = find_interest(document)
    calc.principal = find_money_near(document, ["principal", "principal corrigido"], "principal")
    calc.arrears = find_money_near(document, ["atrasados", "resultado atrasados"], "arrears")
    calc.abatements = find_money_near(
        document,
        ["abatimento", "abatimentos", "desconto", "descontos", "deducao", "dedução"],
        "abatements",
    )
    calc.honoraries = find_money_near(
        document, ["honorarios", "honorários", "verba honoraria", "verba honorária"], "honoraries"
    )
    calc.total = find_money_near(
        document,
        ["valor total", "total:", "total apurado", "total atualizado", "totalizando"],
        "total",
    )
    calc.flags = detect_flags(full_text)
    return calc


def line_window(page: PageText, target_index: int, radius: int = 2) -> str:
    lines = [line.strip() for line in page.text.splitlines() if line.strip()]
    start = max(0, target_index - radius)
    end = min(len(lines), target_index + radius + 1)
    return " | ".join(lines[start:end])


def make_value(
    raw: str,
    normalized: object,
    document: ParsedDocument,
    page: PageText,
    snippet: str,
    confidence: float,
) -> ExtractedValue:
    return ExtractedValue(
        value=raw,
        normalized=normalized,
        confidence=confidence,
        evidence=EvidenceRef(file_name=document.file_name, page=page.page_number, text=snippet[:1000]),
    )


def find_regex_value(
    document: ParsedDocument, pattern: re.Pattern[str], field_name: str, confidence: float
) -> ExtractedValue | None:
    for page in document.pages:
        match = pattern.search(page.text)
        if match:
            raw = match.group(0)
            return make_value(raw, raw, document, page, raw, confidence)
    return None


def find_beneficiary_name(document: ParsedDocument) -> ExtractedValue | None:
    patterns = [
        re.compile(r"EXEQUENTE:\s*([A-ZÀ-Ú][A-ZÀ-Ú\s]{5,})"),
        re.compile(r"EXEQUENTE\(S\):\s*([A-ZÀ-Ú][A-ZÀ-Ú\s]{5,})"),
        re.compile(r"Autor(?:a)?:\s*([A-ZÀ-Ú][A-ZÀ-Ú\s]{5,})", re.IGNORECASE),
    ]
    for page in document.pages:
        for pattern in patterns:
            match = pattern.search(page.text)
            if match:
                raw = re.sub(r"\s+", " ", match.group(1)).strip()
                return make_value(raw, raw.title(), document, page, match.group(0), 0.72)
    return None


def find_money_near(document: ParsedDocument, labels: list[str], field_name: str) -> ExtractedValue | None:
    normalized_labels = [normalize_text(label) for label in labels]
    fallback: ExtractedValue | None = None
    for page in document.pages:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            norm_line = normalize_text(line)
            if not any(label in norm_line for label in normalized_labels):
                continue
            snippet = " | ".join(lines[idx : min(len(lines), idx + 4)])
            match = MONEY_RE.search(snippet)
            if not match and idx + 1 < len(lines):
                match = MONEY_RE.search(lines[idx + 1])
            if match:
                raw = f"R$ {match.group(1)}"
                return make_value(raw, parse_brl(match.group(1)), document, page, snippet, 0.78)
            if fallback is None:
                nearby_money = MONEY_RE.search(line_window(page, idx, radius=3))
                if nearby_money:
                    raw = f"R$ {nearby_money.group(1)}"
                    fallback = make_value(
                        raw,
                        parse_brl(nearby_money.group(1)),
                        document,
                        page,
                        line_window(page, idx, radius=3),
                        0.54,
                    )
    return fallback


def find_date_near(document: ParsedDocument, labels: list[str], field_name: str) -> ExtractedValue | None:
    normalized_labels = [normalize_text(label) for label in labels]
    for page in document.pages:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            norm_line = normalize_text(line)
            if not any(label in norm_line for label in normalized_labels):
                continue
            snippet = " | ".join(lines[idx : min(len(lines), idx + 4)])
            match = DATE_RE.search(snippet)
            if match:
                raw = match.group(1)
                return make_value(raw, parse_date(raw), document, page, snippet, 0.76)
    return None


def find_index(document: ParsedDocument) -> ExtractedValue | None:
    index_patterns = [
        ("IPCA-E", re.compile(r"\bIPCA-?E\b", re.IGNORECASE)),
        ("INPC", re.compile(r"\bINPC\b", re.IGNORECASE)),
        ("SELIC", re.compile(r"\bSELIC\b", re.IGNORECASE)),
        ("TR", re.compile(r"\bTR\b|taxa referencial", re.IGNORECASE)),
    ]
    for page in document.pages:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            norm_line = normalize_text(line)
            if "correcao monetaria" not in norm_line and "indice" not in norm_line and "selic" not in norm_line:
                continue
            snippet = line_window(page, idx, radius=2)
            found = [name for name, pattern in index_patterns if pattern.search(snippet)]
            if found:
                value = " + ".join(dict.fromkeys(found))
                return make_value(value, value, document, page, snippet, 0.74)
    return None


def find_interest(document: ParsedDocument) -> ExtractedValue | None:
    rate_re = re.compile(r"(\d{1,3}(?:[,.]\d{1,4})?)\s*%\s*(?:ao mes|ao mês|a\.m\.|ate|até)?", re.I)
    for page in document.pages:
        lines = [line.strip() for line in page.text.splitlines() if line.strip()]
        for idx, line in enumerate(lines):
            if "juros" not in normalize_text(line):
                continue
            snippet = line_window(page, idx, radius=2)
            match = rate_re.search(snippet)
            if match:
                raw = f"{match.group(1)}%"
                normalized = Decimal(match.group(1).replace(",", "."))
                return make_value(raw, normalized, document, page, snippet, 0.7)
            if "selic" in normalize_text(snippet):
                return make_value("SELIC", "SELIC", document, page, snippet, 0.66)
    return None


def detect_flags(text: str) -> list[str]:
    norm = normalize_text(text)
    flags: list[str] = []
    if "ec 113" in norm or "emenda constitucional 113" in norm:
        flags.append("mentions_ec_113_2021")
    if "selic" in norm:
        flags.append("mentions_selic")
    if "ipca-e" in text.lower() or "ipca e" in norm:
        flags.append("mentions_ipca_e")
    if "juros negativos" in norm:
        flags.append("mentions_negative_interest")
    if "seguro-desemprego" in norm or "seguro desemprego" in norm:
        flags.append("mentions_unemployment_insurance_offset")
    if "taxa referencial" in norm or re.search(r"\bTR\b", text):
        flags.append("mentions_tr")
    if "honor" in norm:
        flags.append("mentions_honoraries")
    return flags

