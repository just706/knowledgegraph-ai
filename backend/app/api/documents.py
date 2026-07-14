"""文档管理路由（Phase 3 知识库）。

所有操作按当前用户隔离（AI 宪法第五章：用户数据必须隔离）。
上传流程：解析 → 切片 → 落库（向量化在 Phase 4 接入）。
"""
import os

from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, DbSession
from app.models.document import Document, DocumentChunk
from app.schemas.document import DocumentDetail, DocumentPublic
from app.services.parser import (
    SUPPORTED_TYPES,
    extract_text,
    normalize_file_type,
)
from app.services.splitter import split_text

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=DocumentPublic, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> Document:
    """上传资料：解析 + 切片 + 入库（仅当前用户可见）。"""
    raw = file.file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="文件为空")

    if len(raw) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="文件超过 10MB 上限")

    file_type = normalize_file_type(file.filename or "")
    if not file_type:
        raise HTTPException(
            status_code=415,
            detail=f"不支持的文件类型，仅支持：{', '.join(sorted(SUPPORTED_TYPES))}",
        )

    try:
        text = extract_text(raw, file_type)
    except Exception as exc:  # noqa: BLE001 解析失败需明确反馈
        raise HTTPException(status_code=422, detail=f"文件解析失败：{exc}") from exc

    text = text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="文件中未提取到文本内容")

    chunks = split_text(text)

    doc = Document(
        user_id=current_user.id,
        filename=file.filename or "未命名",
        title=(file.filename or "未命名").rsplit(".", 1)[0],
        file_type=file_type,
        file_size=len(raw),
        chunk_count=len(chunks),
        status="ready",
    )
    db.add(doc)
    db.flush()  # 拿到 doc.id

    for idx, ch in enumerate(chunks):
        db.add(
            DocumentChunk(
                user_id=current_user.id,
                document_id=doc.id,
                chunk_index=idx,
                content=ch.content,
                token_estimate=ch.token_estimate,
            )
        )
    db.commit()
    db.refresh(doc)
    return doc


@router.get("", response_model=list[DocumentPublic])
def list_documents(
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> list[Document]:
    """列出当前用户的所有文档（按创建时间倒序）。"""
    stmt = (
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: int,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> Document:
    """获取文档详情及切片（仅当前用户）。"""
    doc = db.get(Document, document_id)
    if doc is None or doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文档不存在")

    stmt = (
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document_id,
            DocumentChunk.user_id == current_user.id,
        )
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = list(db.scalars(stmt).all())
    return DocumentDetail(**DocumentPublic.model_validate(doc).model_dump(), chunks=chunks)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document_id: int,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> None:
    """删除文档及其切片（级联，仅当前用户）。"""
    doc = db.get(Document, document_id)
    if doc is None or doc.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="文档不存在")
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id,
        DocumentChunk.user_id == current_user.id,
    ).delete()
    db.delete(doc)
    db.commit()
