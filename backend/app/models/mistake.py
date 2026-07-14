"""错题本模型（Phase 7）。

用户数据隔离：mistake 带 user_id，所有查询按当前用户过滤
（AI 宪法第五章：用户数据必须隔离）。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Mistake(Base):
    """用户错题本中的一条记录。"""

    __tablename__ = "mistakes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)          # 原题/知识点
    my_answer: Mapped[str] = mapped_column(Text, default="")             # 用户当时作答
    correct_answer: Mapped[str] = mapped_column(Text, default="")        # 正确答案/要点
    error_reason: Mapped[str] = mapped_column(Text, default="")          # 错误原因/反思
    subject: Mapped[str] = mapped_column(String(64), default="")         # 学科/主题标签
    mastered: Mapped[bool] = mapped_column(Boolean, default=False)       # 是否已掌握
    review_count: Mapped[int] = mapped_column(Integer, default=0)        # 复习次数
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Mistake {self.id} subject={self.subject!r}>"
