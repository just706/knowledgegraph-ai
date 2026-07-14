"""健康检查路由（无需认证）。"""
from fastapi import APIRouter

from app.config import settings
from app.schemas.common import HealthCheck

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthCheck)
def health_check() -> HealthCheck:
    return HealthCheck(status="ok", app_name=settings.APP_NAME, version="0.1.0")
