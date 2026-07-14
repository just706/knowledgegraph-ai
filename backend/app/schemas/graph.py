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
    source_type: str = "auto"  # auto(抽取) / manual(用户标注)


class GraphDataResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    entity_count: int
    relation_count: int


class GraphBuildResponse(BaseModel):
    entity_count: int
    relation_count: int
    message: str


class RelationCreate(BaseModel):
    source_id: int
    target_id: int
    relation: str


class RelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source_id: int
    target_id: int
    relation: str
    weight: int
    source_type: str = "manual"
