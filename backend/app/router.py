"""规则路由（Router）：按意图把请求分流到 Workflow 或 Agent 兜底。

纯函数、零 LLM 调用。明确意图走现有 services（确定性 Workflow），
只有规则无法匹配的复合/开放意图才进入 Agent。
"""
from __future__ import annotations

import re

from app.services.rag import answer as rag_answer
from app.services import plan_service, quiz_generator, graph_builder, stats_service
from app.agent import route_agent

# 路由表：顺序即优先级（先匹配先命中）
_ROUTES = [
    ("plan",  r"计划|安排|复习|规划|schedule|plan"),
    ("quiz",  r"出题|练习|做题|测验|题目|quiz|test|题"),
    ("graph", r"图谱|构建|生成图谱|知识网络|graph"),
    ("stats", r"统计|掌握度|薄弱|错题|进度|概览|学得|怎么样|如何"),
]

# 已知学科关键词，用于从「出题」类请求中识别学科与数量
_KNOWN_SUBJECTS = [
    "高等数学", "数学", "线性代数", "概率论", "微积分", "英语", "政治", "历史",
    "物理", "化学", "生物", "计算机", "数据结构", "操作系统", "网络", "数据库",
    "机器学习", "深度学习", "人工智能",
]


def classify(user_input: str) -> str:
    """规则意图分类，返回路由名；都不匹配返回 'agent'。"""
    text = (user_input or "").strip()
    for route, pattern in _ROUTES:
        if re.search(pattern, text, re.IGNORECASE):
            return route
    return "agent"


def dispatch(db, user, payload) -> dict:
    """入口分发。

    - mode == 'agent'：强制走 Agent。
    - mode 为普通 RAG 风格（normal/beginner/exam/interview）：强制普通 RAG，跳过路由。
    - 其余（auto/None）：按关键词规则路由。
    """
    mode = payload.mode
    if mode == "agent":
        return route_agent(db, user, payload)
    if mode in ("normal", "beginner", "exam", "interview"):
        res = rag_answer(db, user.id, query=payload.query, top_k=payload.top_k or 5,
                         mode=mode, user=user, history=payload.history)
        res["mode"] = f"rag:{mode}"
        return res

    route = classify(payload.query)
    if route == "plan":
        return route_plan(db, user, payload)
    if route == "quiz":
        return route_quiz(db, user, payload)
    if route == "graph":
        return route_graph(db, user, payload)
    if route == "stats":
        return route_stats(db, user, payload)
    return route_agent(db, user, payload)


# ------------------------- Workflow 路由（复用现有 services） -------------------------
def _fmt_stats(overview: dict) -> str:
    lines = ["📊 学习概览（基于你的真实数据）：",
             f"- 资料切片：{overview.get('chunk_count')} 条，知识库文档：{overview.get('document_count')} 份",
             f"- 知识图谱：{overview.get('entity_count')} 个实体 / {overview.get('relation_count')} 条关系",
             f"- 错题：共 {overview.get('mistake_total')} 道，已掌握 {overview.get('mistake_mastered')} 道，掌握率 {overview.get('mastery_rate')}%",
             f"- 已完成练习：{overview.get('quiz_total')} 道"]
    weak = [k for k in overview.get("knowledge_mastery", []) if k.get("value", 100) < 80]
    if weak:
        lines.append("- 薄弱知识点：" + "、".join(f"{w['name']}({w['value']}%)" for w in weak[:5]))
    lines.append(f"- AI 建议：{overview.get('ai_suggestion', '')}")
    lines.append(f"- 今日目标：{overview.get('today_goal', '')}")
    return "\n".join(lines)


def route_stats(db, user, payload) -> dict:
    try:
        overview = stats_service.get_overview(db, user.id)
    except Exception:  # noqa: BLE001
        return rag_answer(db, user.id, query=payload.query, top_k=payload.top_k or 5,
                          mode="normal", user=user, history=payload.history)
    return {"answer": _fmt_stats(overview), "sources": [], "mode": "workflow:stats"}


