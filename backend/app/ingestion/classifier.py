from __future__ import annotations

import re
import unicodedata

from app.domain.schemas import CalculationSource


def classify_source(file_name: str, text: str) -> CalculationSource:
    haystack = normalize(f"{file_name}\n{text[:8000]}")

    if "assinado eletronicamente por: breno borges de camargo" in haystack:
        return CalculationSource.OFFICE
    if "parecer contabil" in haystack:
        return CalculationSource.COURT_ACCOUNTING
    if "poder judiciario" in haystack and "informacao" in haystack and "apresentamos calculo" in haystack:
        return CalculationSource.COURT_ACCOUNTING
    if "manual de calculos da justica federal" in haystack and "calculo apresentado pelo exequente" in haystack:
        return CalculationSource.COURT_ACCOUNTING
    if "pfe-inss" in haystack or "sistema de calculo (e-pcalc)" in haystack:
        return CalculationSource.INSS
    if "impugnante(s): instituto nacional do seguro social" in haystack:
        return CalculationSource.INSS
    if "instituto nacional do seguro social, pessoa jurídica de direito público" in haystack:
        return CalculationSource.INSS
    if "instituto nacional do seguro social, pessoa juridica de direito publico" in haystack:
        return CalculationSource.INSS
    if "impugnacao calculo inss" in haystack:
        return CalculationSource.OFFICE
    if "manifestar-se em discordancia aos calculos da contadoria" in haystack:
        return CalculationSource.OFFICE
    if "manifestar discordancia aos calculos da contadoria" in haystack:
        return CalculationSource.OFFICE
    if "manifestar-se em discordancia a impugnacao do executado" in haystack:
        return CalculationSource.OFFICE
    if "manifestar-se em discordancia ao parecer e calculos apresentados pela contadoria judicial" in haystack:
        return CalculationSource.OFFICE
    if "discordancia acerca da impugnacao e calculo apresentado pelo inss" in haystack:
        return CalculationSource.OFFICE
    if "discordancia acerca do calculo apresentado pelo inss" in haystack:
        return CalculationSource.OFFICE
    if "manifestar discordancia acerca do calculo apresentado pelo inss" in haystack:
        return CalculationSource.OFFICE
    if "move em face do inss, por meio de seu advogado" in haystack:
        return CalculationSource.OFFICE
    if "move em face do inss, por seus advogados" in haystack:
        return CalculationSource.OFFICE
    if "exequente" in haystack and "demonstrativo discriminado" in haystack:
        return CalculationSource.OFFICE
    if "informamos a vossa excelência que conferimos" in haystack:
        return CalculationSource.COURT_ACCOUNTING
    if "informamos a vossa excelencia que conferimos" in haystack:
        return CalculationSource.COURT_ACCOUNTING
    if "contadoria" in haystack and "resultado atrasados" in haystack:
        return CalculationSource.COURT_ACCOUNTING
    if "peticao intercorrente" in haystack or "petição intercorrente" in haystack:
        return CalculationSource.UNKNOWN
    return CalculationSource.UNKNOWN


def normalize(value: str) -> str:
    without_accents = "".join(
        c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", without_accents.lower()).strip()
