"""知识图谱路由（Phase 5）。

提供：查询当前用户图谱、基于资料重新构建、清空图谱。
所有操作按当前用户隔离。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession
from app.models.document import Document, DocumentChunk
from app.schemas.graph import GraphBuildResponse, GraphDataResponse
from app.services.graph_builder import build_graph, clear_graph, get_graph

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=GraphDataResponse)
def get_user_graph(
    min_weight: int = 1,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> dict:
    """获取当前用户的图谱数据（节点 + 边），用于前端可视化。"""
    return get_graph(db, current_user.id, min_weight=min_weight)


@router.post("/build", response_model=GraphBuildResponse, status_code=status.HTTP_201_CREATED)
def build_user_graph(
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> GraphBuildResponse:
    """基于当前用户全部资料切片重新构建图谱。

    抽取 + 合并落库；返回构建后的实体/关系数量。
    """
    # 收集该用户所有切片文本
    stmt = (
        select(DocumentChunk.content)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(
            DocumentChunk.user_id == current_user.id,
            Document.user_id == current_user.id,
        )
    )
    chunks = list(db.scalars(stmt).all())
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="暂无资料可用于构建图谱，请先到「知识库」上传文档。",
        )

    build_graph(db, current_user.id, chunks)
    graph = get_graph(db, current_user.id)
    return GraphBuildResponse(
        entity_count=graph["entity_count"],
        relation_count=graph["relation_count"],
        message=f"图谱构建完成：{graph['entity_count']} 个实体，{graph['relation_count']} 条关系。",
    )


@router.delete("/clear", status_code=status.HTTP_200_OK)
def clear_user_graph(
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> dict:
    """清空当前用户的图谱数据。"""
    n = clear_graph(db, current_user.id)
    return {"deleted_entities": n, "message": f"已清空 {n} 个实体。"}
