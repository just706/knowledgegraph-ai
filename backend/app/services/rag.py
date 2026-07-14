"""RAG 协调服务（Phase 4）。

封装端到端的问答流程：
1. ensure_embeddings：确保用户文档切片已向量化（幂等）；
2. answer：检索相关切片 + 生成答案，并返回引用来源。

遵循 AI 宪法：用户数据隔离（全部按 user_id 过滤）、答案可溯源。
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.embedding import embed_texts, serialize_vector
from app.services.generator import generate_answer
from app.services.retriever import retrieve


def ensure_embeddings(db: Session, user_id: int) -> int:
    """为当前用户尚未向量化的切片生成 embedding，返回本次新生成的切片数。"""
    stmt = select(DocumentChunk).where(
        DocumentChunk.user_id == user_id,
        DocumentChunk.embedding.is_(None),
    )
    pending = list(db.scalars(stmt).all())
    if not pending:
        return 0

    texts = [c.content for c in pending]
    vectors = embed_texts(texts)
    for chunk, vec in zip(pending, vectors):
        chunk.embedding = serialize_vector(vec)
    db.commit()
    return len(pending)


def answer(
    db: Session,
    user_id: int,
    query: str,
    top_k: int = 5,
) -> dict:
    """执行 RAG 问答，返回 {answer, sources}。"""
    ensure_embeddings(db, user_id)
    hits = retrieve(db, user_id, query, top_k=top_k)

    chunks = [c for c, _ in hits]
    answer_text = generate_answer(query, chunks)

    sources = [
        {
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "snippet": c.content[:200],
            "score": round(score, 4),
        }
        for c, score in hits
    ]
    return {"answer": answer_text, "sources": sources}


def list_user_documents(db: Session, user_id: int) -> list[Document]:
    """列出用户文档（供前端判断是否有可问答的资料）。"""
    stmt = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    return list(db.scalars(stmt).all())
