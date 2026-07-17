"""后台管理路由：用户管理、系统统计（仅管理员可访问）。"""
from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func

from app.api.deps import CurrentAdminUser, DbSession
from app.models.chat import ChatMessage, ChatSession
from app.models.document import Document, DocumentChunk
from app.models.graph import Entity, Relation
from app.models.mistake import Mistake
from app.models.quiz import Quiz
from app.models.user import User
from app.schemas.admin import (
    AdminDashboard,
    AdminUserSummary,
    SystemStats,
    UserSetRole,
    UserToggleActive,
)

router = APIRouter(prefix="/admin", tags=["admin"])


def _build_user_summary(user: User, db: DbSession) -> AdminUserSummary:
    """为单个用户聚合各模块计数。"""
    return AdminUserSummary(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        role=user.role,
        created_at=user.created_at,
        document_count=db.query(Document).filter(Document.user_id == user.id).count(),
        chat_session_count=db.query(ChatSession).filter(ChatSession.user_id == user.id).count(),
        entity_count=db.query(Entity).filter(Entity.user_id == user.id).count(),
        mistake_count=db.query(Mistake).filter(Mistake.user_id == user.id).count(),
        quiz_count=db.query(Quiz).filter(Quiz.user_id == user.id).count(),
    )


@router.get("/dashboard", response_model=AdminDashboard)
def dashboard(db: DbSession) -> AdminDashboard:
    """后台仪表盘：系统统计 + 最近注册用户。"""
    stats = SystemStats(
        total_users=db.query(User).count(),
        active_users=db.query(User).filter(User.is_active == True).count(),
        admin_users=db.query(User).filter(User.role == "admin").count(),
        total_documents=db.query(Document).count(),
        total_chunks=db.query(DocumentChunk).count(),
        total_chat_sessions=db.query(ChatSession).count(),
        total_chat_messages=db.query(ChatMessage).count(),
        total_entities=db.query(Entity).count(),
        total_relations=db.query(Relation).count(),
        total_mistakes=db.query(Mistake).count(),
        total_quizzes=db.query(Quiz).count(),
    )
    recent = (
        db.query(User)
        .order_by(User.created_at.desc().nullslast(), User.id.desc())
        .limit(20)
        .all()
    )
    recent_users = [_build_user_summary(u, db) for u in recent]
    return AdminDashboard(stats=stats, recent_users=recent_users)


@router.get("/users", response_model=list[AdminUserSummary])
def list_users(
    db: DbSession,
    q: str | None = None,
    role: str | None = None,
    active_only: bool = False,
    offset: int = 0,
    limit: int = 50,
) -> list[AdminUserSummary]:
    """用户列表（支持搜索邮箱/名称、角色筛选、仅活跃）。"""
    query = db.query(User)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            (User.email.ilike(pattern)) | (User.display_name.ilike(pattern))
        )
    if role:
        query = query.filter(User.role == role)
    if active_only:
        query = query.filter(User.is_active == True)
    users = query.order_by(User.id.desc()).offset(offset).limit(limit).all()
    return [_build_user_summary(u, db) for u in users]


@router.get("/users/{user_id}", response_model=AdminUserSummary)
def get_user_detail(user_id: int, db: DbSession) -> AdminUserSummary:
    """查看单个用户详情。"""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return _build_user_summary(user, db)


@router.put("/users/{user_id}/active", response_model=AdminUserSummary)
def toggle_user_active(user_id: int, payload: UserToggleActive, db: DbSession) -> AdminUserSummary:
    """启用/禁用用户。"""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    user.is_active = payload.is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return _build_user_summary(user, db)


@router.put("/users/{user_id}/role", response_model=AdminUserSummary)
def set_user_role(user_id: int, payload: UserSetRole, db: DbSession) -> AdminUserSummary:
    """修改用户角色（admin / user）。"""
    if payload.role not in ("admin", "user"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="角色必须是 admin 或 user",
        )
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    user.role = payload.role
    db.add(user)
    db.commit()
    db.refresh(user)
    return _build_user_summary(user, db)
