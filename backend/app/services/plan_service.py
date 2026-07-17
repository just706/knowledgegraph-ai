"""学习计划 Agent 服务（V2 增强）。

综合用户真实学习数据（来自 stats_service.get_overview）生成结构化每日学习计划：
  - LLM 可用时：调用大模型基于掌握度/薄弱点/错题趋势产出个性化计划
  - LLM 不可用时：降级为基于 overview 真实数据的本地规则计划

所有数据按 user_id 隔离，不凭空编造（AI 宪法第五章）。
"""
from __future__ import annotations

import json
import re
from datetime import date

from sqlalchemy.orm import Session

from app.services import stats_service
from app.services.llm_client import chat_completion, is_llm_enabled

_SYSTEM_PROMPT = (
    "你是一个 AI 学习规划助手。根据用户的学习统计数据，生成一份今天（当天）的"
    "个性化学习计划。计划必须基于用户真实数据，聚焦于最薄弱的知识点。\n"
    "请只返回一个 JSON 对象，不要包含多余文字，格式如下：\n"
    "{\n"
    '  "goal": "一句话今日总目标",\n'
    '  "tasks": [\n'
    '    {"title": "任务标题", "detail": "具体做法", "duration": 25, "type": "复习|练习|阅读|整理"},\n'
    '    ...\n'
    "  ],\n"
    '  "tip": "一条学习建议"\n'
    "}\n"
    "duration 单位为分钟，整数；tasks 3-5 条，按优先级排序。"
)


def _extract_json(text: str) -> dict:
    """从 LLM 返回中稳健地提取 JSON 对象。"""
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        pass
    # 尝试匹配第一个 {...} 块（兼容模型多余包裹文字）
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass
    return {}


def _local_plan(overview: dict) -> dict:
    """LLM 不可用时的本地规则计划，完全基于 overview 真实字段。"""
    tasks = []
    goal = overview.get("today_goal") or "开启今天的学习"

    weak = [k for k in overview.get("knowledge_mastery", []) if k["value"] < 80]
    if weak:
        top = weak[0]["name"]
        tasks.append({
            "title": f"复习薄弱点：{top}",
            "detail": f"「{top}」当前掌握度 {weak[0]['value']}%，优先回顾基础概念与易错例题。",
            "duration": 25,
            "type": "复习",
        })
        tasks.append({
            "title": "针对性练习巩固",
            "detail": f"针对「{top}」完成一轮智能练习，检验掌握情况。",
            "duration": 20,
            "type": "练习",
        })

    if overview.get("recent_documents"):
        doc = overview["recent_documents"][0]["title"]
        tasks.append({
            "title": f"阅读资料：{doc}",
            "detail": "温习关键章节，标记不理解的术语以便后续提问。",
            "duration": 20,
            "type": "阅读",
        })

    if not tasks:
        tasks.append({
            "title": "上传第一份学习资料",
            "detail": "系统将基于你的资料生成知识库、练习与学习计划。",
            "duration": 15,
            "type": "整理",
        })

    tip = overview.get("ai_suggestion") or "保持每天固定时段学习，效果更佳。"
    return {"goal": goal, "tasks": tasks[:5], "tip": tip, "mode": "local"}


def generate_plan(db: Session, user_id: int, user) -> dict:
    """生成当日学习计划。优先 LLM，失败/无凭据时本地降级。"""
    overview = stats_service.get_overview(db, user_id)

    if not is_llm_enabled(user):
        plan = _local_plan(overview)
        plan["date"] = date.today().isoformat()
        return plan

    # 构建给 LLM 的精简上下文
    ctx = {
        "mastery_rate": overview["mastery_rate"],
        "knowledge_mastery": overview["knowledge_mastery"][:8],
        "mistake_subject_dist": overview["mistake_subject_dist"][:5],
        "recent_trend_7d": overview["mistake_trend_7d"],
        "quiz_total": overview["quiz_total"],
        "document_count": overview["document_count"],
        "today_goal_hint": overview.get("today_goal", ""),
    }
    user_prompt = (
        f"今天是 {date.today().isoformat()}。以下是该用户的学习统计：\n"
        f"{json.dumps(ctx, ensure_ascii=False)}\n\n"
        "请基于以上真实数据，生成今天的个性化学习计划。"
    )

    try:
        raw = chat_completion(
            user,
            system_prompt=_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.4,
            timeout=60,
            json_mode=True,
        )
        parsed = _extract_json(raw)
        if parsed and parsed.get("tasks"):
            parsed["date"] = date.today().isoformat()
            parsed.setdefault("goal", overview.get("today_goal", "今日学习计划"))
            parsed.setdefault("tip", "")
            parsed["mode"] = "llm"
            return parsed
    except Exception:  # noqa: BLE001  LLM 异常一律降级，主流程不受影响
        pass

    plan = _local_plan(overview)
    plan["date"] = date.today().isoformat()
    return plan
