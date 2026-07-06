from __future__ import annotations

from io import BytesIO
from zipfile import ZipFile


def expand_zip_payload(payload: bytes) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    with ZipFile(BytesIO(payload)) as archive:
        for entry in archive.infolist():
            if entry.is_dir():
                continue
            files.append((entry.filename, archive.read(entry.filename)))
    return files


def is_zip(file_name: str, payload: bytes) -> bool:
    return file_name.lower().endswith(".zip") or payload.startswith(b"PK\x03\x04")

