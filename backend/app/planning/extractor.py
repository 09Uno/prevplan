from __future__ import annotations

import re
import unicodedata
from datetime import date

from app.domain.schemas import EvidenceRef
from app.ingestion.types import ParsedDocument
from app.planning.schemas import DocumentInsight, DocumentType


def strip_accents(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFD", value) if unicodedata.category(char) != "Mn"
    )


def normalize(value: str) -> str:
    return re.sub(r"\s+", " ", strip_accents(value).lower()).strip()


def analyze_document(document: ParsedDocument) -> DocumentInsight:
    text = document.full_text
    norm = normalize(text)
    doc_type = classify_document(norm, document.file_name)
    signals = detect_signals(norm, text)
    evidence = collect_evidence(document, signals)
    name = extract_name(document)
    birth = extract_birth_date(document)
    duration = extract_duration_text(text)
    confidence = min(0.95, 0.35 + (0.12 * len(signals)) + (0.12 if name else 0))
    return DocumentInsight(
        file_name=document.file_name,
        document_type=doc_type,
        pages=max(1, len(document.pages)),
        confidence=round(confidence, 2),
        extracted_name=name,
        extracted_birth_date=birth,
        contribution_duration_text=duration,
        detected_signals=signals,
        evidence=evidence,
    )


def classify_document(norm: str, file_name: str) -> DocumentType:
    lower_name = normalize(file_name)
    if "cnis" in norm or "extrato previdenciario" in norm or "cadastro nacional" in norm:
        return DocumentType.CNIS
    if "perfil profissiografico previdenciario" in norm or re.search(r"\bppp\b", norm):
        return DocumentType.PPP
    if "ltcat" in norm or "laudo tecnico" in norm:
        return DocumentType.LTCAT
    if "carteira de trabalho" in norm or "ctps" in norm:
        return DocumentType.CTPS
    if "certidao de tempo de contribuicao" in norm or " ctc " in f" {norm} ":
        return DocumentType.CTC
    if "parecer previdenciario" in norm or "planejamento previdenciario" in norm:
        return DocumentType.REPORT
    if any(token in lower_name for token in ["rg", "cnh", "cpf", "identidade"]):
        return DocumentType.ID
    return DocumentType.OTHER


def detect_signals(norm: str, original: str) -> list[str]:
    checks = [
        ("rgps", "RGPS"),
        ("rpps", "RPPS"),
        ("ec 103", "EC 103/2019"),
        ("atividade especial", "atividade especial"),
        ("agente nocivo", "agente nocivo"),
        ("ruido", "ruido"),
        ("quimic", "agentes quimicos"),
        ("deficiencia", "PCD"),
        ("contribuinte individual", "contribuinte individual"),
        ("indenizacao", "indenizacao/debito"),
        ("lacuna", "lacunas"),
        ("remuneracao pos fim", "remuneracao pos fim do vinculo"),
        ("tesouro direto", "Tesouro Direto"),
        ("acordo internacional", "acordo internacional"),
    ]
    signals = [label for token, label in checks if token in norm]
    if re.search(r"\bPPP\b", original):
        signals.append("PPP")
    return list(dict.fromkeys(signals))


def collect_evidence(document: ParsedDocument, signals: list[str]) -> list[EvidenceRef]:
    evidence: list[EvidenceRef] = []
    for signal in signals[:6]:
        signal_norm = normalize(signal)
        for page in document.pages:
            lines = [line.strip() for line in page.text.splitlines() if line.strip()]
            for idx, line in enumerate(lines):
                if signal_norm in normalize(line):
                    snippet = " | ".join(lines[max(0, idx - 1) : idx + 2])
                    evidence.append(
                        EvidenceRef(
                            file_name=document.file_name,
                            page=page.page_number,
                            text=snippet[:700],
                        )
                    )
                    break
            if evidence and evidence[-1].text:
                break
    return evidence


def extract_name(document: ParsedDocument) -> str | None:
    patterns = [
        re.compile(r"SEGURAD[OA]:\s*([A-ZÀ-Ú][A-ZÀ-Ú ]{5,})"),
        re.compile(r"SERVIDOR[AA]?/SEGURAD[OA]:\s*([A-ZÀ-Ú][A-ZÀ-Ú ]{5,})"),
        re.compile(r"SERVIDOR[AA]?:\s*([A-ZÀ-Ú][A-ZÀ-Ú ]{5,})"),
        re.compile(r"NOME:\s*([A-ZÀ-Ú][A-ZÀ-Ú ]{5,})"),
    ]
    for page in document.pages[:3]:
        text = "\n".join(line.strip() for line in page.text.splitlines())
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return re.sub(r"\s+", " ", match.group(1)).strip().title()
    return None


def extract_birth_date(document: ParsedDocument) -> date | None:
    pattern = re.compile(
        r"(?:nascimento|data de nascimento|nascid[oa] em)\D{0,30}(\d{2}/\d{2}/\d{4})",
        re.IGNORECASE,
    )
    for page in document.pages:
        match = pattern.search(page.text)
        if match:
            day, month, year = [int(part) for part in match.group(1).split("/")]
            try:
                return date(year, month, day)
            except ValueError:
                return None
    return None


def extract_duration_text(text: str) -> str | None:
    matches = re.findall(r"\d{1,2}\s+anos?,\s*\d{1,2}\s+mes(?:es)?(?:\s+e\s+\d{1,2}\s+dias?)?", text)
    if matches:
        return matches[-1]
    return None
