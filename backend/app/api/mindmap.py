"""思维导图路由（Phase 6）。

提供：获取当前用户基于知识库生成的思维导图（学习地图）。
所有操作按当前用户隔离。
"""
from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession
from app.schemas.mindmap import MindmapResponse
from app.services.mindmap_builder import get_mindmap

router = APIRouter(prefix="/mindmap", tags=["mindmap"])


@router.get("", response_model=MindmapResponse)
def read_mindmap(
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> MindmapResponse:
    """返回当前用户的思维导图（由知识图谱投影生成）。"""
    data = get_mindmap(db, current_user.id)
    return MindmapResponse(**data)
