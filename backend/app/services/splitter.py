"""文本切片：将长文本切分为语义尽量完整的片段。

MVP 阶段用"递归字符切分"（按段落→句子→固定长度逐级切），不依赖 LLM，
属于代码职责（AI 宪法第四章）。向量化在 Phase 4 接入。
"""
from dataclasses import dataclass

# 切分时优先在这些分隔符处断开，保持语义完整
_SEPARATORS = ["\n\n", "\n", "。", "！", "？", ".", "!", "?", "；", ";", "，", ", ", " "]


@dataclass
class Chunk:
    content: str
    token_estimate: int


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数（中英文混合：按字符数 / 1.5 近似）。"""
    return max(1, round(len(text) / 1.5))


def split_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[Chunk]:
    """递归切分文本为片段。

    Args:
        text: 待切分文本
        chunk_size: 单片段目标最大字符数
        chunk_overlap: 相邻片段重叠字符数（保留上下文连贯）
    Returns:
        切片列表（按原文顺序）
    """
    text = text.strip()
    if not text:
        return []

    pieces = _recursive_split(text, chunk_size)
    chunks: list[Chunk] = []
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        # 单块仍超长时硬截断
        if len(piece) > chunk_size:
            for sub in _hard_split(piece, chunk_size, chunk_overlap):
                chunks.append(Chunk(content=sub, token_estimate=estimate_tokens(sub)))
        else:
            chunks.append(Chunk(content=piece, token_estimate=estimate_tokens(piece)))
    return chunks


def _recursive_split(text: str, chunk_size: int) -> list[str]:
    """递归按分隔符切分，直到每段 <= chunk_size。"""
    if len(text) <= chunk_size:
        return [text]

    for sep in _SEPARATORS:
        if sep in text:
            segments = text.split(sep)
            # 还原分隔符
            joined = [s + (sep if not sep.isspace() else "") for s in segments[:-1]] + [segments[-1]]
            result: list[str] = []
            for seg in joined:
                if len(seg) > chunk_size:
                    result.extend(_recursive_split(seg, chunk_size))
                else:
                    result.append(seg)
            if len(result) > 1:
                return result
    # 没有任何分隔符可用，直接硬切
    return _hard_split(text, chunk_size, 0)


def _hard_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """按固定长度硬切分。"""
    step = max(1, chunk_size - overlap)
    return [text[i : i + chunk_size] for i in range(0, len(text), step)]
