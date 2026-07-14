"""错题本路由（Phase 7）。

提供：错题的增删改查、标记掌握、按主题筛选、AI 错题解析。
所有操作按当前用户隔离（AI 宪法第五章）。
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.models.mistake import Mistake
from app.schemas.mistake import (
    MistakeCreate,
    MistakeExplainResponse,
    MistakeOut,
    MistakeUpdate,
)
from app.services import mistake_service as svc

router = APIRouter(prefix="/mistakes", tags=["mistakes"])


@router.get("", response_model=list[MistakeOut])
def list_mistakes(
    unmastered: bool = False,
    subject: str | None = None,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> list[Mistake]:
    """列出当前用户的错题（可按未掌握/主题筛选）。"""
    return svc.list_mistakes(db, current_user.id, only_unmastered=unmastered, subject=subject)


@router.get("/subjects", response_model=list[str])
def list_subjects(db: DbSession = None, current_user: CurrentUser = None) -> list[str]:
    """列出当前用户错题涉及的全部主题。"""
    return svc.list_subjects(db, current_user.id)


@router.post("", response_model=MistakeOut, status_code=status.HTTP_201_CREATED)
def create_mistake(
    payload: MistakeCreate,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> Mistake:
    """新增一条错题。"""
    return svc.create_mistake(db, current_user.id, payload.model_dump())


@router.get("/{mistake_id}", response_model=MistakeOut)
def get_mistake(
    mistake_id: int,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> Mistake:
    mistake = svc.get_mistake(db, current_user.id, mistake_id)
    if mistake is None:
        raise HTTPException(status_code=404, detail="错题不存在")
    return mistake


@router.patch("/{mistake_id}", response_model=MistakeOut)
def update_mistake(
    mistake_id: int,
    payload: MistakeUpdate,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> Mistake:
    mistake = svc.get_mistake(db, current_user.id, mistake_id)
    if mistake is None:
        raise HTTPException(status_code=404, detail="错题不存在")
    return svc.update_mistake(db, mistake, payload.model_dump(exclude_unset=True))


@router.delete("/{mistake_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mistake(
    mistake_id: int,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> None:
    mistake = svc.get_mistake(db, current_user.id, mistake_id)
    if mistake is None:
        raise HTTPException(status_code=404, detail="错题不存在")
    svc.delete_mistake(db, mistake)


@router.post("/{mistake_id}/explain", response_model=MistakeExplainResponse)
def explain_mistake(
    mistake_id: int,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> dict:
    """生成该错题的 AI 诊断解析（无 key 时降级为本地模板）。"""
    try:
        return svc.explain_mistake(db, current_user.id, mistake_id)
    except LookupError:
        raise HTTPException(status_code=404, detail="错题不存在")
