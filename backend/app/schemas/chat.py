"""对话/问答相关校验与响应模型（Phase 4 RAG + 多会话历史）。

输入与响应分离，避免泄露内部字段（AI 宪法第三章）。
"""
from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

T = TypeVar("T")


class Paginated(BaseModel, Generic[T]):
    """通用分页响应外壳。"""

    total: int
    page: int
    page_size: int
    items: list[T]


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=5, ge=1, le=20)
    mode: str | None = Field(default="normal", pattern="^(normal|beginner|exam|interview)$")
    # 可选会话 id：不传则自动新建会话，传则追加到该会话
    session_id: int | None = Field(default=None)
    # 多轮对话上下文：由前端按"最近 N 轮"组装为 {role, content} 列表，
    # 用于让 RAG 生成与检索理解追问/指代（如"它""这个"），不持久化、不回传。
    history: list[dict[str, str]] | None = Field(default=None)


class ChatSource(BaseModel):
    document_id: int
    chunk_index: int
    snippet: str
    score: float


class ChatResponse(BaseModel):
    session_id: int
    session_title: str
    answer: str
    sources: list[ChatSource] = []
    # 生成模式：llm（AI 生成）/ local（本地模式，未配置 Key 或 AI 调用失败）
    mode: str = "local"


class ChatSessionCreate(BaseModel):
    """新建会话请求（标题可空）。"""

    title: str | None = Field(default=None, max_length=128)


class ChatSessionOut(BaseModel):
    """会话概要（列表项）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageOut(BaseModel):
    """会话中的单条消息。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: int
    role: str
    content: str
    sources: list[dict[str, Any]] = []
    gen_mode: str | None = None
    created_at: datetime

    @field_validator("sources", mode="before")
    @classmethod
    def _load_sources(cls, v):
        if isinstance(v, str):
            import json

            try:
                return json.loads(v) or []
            except (json.JSONDecodeError, ValueError):
                return []
        return v or []


# 分页别名（带泛型实例化）
PaginatedChatSessions = Paginated[ChatSessionOut]
PaginatedChatMessages = Paginated[ChatMessageOut]
