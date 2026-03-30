from fastapi import Header, HTTPException, status

from app.core.config import settings


def verify_service_api_key(x_api_key: str | None = Header(default=None)) -> None:
    expected_key = settings.service_api_key
    if not expected_key:
        return

    if x_api_key != expected_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header.",
        )
