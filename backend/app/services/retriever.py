"""检索服务（Phase 4 RAG 召回）。

用户提问时，生成查询向量，从当前用户的文档切片中召回 Top-K 最相关片段。
- 若切片已向量化（embedding 字段非空），走向量余弦相似度检索；
- 若切片未向量化（历史数据或降级场景），走本地关键词（BM25 风格）检索兜底。

所有检索都按 user_id 隔离，确保用户数据不越权（AI 宪法第五章）。
"""
import math
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.services.embedding import (
    cosine_similarity,
    deserialize_vector,
    embed_text,
)

DEFAULT_TOP_K = 5


def _tokenize(text: str) -> list[str]:
    """简易分词：中文单字+二元，英文单词。"""
    import re

    text = (text or "").lower()
    tokens: list[str] = []
    cn = re.findall(r"[\u4e00-\u9fff]", text)
    for i, ch in enumerate(cn):
        tokens.append(ch)
        if i + 1 < len(cn):
            tokens.append(cn[i] + cn[i + 1])
    tokens.extend(re.findall(r"[a-z0-9]+", text))
    return tokens


def _bm25_score(query_tokens: list[str], content: str) -> float:
    """基于词频的轻量相关性打分（BM25 简化版）。"""
    if not query_tokens:
        return 0.0
    doc_tokens = _tokenize(content)
    if not doc_tokens:
        return 0.0
    doc_freq = Counter(doc_tokens)
    doc_len = len(doc_tokens)
    avg_len = 100.0  # 简化平均长度
    k1, b = 1.5, 0.75
    score = 0.0
    for qt in set(query_tokens):
        f = doc_freq.get(qt, 0)
        if f == 0:
            continue
        idf = math.log(1 + (doc_len + 1) / (f + 0.5))
        score += idf * (f * (k1 + 1)) / (f + k1 * (1 - b + b * doc_len / avg_len))
    return score


def retrieve(
    db: Session,
    user_id: int,
    query: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[tuple[DocumentChunk, float]]:
    """召回与 query 最相关的切片，返回 (chunk, score) 列表，按分数降序。"""
    # 只检索当前用户的切片
    stmt = select(DocumentChunk).where(DocumentChunk.user_id == user_id)
    chunks = list(db.scalars(stmt).all())
    if not chunks:
        return []

    query_vec = embed_text(query)
    query_tokens = _tokenize(query)

    scored: list[tuple[DocumentChunk, float]] = []
    for chunk in chunks:
        vec = deserialize_vector(chunk.embedding)
        if vec is not None and len(vec) == len(query_vec):
            sim = cosine_similarity(query_vec, vec)
            score = sim
        else:
            # 兜底：关键词检索
            score = _bm25_score(query_tokens, chunk.content)
        scored.append((chunk, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]
