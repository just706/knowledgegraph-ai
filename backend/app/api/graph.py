"""知识图谱路由（Phase 5）。

提供：查询当前用户图谱、基于资料重新构建、清空图谱、
用户手动创建/删除关系（标注）。所有操作按当前用户隔离。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession
from app.models.document import Document, DocumentChunk
from app.models.graph import EntitySource
from app.schemas.graph import (
    GraphBuildResponse,
    GraphDataResponse,
    RelationCreate,
    RelationResponse,
)
from app.services.graph_builder import (
    MANUAL_RELATION_TYPES,
    add_manual_relation,
    build_graph,
    clear_graph,
    delete_relation,
    get_graph,
)

router = APIRouter(prefix="/graph", tags=["graph"])


@router.get("", response_model=GraphDataResponse)
def get_user_graph(
    min_weight: int = 1,
    category: str | None = None,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> dict:
    """获取当前用户的图谱数据（节点 + 边），用于前端可视化。

    category：非 None 时仅返回该分类下的实体与关系。
    """
    return get_graph(db, current_user.id, min_weight=min_weight, category=category)


@router.post("/build", response_model=GraphBuildResponse, status_code=status.HTTP_201_CREATED)
def build_user_graph(
    category: str | None = None,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> GraphBuildResponse:
    """基于当前用户资料切片重新构建图谱。

    抽取 + 合并落库；返回构建后的实体/关系数量。
    category：非 None 时仅基于该分类下的文档构建（并记录来源用于筛选）。
    """
    # 收集该用户（可选：该分类下）文档的切片文本
    doc_filter = [
        DocumentChunk.user_id == current_user.id,
        Document.user_id == current_user.id,
    ]
    if category and category != "全部":
        doc_ids = [
            s.document_id
            for s in db.scalars(
                select(EntitySource).where(
                    EntitySource.user_id == current_user.id,
                    EntitySource.category == category,
                )
            ).all()
        ]
        if not doc_ids:
            # 退而求其次：按文档表 category 字段过滤
            doc_ids = [
                d.id
                for d in db.scalars(
                    select(Document).where(
                        Document.user_id == current_user.id, Document.category == category
                    )
                ).all()
            ]
        doc_filter.append(DocumentChunk.document_id.in_(doc_ids))

    stmt = (
        select(DocumentChunk.content)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(*doc_filter)
    )
    chunks = list(db.scalars(stmt).all())
    if not chunks:
        raise HTTPException(
            status_code=400,
            detail="暂无资料可用于构建图谱，请先到「知识库」上传文档。",
        )

    # 取这些切片所属文档 id，用于记录实体来源
    doc_ids_stmt = (
        select(DocumentChunk.document_id)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(*doc_filter)
        .distinct()
    )
    document_ids = list(db.scalars(doc_ids_stmt).all())

    build_graph(db, current_user.id, chunks, user=current_user, document_ids=document_ids)
    graph = get_graph(db, current_user.id, category=category)
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


@router.get("/relation-types", response_model=list[str])
def list_relation_types() -> list[str]:
    """返回用户可标注的关系类型列表。"""
    return MANUAL_RELATION_TYPES


@router.post("/relations", response_model=RelationResponse, status_code=status.HTTP_201_CREATED)
def create_manual_relation(
    payload: RelationCreate,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> RelationResponse:
    """用户手动标注一条关系（实体 A -关系-> 实体 B）。"""
    try:
        rel = add_manual_relation(
            db, current_user.id, payload.source_id, payload.target_id, payload.relation
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RelationResponse(
        id=rel.id,
        source_id=rel.source_id,
        target_id=rel.target_id,
        relation=rel.relation,
        weight=rel.weight,
        source_type=rel.source,
    )


@router.delete("/relations/{relation_id}", status_code=status.HTTP_200_OK)
def remove_relation(
    relation_id: int,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> dict:
    """删除一条关系（仅限当前用户，auto 或 manual 均可）。"""
    try:
        delete_relation(db, current_user.id, relation_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"deleted": relation_id, "message": "关系已删除。"}
