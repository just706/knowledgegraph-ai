"""API 路由包。"""
from app.api.documents import router as documents_router
from app.api.health import router as health_router
from app.api.users import router as users_router

__all__ = ["health_router", "users_router", "documents_router"]
