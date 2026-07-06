from __future__ import annotations

import fitz

from app.ingestion.types import PageText, ParsedDocument


def parse_pdf_bytes(file_name: str, payload: bytes) -> ParsedDocument:
    """Extrai texto por pagina usando PyMuPDF.

    A extracao e deliberadamente simples nesta camada. Tabelas complexas entram por
    extratores especificos, mas o texto paginado ja garante rastreabilidade basica.
    """

    document = fitz.open(stream=payload, filetype="pdf")
    try:
        pages = [
            PageText(page_number=index + 1, text=document.load_page(index).get_text("text"))
            for index in range(document.page_count)
        ]
    finally:
        document.close()
    return ParsedDocument(file_name=file_name, pages=pages, mime_type="application/pdf")

