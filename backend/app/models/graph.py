"""知识图谱模型（Phase 5）。

实体（Entity）与关系（Relation）均按用户隔离。
图谱从用户资料（DocumentChunk）中抽取，并保留来源回溯。
"""
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Entity(Base):
    """知识图谱中的实体节点（如：卷积神经网络、反向传播、Transformer）。"""

    __tablename__ = "entities"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_entity_user_name"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)  # 实体名（归一化）
    label: Mapped[str] = mapped_column(String(32), default="概念")  # 类型：概念/方法/术语...
    mention_count: Mapped[int] = mapped_column(Integer, default=1)  # 出现频次
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Entity {self.name!r}>"


class Relation(Base):
    """知识图谱中的关系边（如：卷积神经网络 -属于-> 深度学习）。"""

    __tablename__ = "relations"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "source_id", "target_id", "relation",
            name="uq_relation_user_triple",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    target_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id", ondelete="CASCADE"), nullable=False
    )
    relation: Mapped[str] = mapped_column(String(32), nullable=False)  # 关系类型
    weight: Mapped[int] = mapped_column(Integer, default=1)  # 共现/抽取次数
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Relation {self.source_id}-{self.relation}->{self.target_id}>"
