"""后台管理相关 Schema。"""
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr


class AdminUserSummary(BaseModel):
    """管理员视角的用户摘要（含敏感字段，仅管理员可见）。"""
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str | None
    is_active: bool
    role: str
    created_at: datetime | None = None
    # 各模块计数
    document_count: int = 0
    chat_session_count: int = 0
    entity_count: int = 0
    mistake_count: int = 0
    quiz_count: int = 0


class UserToggleActive(BaseModel):
    is_active: bool


class UserSetRole(BaseModel):
    role: str  # admin 或 user


class SystemStats(BaseModel):
    """系统全局统计。"""
    total_users: int
    active_users: int
    admin_users: int
    total_documents: int
    total_chunks: int
    total_chat_sessions: int
    total_chat_messages: int
    total_entities: int
    total_relations: int
    total_mistakes: int
    total_quizzes: int


class AdminDashboard(BaseModel):
    """后台仪表盘总览。"""
    stats: SystemStats
    recent_users: list[AdminUserSummary]
