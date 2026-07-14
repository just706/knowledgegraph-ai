"""对话/问答相关校验与响应模型（Phase 4 RAG）。

输入与响应分离，避免泄露内部字段（AI 宪法第三章）。
"""
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int | None = Field(default=5, ge=1, le=20)


class ChatSource(BaseModel):
    document_id: int
    chunk_index: int
    snippet: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = []
