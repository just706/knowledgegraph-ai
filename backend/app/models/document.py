"""文档与切片模型（Phase 3 知识库）。

用户数据隔离：document / chunk 均带 user_id，所有查询按当前用户过滤
（AI 宪法第五章：用户数据必须隔离）。
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Document(Base):
    """用户上传的资料文档元信息。"""

    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(32), nullable=False)  # txt / md / pdf
    file_size: Mapped[int] = mapped_column(Integer, default=0)  # 字节
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    # 分类（学科/资料类别）：上传时可选，缺省按标题自动推断
    category: Mapped[str] = mapped_column(String(64), default="未分类", index=True)
    status: Mapped[str] = mapped_column(String(32), default="ready")  # ready / processing / failed
    # 图谱构建状态：pending / success / failed（不再静默吞异常，便于前端反馈）
    graph_status: Mapped[str] = mapped_column(String(32), default="pending")
    graph_error: Mapped[str | None] = mapped_column(Text, nullable=True)  # 图谱构建失败的原因
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class DocumentChunk(Base):
    """文档切片：解析后的文本片段，供后续向量化与 RAG 检索。"""

    __tablename__ = "document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), index=True, nullable=False
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 文档内顺序
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_estimate: Mapped[int] = mapped_column(Integer, default=0)  # 粗略 token 估算
    embedding: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 向量（Phase 4 RAG）

    @property
    def has_embedding(self) -> bool:
        return bool(self.embedding)
