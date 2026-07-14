"""知识图谱相关校验/响应模型（Phase 5）。"""
from pydantic import BaseModel, ConfigDict


class GraphNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    label: str
    mentions: int
    degree: int


class GraphEdge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: int
    target: int
    relation: str
    weight: int


class GraphDataResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    entity_count: int
    relation_count: int


class GraphBuildResponse(BaseModel):
    entity_count: int
    relation_count: int
    message: str
