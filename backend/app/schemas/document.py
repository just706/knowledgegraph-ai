"""文档相关校验/响应模型（Phase 3 知识库）。

输入与响应分离，避免泄露内部字段（AI 宪法第三章）。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentCreate(BaseModel):
    """上传资料时可选的元信息（如分类）。"""

    category: str | None = None


class DocumentPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    filename: str
    title: str
    file_type: str
    file_size: int
    chunk_count: int
    category: str
    status: str
    graph_status: str
    graph_error: str | None
    created_at: datetime


class DocumentChunkPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    document_id: int
    chunk_index: int
    content: str
    token_estimate: int


class DocumentDetail(DocumentPublic):
    chunks: list[DocumentChunkPublic] = []
