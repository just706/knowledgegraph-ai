"""答案生成服务（Phase 4 RAG 生成）。

基于召回的上下文片段，调用 LLM 生成最终答案。
- 配置了 OPENAI_API_KEY 时，走真实 LLM（OpenAI 兼容 chat completions）；
- 否则降级为本地"模板拼接"答案：直接引用最相关片段并附来源，保证本地可演示。

遵循 AI 宪法：答案需可溯源，返回时携带引用来源。
"""
from collections.abc import Sequence

from app.config import settings
from app.models.document import DocumentChunk


def _is_real_llm_enabled() -> bool:
    return bool(settings.OPENAI_API_KEY)


def _build_prompt(query: str, contexts: list[str]) -> str:
    context_block = "\n\n".join(
        f"[资料 {i + 1}]\n{c}" for i, c in enumerate(contexts)
    )
    return (
        "你是一个严谨的学习助手。请仅基于以下资料回答问题，"
        "若资料中无答案，请明确告知无法从资料中找到答案，不要编造。\n\n"
        f"{context_block}\n\n"
        f"问题：{query}\n\n回答："
    )


def _local_answer(query: str, chunks: Sequence[DocumentChunk]) -> str:
    """本地降级答案：汇总最相关片段要点，透明说明来源。"""
    if not chunks:
        return "暂无相关学习资料。请先在「知识库」上传文档，我再为你答疑。"
    lines = [f"根据已上传的资料，关于「{query}」有以下相关内容：\n"]
    for i, ch in enumerate(chunks, 1):
        snippet = ch.content.strip()
        if len(snippet) > 300:
            snippet = snippet[:300] + "…"
        lines.append(f"{i}. {snippet}")
    lines.append(
        "\n（当前为本地演示模式：未配置 LLM API Key，"
        "答案直接来自资料切片，未做语言润色。配置 OPENAI_API_KEY 后即为 AI 生成。）"
    )
    return "\n".join(lines)


def generate_answer(
    query: str,
    chunks: Sequence[DocumentChunk],
) -> str:
    """基于召回切片生成答案。"""
    if not chunks:
        if _is_real_llm_enabled():
            # 仍允许 LLM 通用回答，但本系统强调 RAG，这里直接告知无资料
            return "暂无相关学习资料。请先在「知识库」上传文档，我再为你答疑。"
        return _local_answer(query, chunks)

    if _is_real_llm_enabled():
        try:
            return _remote_generate(query, [c.content for c in chunks])
        except Exception:  # noqa: BLE001
            return _local_answer(query, chunks)
    return _local_answer(query, chunks)


def _remote_generate(query: str, contexts: list[str]) -> str:
    import requests

    prompt = _build_prompt(query, contexts)
    resp = requests.post(
        f"{settings.OPENAI_BASE_URL}/chat/completions",
        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
        json={
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": "你是 KnowledgeGraph AI 智能学习助手。"},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
        },
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()
