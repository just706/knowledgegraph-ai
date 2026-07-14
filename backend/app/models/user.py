"""用户模型（Phase 2 用户系统的基础表）。

MVP 优先：先定义最小用户实体，后续按迁移管理扩展（AI 宪法第五章：结构修改必须通过迁移）。
用户数据隔离通过 user_id 行级隔离实现。
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)
