"""学习计划路由（V2 增强）。

提供：基于用户真实学习数据生成的当日个性化学习计划（LLM 优先，本地降级）。
所有操作按当前用户隔离（AI 宪法第五章）。
"""
from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession
from app.services import plan_service

router = APIRouter(prefix="/plan", tags=["plan"])


@router.get("/today", summary="获取今日学习计划")
def today_plan(db: DbSession = None, current_user: CurrentUser = None) -> dict:
    """综合用户真实学习数据，生成今日个性化学习计划。"""
    return plan_service.generate_plan(db, current_user.id, current_user)
