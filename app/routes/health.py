from fastapi import APIRouter

from app.core.config import settings


router = APIRouter(tags=["health"])


@router.get("/health")
def healthcheck():
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.app_env,
        "api_prefix": settings.api_prefix,
        "auth_enabled": bool(settings.service_api_key),
    }
