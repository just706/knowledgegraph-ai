"""嵌入服务（Phase 4 RAG 核心）。

设计原则（AI 宪法：简单 > 成熟 > 可扩展 > 高级）：
- 若配置了 OPENAI_API_KEY，调用 OpenAI 兼容 embedings API 生成真实向量；
- 否则降级为本地"特征哈希向量"（character n-gram + 词频），
  无需任何外部依赖即可在无 API key 的开发环境跑通 RAG 召回。

向量统一以 JSON 字符串形式存储于 document_chunks.embedding。
"""
import json
import math
import re
from functools import lru_cache

from app.config import settings

# 本地向量维度（特征哈希桶数量）
_LOCAL_DIM = 512


def _is_real_embedding_enabled() -> bool:
    return bool(settings.OPENAI_API_KEY)


@lru_cache(maxsize=1)
def _http_client():
    """延迟导入 requests，仅在使用真实 embedding 时引入依赖。"""
    import requests

    return requests


def _local_embedding(text: str) -> list[float]:
    """本地特征哈希向量：中英文混合 n-gram 词频特征。

    思路：将文本切分为字符级 n-gram（1~2 元），哈希到固定维度桶，
    累加词频并做 L2 归一化，使语义相近的文本向量余弦相似度高。
    """
    text = (text or "").lower()
    # 提取中文字符、英文单词、数字片段
    tokens: list[str] = []
    # 中文按单字 + 二元；英文/数字按词
    cn_chars = re.findall(r"[\u4e00-\u9fff]", text)
    for i, ch in enumerate(cn_chars):
        tokens.append(ch)
        if i + 1 < len(cn_chars):
            tokens.append(cn_chars[i] + cn_chars[i + 1])
    en_words = re.findall(r"[a-z0-9]+", text)
    tokens.extend(en_words)

    vec = [0.0] * _LOCAL_DIM
    for tok in tokens:
        # 哈希到桶
        h = hash(tok) % _LOCAL_DIM
        vec[h] += 1.0

    # L2 归一化
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def embed_text(text: str) -> list[float]:
    """为单条文本生成向量（真实或本地降级）。"""
    if _is_real_embedding_enabled():
        try:
            return _remote_embedding(text)
        except Exception:  # noqa: BLE001 真实嵌入失败则降级，保证可用
            return _local_embedding(text)
    return _local_embedding(text)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """批量生成向量。"""
    if _is_real_embedding_enabled():
        try:
            return _remote_embedding_batch(texts)
        except Exception:  # noqa: BLE001
            return [_local_embedding(t) for t in texts]
    return [_local_embedding(t) for t in texts]


def _remote_embedding(text: str) -> list[float]:
    requests = _http_client()
    resp = requests.post(
        f"{settings.OPENAI_BASE_URL}/embeddings",
        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
        json={"model": settings.EMBEDDING_MODEL, "input": text},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def _remote_embedding_batch(texts: list[str]) -> list[list[float]]:
    requests = _http_client()
    resp = requests.post(
        f"{settings.OPENAI_BASE_URL}/embeddings",
        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
        json={"model": settings.EMBEDDING_MODEL, "input": texts},
        timeout=60,
    )
    resp.raise_for_status()
    return [d["embedding"] for d in resp.json()["data"]]


def serialize_vector(vec: list[float]) -> str:
    """将向量序列化为可存储的 JSON 字符串。"""
    return json.dumps(vec, ensure_ascii=False)


def deserialize_vector(raw: str | None) -> list[float] | None:
    """从 JSON 字符串还原向量。"""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度。维度不一致或任一为零向量时返回 0。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
