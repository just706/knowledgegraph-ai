"""思维导图相关响应模型（Phase 6）。"""
from pydantic import BaseModel, ConfigDict


class MindNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    kind: str = "topic"
    entity_id: int | None = None
    meta: dict = {}
    children: list["MindNode"] = []


class MindmapResponse(BaseModel):
    mode: str  # llm / local
    root: MindNode
    node_count: int
