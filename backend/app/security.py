from __future__ import annotations

import os

from fastapi import HTTPException, Request, status


def configured_access_token() -> str | None:
    token = os.getenv("INTERNAL_ACCESS_TOKEN", "").strip()
    return token or None


async def require_access_token(request: Request) -> None:
    token = configured_access_token()
    if not token:
        return

    provided = request.headers.get("x-access-token", "").strip()
    if provided != token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de acesso ausente ou invalido.",
        )

