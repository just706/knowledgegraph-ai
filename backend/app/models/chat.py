"""对话会话与消息模型（多会话历史，类 ChatGPT）。

用户数据隔离：session / message 均带 user_id，所有查询按当前用户过滤
（AI 宪法第五章：用户数据必须隔离）。
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ChatSession(Base):
    """一个对话会话（左侧会话列表中的一项）。"""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(128), default="新对话")  # 会话标题（首条问题自动生成）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChatSession {self.id} title={self.title!r}>"


class ChatMessage(Base):
    """会话中的一条消息（用户提问或助手回答）。"""

    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chat_sessions.id"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 助手回答的引用来源（JSON 数组），用户消息为空
    sources_json: Mapped[str | None] = mapped_column(Text, default=None)
    # 生成模式：llm / local
    gen_mode: Mapped[str | None] = mapped_column(String(16), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ChatMessage {self.id} role={self.role!r}>"
