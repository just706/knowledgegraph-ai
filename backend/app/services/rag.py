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
    mode: str = "normal",
    user=None,
    history: list[dict[str, str]] | None = None,
) -> dict:
    """执行 RAG 问答，返回 {answer, sources}。user 用于解析其 LLM 凭证。

    history 为前端传入的最近若干轮对话（[{role, content}]），用于：
    - 检索时把追问/指代补全为带上下文的查询，提升召回准确率；
    - 生成时作为对话背景，让回答理解"它""这个"等指代。
    """
    ensure_embeddings(db, user_id)

    # 将多轮历史压缩为一段对话摘要文本，用于辅助检索与生成
    history_text = _format_history(history)
    # 检索查询：若有历史，将当前问题结合上一轮用户问题做轻量扩展，
    # 帮助理解指代（如"它是什么" → "X 是什么"）。
    retrieval_query = query
    if history_text:
        last_user_turn = _last_user_question(history)
        if last_user_turn and last_user_turn != query:
            retrieval_query = f"{last_user_turn} {query}"

    hits = retrieve(db, user_id, retrieval_query, top_k=top_k)

    chunks = [c for c, _ in hits]
    answer_text, gen_mode = generate_answer(
        query, chunks, mode=mode, user=user, history_text=history_text
    )

    sources = [
        {
            "document_id": c.document_id,
            "chunk_index": c.chunk_index,
            "snippet": c.content[:200],
            "score": round(score, 4),
        }
        for c, score in hits
    ]
    return {"answer": answer_text, "sources": sources, "mode": gen_mode}


def _format_history(history: list[dict[str, str]] | None) -> str:
    """将对话历史格式化为可读文本（仅 role/content 字段）。"""
    if not history:
        return ""
    lines = []
    for turn in history:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if not content:
            continue
        speaker = "用户" if role == "user" else "助手"
        lines.append(f"{speaker}：{content}")
    return "\n".join(lines)


def _last_user_question(history: list[dict[str, str]] | None) -> str:
    """取历史中最后一条用户提问（用于检索查询扩写）。"""
    if not history:
        return ""
    for turn in reversed(history):
        if turn.get("role") == "user" and (turn.get("content") or "").strip():
            return turn["content"].strip()
    return ""


def list_user_documents(db: Session, user_id: int) -> list[Document]:
    """列出用户文档（供前端判断是否有可问答的资料）。"""
    stmt = (
        select(Document)
        .where(Document.user_id == user_id)
        .order_by(Document.created_at.desc())
    )
    return list(db.scalars(stmt).all())
