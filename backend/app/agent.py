"""Agent 兜底层（ReAct 单轮/多轮工具调用）。

仅用于 Router 无法匹配的开放/复合意图。复用现有 services 作为工具，
绝不自行重造逻辑、绝不暴露写入型操作（如图谱抽取）。
"""
from __future__ import annotations

import json

from app.services.llm_client import (
    ToolCallResult,
    chat_completion,
    is_llm_enabled,
    resolve_credential,
    tool_call_completion,
)
from app.services.rag import answer as rag_answer
from app.services import stats_service, quiz_generator, plan_service

MAX_STEPS = 5

TOOLS = [
    {
        "name": "get_study_stats",
        "description": "获取当前用户学习概览：掌握度、薄弱知识点、错题分布、近7天趋势。无需参数。",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_quiz",
        "description": "针对某学科或薄弱点生成练习题，返回题目列表。",
        "parameters": {"type": "object", "properties": {
            "subject": {"type": "string", "description": "学科或主题，可空=不限"},
            "count": {"type": "integer", "description": "题目数量，默认5"},
            "sources": {"type": "array", "items": {"type": "string"}, "description": "来源:knowledge/mistakes/graph"},
            "q_types": {"type": "array", "items": {"type": "string"}, "description": "题型:choice/fill/judgment/short"},
        }},
    },
    {
        "name": "search_knowledge",
        "description": "在用户知识库中检索资料并生成回答（RAG）。",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "description": "检索条数，默认5"},
        }},
    },
    {
        "name": "make_plan",
        "description": "生成今日个性化学习计划（基于真实统计）。无需参数。",
        "parameters": {"type": "object", "properties": {}},
    },
]


def _to_text(data) -> str:
    """把工具返回（dict/list/模型）序列化为纯文本供 LLM 阅读。"""
    if isinstance(data, str):
        return data
    try:
        return json.dumps(data, ensure_ascii=False, default=str)
    except (TypeError, ValueError):
        return str(data)


def _dispatch_tool(db, user, name, args):
    """分发到对应 service（全部复用现有能力，按 user_id 隔离）。"""
    if name == "get_study_stats":
        return _to_text(stats_service.get_overview(db, user.id))
    if name == "generate_quiz":
        return _to_text(quiz_generator.generate_quiz(
            db, user.id,
            sources=args.get("sources", ["knowledge"]),
            count=args.get("count", 5),
            subject=args.get("subject"),
            q_types=args.get("q_types", ["choice"]),
            user=user,
        ))
    if name == "search_knowledge":
        res = rag_answer(db, user.id, query=args["query"], top_k=args.get("top_k", 5),
                         mode="normal", user=user, history=None)
        return res.get("answer", "")
    if name == "make_plan":
        return _to_text(plan_service.generate_plan(db, user.id, user))
    return f"未知工具：{name}"


def route_agent(db, user, payload) -> dict:
    """ReAct 兜底：无凭证→降级 RAG；循环工具→回灌；超步数/异常→降级 RAG。"""
    query = payload.query

    # 0) 无 LLM 凭证 → 降级普通 RAG
    if not is_llm_enabled(user):
        return rag_answer(db, user.id, query=query, top_k=payload.top_k or 5,
                          mode="normal", user=user, history=payload.history)

    system = ("你是 AI 学习助手的大脑。可以调用工具获取用户真实数据后再回答；"
              "工具返回的是真实数据，不要编造；信息足够时直接给出最终回答，不要调用工具。")

    cred = resolve_credential(user)
    is_openai = cred is not None and cred.kind == "openai_compatible"

    messages = [{"role": "user", "content": query}]

    for step in range(1, MAX_STEPS + 1):
        try:
            resp = tool_call_completion(
                user, system_prompt=system, messages=messages, tools=TOOLS, timeout=60
            )
        except Exception:  # noqa: BLE001  LLM 异常 → 降级 RAG
            return rag_answer(db, user.id, query=query, top_k=payload.top_k or 5,
                              mode="normal", user=user, history=payload.history)

        # 返回文本 → 结束
        if resp.text is not None:
            return {"answer": resp.text, "mode": "agent", "steps": step, "sources": []}

        # 有工具调用
        tool_calls = resp.tool_calls or []
        if is_openai:
            # 多轮：把 assistant(tool_calls) 与 tool 结果回灌，继续循环
            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {"id": tc["id"], "type": "function",
                     "function": {"name": tc["name"],
                                  "arguments": json.dumps(tc.get("arguments", {}), ensure_ascii=False)}}
                    for tc in tool_calls
                ],
            })
            for tc in tool_calls:
                try:
                    obs = _dispatch_tool(db, user, tc["name"], tc.get("arguments") or {})
                except Exception as e:  # noqa: BLE001
                    obs = f"工具执行失败：{e}"
                messages.append({"role": "tool", "tool_call_id": tc["id"], "content": obs})
            # 继续下一轮
        else:
            # 单轮：执行工具后，用普通对话把结果交给模型生成最终回答
            obs_text = ""
            for tc in tool_calls:
                try:
                    obs = _dispatch_tool(db, user, tc["name"], tc.get("arguments") or {})
                except Exception as e:  # noqa: BLE001
                    obs = f"工具执行失败：{e}"
                obs_text += f"\n[{tc['name']}] 返回：{obs}\n"
            try:
                final = chat_completion(
                    user, system_prompt=system,
                    user_prompt=(
                        f"用户的问题：{query}\n\n"
                        f"以下工具已返回真实数据，请据此给出最终回答（不要编造）：\n{obs_text}"
                    ),
                    temperature=0.3, timeout=60,
                )
            except Exception:  # noqa: BLE001
                final = ""
            return {"answer": final or "（暂时无法生成回答，请稍后再试）",
                    "mode": "agent", "steps": step, "sources": []}

    # 超步数 → 降级 RAG
    return rag_answer(db, user.id, query=query, top_k=payload.top_k or 5,
                      mode="normal", user=user, history=payload.history)
