"""学习仪表盘统计路由（Phase 8）。

提供：当前用户的学习概览统计。按用户隔离。
"""
from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession
from app.schemas.stats import StatsOverview
from app.services.stats_service import get_overview

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("/overview", response_model=StatsOverview)
def stats_overview(db: DbSession = None, current_user: CurrentUser = None) -> dict:
    """返回当前用户的学习统计概览（用于首页仪表盘）。"""
    return get_overview(db, current_user.id)
