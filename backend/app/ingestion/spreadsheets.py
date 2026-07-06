from __future__ import annotations

from io import BytesIO

import pandas as pd

from app.ingestion.types import PageText, ParsedDocument


def parse_spreadsheet_bytes(file_name: str, payload: bytes) -> ParsedDocument:
    """Normaliza XLSX/CSV em texto tabular para a primeira camada de extracao.

    A evolucao natural deste modulo e mapear celulas e ranges como evidencia precisa.
    Por ora, cada aba vira um bloco textual com coordenadas de linha/coluna preservadas.
    """

    if file_name.lower().endswith(".csv"):
        frames = {"csv": pd.read_csv(BytesIO(payload))}
    else:
        frames = pd.read_excel(BytesIO(payload), sheet_name=None)

    pages: list[PageText] = []
    for index, (sheet_name, frame) in enumerate(frames.items(), start=1):
        text = f"Sheet: {sheet_name}\n{frame.to_csv(index=False)}"
        pages.append(PageText(page_number=index, text=text))
    return ParsedDocument(file_name=file_name, pages=pages, mime_type="application/vnd.ms-excel")

