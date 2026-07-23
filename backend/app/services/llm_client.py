"""统一 LLM 客户端封装（按用户计费核心 + 多厂商支持）。

职责：
1. 解析"当前用户"的 LLM 凭证：优先用用户自己填的 Provider / Key / BaseURL / Model；
   用户未填时，按 ALLOW_GLOBAL_LLM_FALLBACK 决定是否回退到 .env 全局兜底 Key。
2. 提供 chat_completion() / json_completion() 两个便捷方法，屏蔽不同厂商协议差异：
   - openai_compatible：标准 OpenAI /chat/completions（DeepSeek、通义、智谱、Ollama、vLLM…）
   - anthropic：Anthropic Messages API（Claude）
   - gemini：Google Gemini Generative Language API
3. 暴露 resolve_credential(user) 供各服务层判断"是否真的启用了 LLM"。

设计要点：
- 凭证只从「登录用户对象」解析，绝不隐式使用全局 Key 去扣别人的钱（除非明确兜底）。
- 返回结构统一，调用方无需关心厂商/key 来源。
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass

import requests

from app.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 厂商预设：前端下拉直接复用，用户也可手动覆盖 base_url / model。
# kind 决定底层走哪种协议封装。
# ---------------------------------------------------------------------------
PROVIDER_PRESETS: list[dict] = [
    {
        "id": "openai",
        "name": "OpenAI",
        "kind": "openai_compatible",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "doc": "https://platform.openai.com",
    },
    {
        "id": "deepseek",
        "name": "DeepSeek",
        "kind": "openai_compatible",
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
        "doc": "https://platform.deepseek.com",
    },
    {
        "id": "qwen",
        "name": "通义千问 (DashScope)",
        "kind": "openai_compatible",
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-plus",
        "doc": "https://help.aliyun.com/zh/dashscope",
    },
    {
        "id": "zhipu",
        "name": "智谱 GLM",
        "kind": "openai_compatible",
        "base_url": "https://open.bigmodel.cn/api/paas/v4",
        "model": "glm-4-flash",
        "doc": "https://open.bigmodel.cn",
    },
    {
        "id": "moonshot",
        "name": "Kimi (Moonshot)",
        "kind": "openai_compatible",
        "base_url": "https://api.moonshot.cn/v1",
        "model": "moonshot-v1-8k",
        "doc": "https://platform.moonshot.cn",
    },
    {
        "id": "minimax",
        "name": "MiniMax",
        "kind": "openai_compatible",
        "base_url": "https://api.minimax.chat/v1",
        "model": "abab6.5s-chat",
        "doc": "https://www.minimax.chat",
    },
    {
        "id": "ollama",
        "name": "Ollama (本地)",
        "kind": "openai_compatible",
        "base_url": "http://localhost:11434/v1",
        "model": "llama3",
        "doc": "https://ollama.com",
    },
    {
        "id": "anthropic",
        "name": "Anthropic Claude",
        "kind": "anthropic",
        "base_url": "https://api.anthropic.com",
        "model": "claude-3-5-sonnet-latest",
        "doc": "https://docs.anthropic.com",
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "kind": "gemini",
        "base_url": "https://generativelanguage.googleapis.com/v1beta",
        "model": "gemini-1.5-flash",
        "doc": "https://ai.google.dev",
    },
    {
        "id": "custom",
        "name": "自定义 (OpenAI 兼容)",
        "kind": "openai_compatible",
        "base_url": "",
        "model": "",
        "doc": "",
    },
]

# id -> kind 快速映射
_PROVIDER_KIND = {p["id"]: p["kind"] for p in PROVIDER_PRESETS}


def get_provider_presets() -> list[dict]:
    """返回给前端的厂商预设（不含敏感信息）。"""
    return PROVIDER_PRESETS


@dataclass
class LLMCredential:
    """一次 LLM 调用的凭证与端点信息。"""

    api_key: str
    base_url: str
    model: str
    # 协议类型：openai_compatible / anthropic / gemini
    kind: str
    # 本次是否来自用户自己的 Key（False 表示用了全局兜底）
    is_user_owned: bool


def resolve_credential(user) -> LLMCredential | None:
    """从用户对象解析 LLM 凭证。

    优先级：
    1. 用户自己选的 Provider + Key（llm_provider / llm_api_key / llm_base_url / llm_model）→ 扣用户额度
    2. 用户没填：若 ALLOW_GLOBAL_LLM_FALLBACK 为真且 .env 有 OPENAI_API_KEY
       → 用全局兜底（扣部署者额度，默认走 OpenAI 协议）
    3. 都不满足 → 返回 None（代表无可用 LLM，应降级本地逻辑）
    """
    if user is not None and getattr(user, "has_own_llm_key", False):
        api_key = user.llm_api_key
        if api_key:
            provider = getattr(user, "llm_provider", None) or "openai"
            kind = _PROVIDER_KIND.get(provider, "openai_compatible")
            preset = next((p for p in PROVIDER_PRESETS if p["id"] == provider), None)
            preset_base = (preset or {}).get("base_url") or ""
            preset_model = (preset or {}).get("model") or ""
            return LLMCredential(
                api_key=api_key,
                base_url=_normalize_base_url(user.llm_base_url or preset_base or settings.OPENAI_BASE_URL),
                model=(user.llm_model or (preset_model or settings.LLM_MODEL)),
                kind=kind,
                is_user_owned=True,
            )

    # 全局兜底
    if settings.ALLOW_GLOBAL_LLM_FALLBACK and settings.OPENAI_API_KEY:
        return LLMCredential(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.LLM_MODEL,
            kind="openai_compatible",
            is_user_owned=False,
        )
    return None


def is_llm_enabled(user) -> bool:
    """当前用户是否能使用真实 LLM（用于决定是否走本地降级）。"""
    return resolve_credential(user) is not None


def chat_completion(
    user,
    *,
    system_prompt: str | None,
    user_prompt: str,
    temperature: float = 0.3,
    timeout: int = 60,
    json_mode: bool = False,
) -> str:
    """发起一次 chat completion，返回文本。

    失败（网络/鉴权/超时）直接抛异常，由调用方决定降级。
    按厂商 kind 自动选择协议封装。
    """
    cred = resolve_credential(user)
    if cred is None:
        raise RuntimeError("NO_LLM_CREDENTIAL")

    try:
        if cred.kind == "anthropic":
            return _chat_anthropic(cred, system_prompt, user_prompt, temperature, timeout, json_mode)
        if cred.kind == "gemini":
            return _chat_gemini(cred, system_prompt, user_prompt, temperature, timeout, json_mode)
        return _chat_openai(cred, system_prompt, user_prompt, temperature, timeout, json_mode)
    except Exception as exc:  # noqa: BLE001  统一记录真实失败原因，便于排查 Key 是否有效
        logger.warning(
            "LLM 调用失败 provider=%s kind=%s model=%s base_url=%s err=%s",
            cred.provider if hasattr(cred, "provider") else "?",
            cred.kind if hasattr(cred, "kind") else "?",
            cred.model if hasattr(cred, "model") else "?",
            cred.base_url if hasattr(cred, "base_url") else "?",
            exc,
        )
        # 把"实际请求的 URL / 状态码"也带出来，便于前端精准诊断 404（路径错）还是 401（Key 错）
        attempted = getattr(exc, "request_url", None) or getattr(exc, "url", None)
        raise RuntimeError(
            f"LLM_CALL_FAILED: {exc}"
            + (f" | url={attempted}" if attempted else "")
        ) from exc


def _normalize_base_url(base_url: str | None) -> str:
    """清洗用户/预设的 base_url：去首尾空白；去掉结尾多余的斜杠。

    避免 ' https://x.com/ ' 之类误输入导致路径拼接出 '//' 或带空格的请求。
    """
    if not base_url:
        return ""
    return base_url.strip().rstrip("/")


def _chat_openai(cred, system_prompt, user_prompt, temperature, timeout, json_mode) -> str:
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})

    body: dict = {
        "model": cred.model,
        "messages": messages,
        "temperature": temperature,
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    resp = requests.post(
        f"{cred.base_url.rstrip('/')}/chat/completions",
        headers={"Authorization": f"Bearer {cred.api_key}"},
        json=body,
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _chat_anthropic(cred, system_prompt, user_prompt, temperature, timeout, json_mode) -> str:
    """Anthropic Messages API 封装。

    注意：Anthropic 用 x-api-key 头，且 system 为顶层字段，messages 仅含 user/assistant。
    """
    headers = {
        "x-api-key": cred.api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    if json_mode:
        headers["anthropic-beta"] = "output-json-2025-01-01"

    body: dict = {
        "model": cred.model,
        "max_tokens": 4096,
        "temperature": temperature,
        "messages": [{"role": "user", "content": user_prompt}],
    }
    if system_prompt:
        body["system"] = system_prompt
    if json_mode:
        body["output_format"] = {"type": "json"}

    resp = requests.post(
        f"{cred.base_url.rstrip('/')}/v1/messages",
        headers=headers,
        json=body,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    # Anthropic 返回 content 数组，拼接文本块
    text = "".join(
        block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
    )
    return text.strip()


def _chat_gemini(cred, system_prompt, user_prompt, temperature, timeout, json_mode) -> str:
    """Google Gemini Generative Language API 封装。

    Gemini 把 key 放在 query 参数，多轮以 contents 表达，system 指令放 systemInstruction。
    """
    url = f"{cred.base_url.rstrip('/')}/models/{cred.model}:generateContent"
    params = {"key": cred.api_key}

    parts = [{"text": user_prompt}]
    contents = [{"role": "user", "parts": parts}]
    body: dict = {
        "contents": contents,
        "generationConfig": {"temperature": temperature},
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    if json_mode:
        body["generationConfig"]["responseMimeType"] = "application/json"

    resp = requests.post(url, params=params, json=body, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates") or []
    if not candidates:
        return ""
    parts_out = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts_out)
    return text.strip()


def json_completion(
    user,
    *,
    system_prompt: str | None,
    user_prompt: str,
    temperature: float = 0.0,
    timeout: int = 60,
) -> dict:
    """发起一次返回 JSON 的 completion，解析为 dict（失败抛异常）。"""
    text = chat_completion(
        user,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        timeout=timeout,
        json_mode=True,
    )
    return json.loads(text)


# 兼容直接以 key 调用（如某些脚本），避免未使用导入告警
_ = os.environ


# ===========================================================================
# 工具调用（Agent 能力）：让 LLM 在 ReAct 循环中调用现有业务工具
# ===========================================================================
@dataclass
class ToolCallResult:
    """工具调用统一返回结构：text 与 tool_calls 二选一。"""

    text: str | None = None
    tool_calls: list[dict] | None = None  # 每项：{"id", "name", "arguments": {}}


def tool_call_completion(
    user,
    *,
    system_prompt: str,
    messages: list[dict],
    tools: list[dict],
    temperature: float = 0.3,
    timeout: int = 60,
) -> ToolCallResult:
    """多厂商工具调用统一入口。

    - openai_compatible：完整多轮工具循环。
    - anthropic / gemini：单次工具调用，由编排层做单轮（执行后二次普通对话）。
    无凭证抛 RuntimeError("NO_LLM_CREDENTIAL")，由编排层降级。
    """
    cred = resolve_credential(user)
    if cred is None:
        raise RuntimeError("NO_LLM_CREDENTIAL")
    if cred.kind == "openai_compatible":
        return _tool_openai(cred, system_prompt, messages, tools, temperature, timeout)
    if cred.kind == "anthropic":
        return _tool_anthropic(cred, system_prompt, messages, tools, temperature, timeout)
    if cred.kind == "gemini":
        return _tool_gemini(cred, system_prompt, messages, tools, temperature, timeout)
    text = chat_completion(
        user, system_prompt=system_prompt,
        user_prompt=_last_user_text(messages), temperature=temperature, timeout=timeout,
    )
    return ToolCallResult(text=text)


def _last_user_text(messages: list[dict]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            c = m.get("content")
            if isinstance(c, str):
                return c
    return ""


def _tool_openai(cred, system_prompt, messages, tools, temperature, timeout) -> ToolCallResult:
    sys_msgs = [{"role": "system", "content": system_prompt}] if system_prompt else []
    oa_msgs = sys_msgs + list(messages)
    oa_tools = [
        {"type": "function", "function": {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}}
        for t in tools
    ]
    body = {
        "model": cred.model,
        "messages": oa_msgs,
        "temperature": temperature,
        "tools": oa_tools,
        "tool_choice": "auto",
    }
    try:
        resp = requests.post(
            f"{cred.base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {cred.api_key}", "Content-Type": "application/json"},
            json=body,
            timeout=timeout,
        )
        resp.raise_for_status()
        msg = resp.json()["choices"][0]["message"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM 工具调用失败：%s", exc)
        raise
    if msg.get("tool_calls"):
        calls = []
        for tc in msg["tool_calls"]:
            if tc.get("type") != "function":
                continue
            try:
                args = json.loads(tc["function"].get("arguments") or "{}")
            except (json.JSONDecodeError, TypeError):
                args = {}
            calls.append({"id": tc["id"], "name": tc["function"]["name"], "arguments": args})
        return ToolCallResult(tool_calls=calls)
    return ToolCallResult(text=(msg.get("content") or "").strip())


def _tool_anthropic(cred, system_prompt, messages, tools, temperature, timeout) -> ToolCallResult:
    anth_tools = [
        {"name": t["name"], "description": t["description"], "input_schema": t["parameters"]}
        for t in tools
    ]
    convo = _oa_to_anthropic_messages(messages)
    body = {"model": cred.model, "max_tokens": 4096, "temperature": temperature, "messages": convo, "tools": anth_tools}
    if system_prompt:
        body["system"] = system_prompt
    try:
        resp = requests.post(
            f"{cred.base_url.rstrip('/')}/v1/messages",
            headers={"x-api-key": cred.api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
            json=body,
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Anthropic 工具调用失败：%s", exc)
        raise
    blocks = data.get("content", [])
    text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
    tool_uses = [b for b in blocks if b.get("type") == "tool_use"]
    if tool_uses:
        calls = [{"id": b["id"], "name": b["name"], "arguments": b.get("input", {}) or {}} for b in tool_uses]
        return ToolCallResult(tool_calls=calls)
    return ToolCallResult(text="".join(text_parts).strip())


def _tool_gemini(cred, system_prompt, messages, tools, temperature, timeout) -> ToolCallResult:
    decls = [
        {"name": t["name"], "description": t["description"], "parameters": t["parameters"]}
        for t in tools
    ]
    contents = _oa_to_gemini_contents(messages)
    body: dict = {
        "contents": contents,
        "tools": [{"functionDeclarations": decls}],
        "generationConfig": {"temperature": temperature},
    }
    if system_prompt:
        body["systemInstruction"] = {"parts": [{"text": system_prompt}]}
    url = f"{cred.base_url.rstrip('/')}/models/{cred.model}:generateContent"
    try:
        resp = requests.post(url, params={"key": cred.api_key}, json=body, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini 工具调用失败：%s", exc)
        raise
    parts = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
    calls = [p for p in parts if p.get("functionCall")]
    if calls:
        out = []
        for p in calls:
            fc = p["functionCall"]
            out.append({"id": fc.get("name"), "name": fc["name"], "arguments": fc.get("args", {}) or {}})
        return ToolCallResult(tool_calls=out)
    text = "".join(p.get("text", "") for p in parts)
    return ToolCallResult(text=text.strip())


def _oa_to_anthropic_messages(messages: list[dict]) -> list[dict]:
    """OpenAI 格式 messages → Anthropic messages。"""
    out = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role == "system":
            continue
        if role == "user":
            if isinstance(content, str):
                out.append({"role": "user", "content": [{"type": "text", "text": content}]})
            else:
                out.append({"role": "user", "content": content})
        elif role == "assistant":
            blocks = []
            if isinstance(content, str) and content:
                blocks.append({"type": "text", "text": content})
            for tc in m.get("tool_calls", []) or []:
                fn = tc.get("function", {})
                try:
                    inp = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    inp = {}
                blocks.append({"type": "tool_use", "id": tc.get("id"), "name": fn.get("name"), "input": inp})
            if blocks:
                out.append({"role": "assistant", "content": blocks})
        elif role == "tool":
            out.append({"role": "user", "content": [{"type": "tool_result", "tool_use_id": m.get("tool_call_id"), "content": str(content)}]})
    return out


def _oa_to_gemini_contents(messages: list[dict]) -> list[dict]:
    """OpenAI 格式 messages → Gemini contents（单轮够用，tool 结果由编排层转普通对话）。"""
    out = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if role == "system":
            continue
        g_role = "user" if role in ("user", "tool") else "model"
        if isinstance(content, str):
            if content:
                out.append({"role": g_role, "parts": [{"text": content}]})
        elif role == "assistant":
            parts = []
            if content:
                parts.append({"text": content})
            for tc in m.get("tool_calls", []) or []:
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except (json.JSONDecodeError, TypeError):
                    args = {}
                parts.append({"functionCall": {"name": fn.get("name"), "args": args}})
            if parts:
                out.append({"role": "model", "parts": parts})
    return out