def _parse_quiz_args(query: str):
    count = 5
    m = re.search(r"(\d+)\s*(道|题|个)", query)
    if m:
        count = max(1, min(20, int(m.group(1))))
    subject = ""
    for kw in _KNOWN_SUBJECTS:
        if kw in query:
            subject = kw
            break
    return count, (subject or None)


def route_quiz(db, user, payload) -> dict:
    count, subject = _parse_quiz_args(payload.query)
    try:
        res = quiz_generator.generate_quiz(
            db, user.id,
            sources=["knowledge", "mistakes", "graph"],
            count=count, subject=subject,
            q_types=["choice", "fill", "judgment", "short"],
            user=user,
        )
    except LookupError:
        return {"answer": "你还没有可出题的学习资料或错题，请先上传资料或记录错题。",
                "sources": [], "mode": "workflow:quiz"}
    except Exception:  # noqa: BLE001
        return rag_answer(db, user.id, query=payload.query, top_k=payload.top_k or 5,
                          mode="normal", user=user, history=payload.history)
    questions = res.get("questions", [])
    if not questions:
        return {"answer": "暂时无法生成题目，请稍后再试。", "sources": [], "mode": "workflow:quiz"}
    lines = [f"已为你生成 {len(questions)} 道练习题：\n"]
    for i, q in enumerate(questions, 1):
        opts = q.options or []
        opt_text = "\n".join(f"  {o}" for o in opts) if opts else ""
        lines.append(f"{i}. （{q.q_type}）{q.question}{opt_text}")
        if q.answer:
            lines.append(f"   答案：{q.answer}")
        if q.explanation:
            lines.append(f"   解析：{q.explanation}")
    lines.append(f"\n（{res.get('message', '')}）")
    return {"answer": "\n".join(lines), "sources": [], "mode": "workflow:quiz"}


def route_plan(db, user, payload) -> dict:
    try:
        plan = plan_service.generate_plan(db, user.id, user)
    except Exception:  # noqa: BLE001
        return rag_answer(db, user.id, query=payload.query, top_k=payload.top_k or 5,
                          mode="normal", user=user, history=payload.history)
    tasks = plan.get("tasks", [])
    lines = [f"📅 今日学习计划（{plan.get('date', '')}）", f"目标：{plan.get('goal', '')}", ""]
    for i, t in enumerate(tasks, 1):
        lines.append(f"{i}. {t.get('title')}（{t.get('type', '')} · {t.get('duration', 0)}分钟）")
        if t.get("detail"):
            lines.append(f"   {t['detail']}")
    if plan.get("tip"):
        lines.append(f"\n建议：{plan['tip']}")
    return {"answer": "\n".join(lines), "sources": [], "mode": "workflow:plan"}


def route_graph(db, user, payload) -> dict:
    try:
        g = graph_builder.get_graph(db, user.id)
    except Exception:  # noqa: BLE001
        return rag_answer(db, user.id, query=payload.query, top_k=payload.top_k or 5,
                          mode="normal", user=user, history=payload.history)
    nodes = g.get("nodes", [])
    edges = g.get("edges", [])
    if not nodes:
        return {"answer": "你还没有构建知识图谱，请先上传资料并生成图谱。",
                "sources": [], "mode": "workflow:graph"}
    lines = [f"🕸 知识图谱概览：{len(nodes)} 个实体 / {len(edges)} 条关系\n", "主要实体："]
    for n in nodes[:15]:
        lines.append(f"- {n['name']}（{n.get('label', '')}，关联度 {n.get('degree', 0)}）")
    if edges:
        lines.append("\n部分关系：")
        for e in edges[:10]:
            src = next((n["name"] for n in nodes if n["id"] == e["source"]), "?")
            tgt = next((n["name"] for n in nodes if n["id"] == e["target"]), "?")
            lines.append(f"- {src} -{e['relation']}-> {tgt}")
    return {"answer": "\n".join(lines), "sources": [], "mode": "workflow:graph"}
