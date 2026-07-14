"""答案生成服务（Phase 4 RAG 生成）。

基于召回的上下文片段，调用 LLM 生成最终答案。
- 配置了 OPENAI_API_KEY 时，走真实 LLM（OpenAI 兼容 chat completions）；
- 否则降级为本地"模板拼接"答案：直接引用最相关片段并附来源，保证本地可演示。

遵循 AI 宪法：答案需可溯源，返回时携带引用来源。
"""
from collections.abc import Sequence

from app.config import settings
from app.models.document import DocumentChunk
from app.services.llm_client import chat_completion, is_llm_enabled


_MODE_PROMPTS: dict[str, str] = {
    "beginner": (
        "请用「初学者」的口吻回答：语言通俗、多用生活类比、避免生僻术语，"
        "一步步把基础概念讲清楚，必要时补充前置知识。"
    ),
    "exam": (
        "请用「应试备考」的口吻回答：紧扣考点、给出可直接记忆的结论与公式、"
        "点明易错点与常见考法，结构清晰便于复习。"
    ),
    "interview": (
        "请用「技术面试」的口吻回答：突出核心原理、对比与权衡、结合实际工程经验，"
        "结论严谨，体现深度思考。"
    ),
    "normal": (
        "请基于资料，严谨、条理清晰地回答。"
    ),
}


def _build_prompt(query: str, contexts: list[str], mode: str = "normal") -> str:
    context_block = "\n\n".join(
        f"[资料 {i + 1}]\n{c}" for i, c in enumerate(contexts)
    )
    mode_instruction = _MODE_PROMPTS.get(mode, _MODE_PROMPTS["normal"])
    return (
        "你是一个严谨的学习助手。请仅基于以下资料回答问题，"
        "若资料中无答案，请明确告知无法从资料中找到答案，不要编造。\n"
        f"{mode_instruction}\n\n"
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
        "\n（当前为本地模式：答案直接来自资料切片，未做 AI 语言润色。"
        "原因可能是未配置 LLM API Key，或本次 AI 调用失败（如 Key 无效 / 网络异常 / 厂商协议不支持）。"
        "在「API 设置」中配置有效的自有 Key 后即为 AI 生成。）"
    )
    return "\n".join(lines)


def generate_answer(
    query: str,
    chunks: Sequence[DocumentChunk],
    mode: str = "normal",
    user=None,
) -> tuple[str, str]:
    """基于召回切片生成答案。user 为当前登录用户（用于解析其 LLM 凭证）。

    返回 (答案文本, 生成模式)：mode 为 "llm"（AI 生成）或 "local"（本地模式）。
    本地模式可能因未配置 Key，或本次 AI 调用失败（见 llm_client 日志）触发。
    """
    if not chunks:
        if is_llm_enabled(user):
            # 仍允许 LLM 通用回答，但本系统强调 RAG，这里直接告知无资料
            return "暂无相关学习资料。请先在「知识库」上传文档，我再为你答疑。", "llm"
        return _local_answer(query, chunks), "local"

    if is_llm_enabled(user):
        try:
            return _remote_generate(query, [c.content for c in chunks], mode, user), "llm"
        except Exception:  # noqa: BLE001  AI 调用失败降级
            return _local_answer(query, chunks), "local"
    return _local_answer(query, chunks), "local"


def _remote_generate(query: str, contexts: list[str], mode: str = "normal", user=None) -> str:
    prompt = _build_prompt(query, contexts, mode)
    return chat_completion(
        user,
        system_prompt="你是 KnowledgeGraph AI 智能学习助手。",
        user_prompt=prompt,
        temperature=0.3,
        timeout=60,
    )
