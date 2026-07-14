"""智能出题服务（Phase 8）。

基于用户的三类学习数据生成练习题目：
  1. knowledge —— 知识库文档切片（document_chunks）
  2. mistakes  —— 错题本中未掌握的薄弱点（mistakes）
  3. graph     —— 知识图谱实体与关系（entities / relations）

生成策略：
  - 配置了 OPENAI_API_KEY 时，调用 LLM 生成结构化题目（JSON 数组）；
  - 否则降级为本地模板题，保证无网络也能演示。

所有题目按 user_id 落库到 quizzes 表，支持溯源（source 标记）。
判分时答错的题目可回写错题本（调用 mistake_service）。

遵循 AI 宪法：用户数据隔离、答案可溯源、LLM 失败不影响主流程。
"""
from __future__ import annotations

import json
import re
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.graph import Entity, Relation
from app.models.mistake import Mistake
from app.models.quiz import Quiz
from app.schemas.quiz import QuizAnswerItem, QuizQuestion
from app.services.llm_client import chat_completion, is_llm_enabled


# ------------------------- 数据收集 -------------------------
def _collect_knowledge(db: Session, user_id: int, subject: str | None, limit: int = 8) -> list[str]:
    stmt = (
        select(DocumentChunk.content)
        .join(Document, Document.id == DocumentChunk.document_id)
        .where(DocumentChunk.user_id == user_id, Document.user_id == user_id)
    )
    if subject:
        stmt = stmt.where(Document.title.contains(subject))
    chunks = list(db.scalars(stmt).all())
    # 取较长、信息量大的片段，截断避免过长
    chunks = [c for c in chunks if len(c.strip()) > 30]
    chunks = sorted(chunks, key=len, reverse=True)[:limit]
    return [c.strip()[:600] for c in chunks]


# 常见学科关键词，用于从资料标题推断真实学科（避免把来源名当学科）
_KNOWN_SUBJECTS = [
    "高等数学", "数学", "线性代数", "概率论", "微积分", "英语", "政治", "历史",
    "物理", "化学", "生物", "计算机", "数据结构", "操作系统", "网络", "数据库",
    "机器学习", "深度学习", "人工智能",
]


def _infer_subject(db: Session, user_id: int, requested: str | None) -> str:
    """推断练习的真实学科主题。

    优先级：
    1. 显式传入的 subject（用户在前端选择的）
    2. 从用户资料标题中匹配已知学科关键词
    3. 取首个资料标题去后缀后的前 6 个字
    不回退到来源名（'知识库'/'知识图谱'），因为那不是学科。
    """
    if requested:
        return requested
    titles = list(
        db.scalars(
            select(Document.title).where(Document.user_id == user_id)
        ).all()
    )
    for title in titles:
        for kw in _KNOWN_SUBJECTS:
            if kw in title:
                return kw
    if titles:
        return titles[0].rsplit(".", 1)[0][:6]
    return ""


def _collect_mistakes(db: Session, user_id: int, subject: str | None, limit: int = 8) -> list[Mistake]:
    stmt = select(Mistake).where(
        Mistake.user_id == user_id, Mistake.mastered.is_(False)
    )
    if subject:
        stmt = stmt.where(Mistake.subject == subject)
    stmt = stmt.order_by(Mistake.review_count.asc()).limit(limit)
    return list(db.scalars(stmt).all())


def _collect_graph(db: Session, user_id: int, subject: str | None, limit: int = 12) -> list[str]:
    """返回知识图谱三元组文本，如 '卷积神经网络 -属于-> 深度学习'。"""
    entity_name = select(Entity.name).where(Entity.id == Relation.source_id)
    target_name = select(Entity.name).where(Entity.id == Relation.target_id)
    stmt = (
        select(Relation)
        .where(Relation.user_id == user_id)
        .order_by(Relation.weight.desc())
        .limit(limit * 3)
    )
    rels = db.scalars(stmt).all()
    triples: list[str] = []
    for r in rels:
        src = db.scalars(select(Entity.name).where(Entity.id == r.source_id)).first()
        tgt = db.scalars(select(Entity.name).where(Entity.id == r.target_id)).first()
        if src and tgt:
            triples.append(f"{src} -{r.relation}-> {tgt}")
        if len(triples) >= limit:
            break
    if subject:
        triples = [t for t in triples if subject in t] or triples
    return triples


# ------------------------- LLM 调用 -------------------------
def _build_prompt(
    sources_block: str,
    count: int,
    q_types: list[str],
    subject: str | None,
) -> str:
    type_hint = {
        "choice": "单选题（提供 4 个选项，answer 为正确选项文字）",
        "fill": "填空题（answer 为填空处的标准答案）",
        "judgment": "判断题（answer 为 '正确' 或 '错误'）",
        "short": "简答题（answer 为要点）",
    }
    type_desc = "；".join(type_hint.get(t, t) for t in q_types)
    subject_line = f"主题范围：{subject}。" if subject else "主题范围：不限（覆盖以下资料的各个知识点）。"
    return (
        "你是一位出题严谨的助教。请基于下面的学习资料，为学生生成练习题，"
        "帮助学生巩固知识。\n"
        f"{subject_line}\n"
        f"请生成 {count} 道题，题型包括：{type_desc}。\n"
        "要求：\n"
        "1. 题目必须基于给定资料，不要编造资料中没有的知识点；\n"
        "2. 每题给出解析(explanation)并指出对应出处；\n"
        "3. 严格只输出如下 JSON 数组（不要加任何解释性文字、不要使用 markdown 代码块）：\n"
        '[{"source":"knowledge|mistakes|graph","q_type":"choice|fill|judgment|short",'
        '"subject":"主题","question":"题干","options":["A. ...","B. ..."],'
        '"answer":"正确答案","explanation":"解析与出处",'
        '"difficulty":3,"knowledge_point":"关联知识点"}]\n\n'
        f"【学习资料】\n{sources_block}"
    )


def _parse_llm_json(text: str) -> list[dict]:
    """从 LLM 输出中解析 JSON 数组，兼容被 markdown 代码块包裹的情况。"""
    text = text.strip()
    # 去掉 ```json ... ``` 包裹
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if not m:
        raise ValueError("未找到 JSON 数组")
    arr = json.loads(m.group(0))
    if not isinstance(arr, list):
        raise ValueError("JSON 不是数组")
    return arr


def _remote_generate(
    sources_block: str, count: int, q_types: list[str], subject: str | None, user=None
) -> list[dict]:
    prompt = _build_prompt(sources_block, count, q_types, subject)
    content = chat_completion(
        user,
        system_prompt="你是 KnowledgeGraph AI 的智能出题助教。",
        user_prompt=prompt,
        temperature=0.7,
        timeout=90,
    )
    return _parse_llm_json(content)


# ------------------------- 本地降级出题 -------------------------
def _local_questions(
    db: Session, user_id: int, sources: list[str], count: int, subject: str | None,
    real_subject: str = "",
) -> list[dict]:
    """无 LLM key 时的模板出题：尽量覆盖所选来源。

    subject：前端显式传入的学科（可能为 None）；real_subject：从资料推断的真实学科，
    用于 quiz.subject 落库，避免把来源名（知识库/知识图谱）当学科。
    """
    out: list[dict] = []
    knowledge = _collect_knowledge(db, user_id, subject) if "knowledge" in sources else []
    mistakes = _collect_mistakes(db, user_id, subject) if "mistakes" in sources else []
    graph = _collect_graph(db, user_id, subject) if "graph" in sources else []

    # 知识库：基于切片出理解题
    for c in knowledge[: max(1, count // 3 + 1)]:
        head = c[:80].replace("\n", " ")
        out.append({
            "source": "knowledge",
            "q_type": "short",
            "subject": real_subject or "资料练习",
            "question": f"请根据以下资料，用自己的话概括其核心内容：\n「{head}…」",
            "options": [],
            "answer": f"应围绕资料主题展开，关键词包括：{head}",
            "explanation": "（本地模式）此题基于你上传的资料切片生成，用于检验理解。配置 LLM 后可由 AI 自动出更丰富的题型。",
            "difficulty": 2,
            "knowledge_point": real_subject or "资料概括",
        })

    # 错题本：针对薄弱点出原题回顾
    for m in mistakes[: max(1, count // 3 + 1)]:
        out.append({
            "source": "mistakes",
            "q_type": "short",
            "subject": m.subject or real_subject or "错题",
            "question": f"重新作答这道你曾做错的题：{m.question}",
            "options": [],
            "answer": m.correct_answer or m.question,
            "explanation": f"这是你之前答错（或尚未掌握）的题。错误原因：{m.error_reason or '未填写'}。",
            "difficulty": 3,
            "knowledge_point": m.subject or "错题回顾",
        })

    # 知识图谱：基于三元组出概念关系题
    for t in graph[: max(1, count // 3 + 1)]:
        out.append({
            "source": "graph",
            "q_type": "fill",
            "subject": real_subject or "知识图谱",
            "question": f"依据知识图谱中的关系，补全下列关联：{t}（请说明该关系的含义）",
            "options": [],
            "answer": t,
            "explanation": "（本地模式）此题来自你构建的知识图谱实体关系，用于巩固概念关联。",
            "difficulty": 3,
            "knowledge_point": "知识图谱关系",
        })

    # 不足 count 则用知识库切片补齐
    idx = 0
    while len(out) < count and knowledge:
        c = knowledge[idx % len(knowledge)]
        idx += 1
        head = c[:80].replace("\n", " ")
        out.append({
            "source": "knowledge",
            "q_type": "short",
            "subject": real_subject or "资料练习",
            "question": f"简述以下资料的关键要点：\n「{head}…」",
            "options": [],
            "answer": head,
            "explanation": "（本地模式）基于资料切片生成的要点回顾题。",
            "difficulty": 2,
            "knowledge_point": real_subject or "资料要点",
        })
    return out[:count]


# ------------------------- 主入口：生成 -------------------------
def generate_quiz(
    db: Session,
    user_id: int,
    *,
    sources: list[str],
    count: int,
    subject: str | None,
    q_types: list[str],
    user=None,
) -> dict:
    sources = [s for s in sources if s in ("knowledge", "mistakes", "graph")] or ["knowledge"]

    # 推断真实学科主题（用于 quiz.subject，避免落库来源名）
    real_subject = _infer_subject(db, user_id, subject)

    knowledge = _collect_knowledge(db, user_id, subject) if "knowledge" in sources else []
    mistakes = _collect_mistakes(db, user_id, subject) if "mistakes" in sources else []
    graph = _collect_graph(db, user_id, subject) if "graph" in sources else []

    if not knowledge and not mistakes and not graph:
        raise LookupError("NO_MATERIAL")

    # 组装来源文本块
    blocks: list[str] = []
    if knowledge:
        blocks.append("【知识库文档】\n" + "\n---\n".join(knowledge))
    if mistakes:
        m_text = "\n".join(
            f"- 题目：{m.question}；正确答案：{m.correct_answer or '（未提供）'}；"
            f"错误原因：{m.error_reason or '（未填写）'}"
            for m in mistakes
        )
        blocks.append("【错题本薄弱点】\n" + m_text)
    if graph:
        blocks.append("【知识图谱关系】\n" + "\n".join(graph))
    sources_block = "\n\n".join(blocks)

    parsed: list[dict] = []
    mode = "local"
    if is_llm_enabled(user):
        try:
            parsed = _remote_generate(sources_block, count, q_types, subject, user=user)
            mode = "llm"
        except Exception:  # noqa: BLE001  LLM 失败降级
            parsed = []

    if not parsed:
        parsed = _local_questions(db, user_id, sources, count, subject, real_subject=real_subject)
        mode = "local"

    questions: list[QuizQuestion] = []
    for item in parsed:
        raw_diff = item.get("difficulty", 2)
        try:
            difficulty = max(1, min(5, int(raw_diff)))
        except (TypeError, ValueError):
            difficulty = 2
        # subject 优先用 LLM 返回；为空或属于来源名时回退到真实学科
        item_subject = item.get("subject") or ""
        if (not item_subject) or item_subject in ("知识库", "知识图谱", "错题"):
            item_subject = real_subject or item_subject
        q = QuizQuestion(
            source=item.get("source", sources[0]),
            q_type=item.get("q_type", "short"),
            subject=item_subject,
            question=str(item.get("question", "")).strip(),
            options=item.get("options") or [],
            answer=str(item.get("answer", "")).strip(),
            explanation=str(item.get("explanation", "")).strip(),
            difficulty=difficulty,
            knowledge_point=str(item.get("knowledge_point", "")).strip(),
        )
        if not q.question or not q.answer:
            continue
        questions.append(q)
        # 落库，保留溯源
        db.add(
            Quiz(
                user_id=user_id,
                source=q.source,
                q_type=q.q_type,
                subject=q.subject,
                question=q.question,
                options=json.dumps(q.options, ensure_ascii=False),
                answer=q.answer,
                explanation=q.explanation,
                difficulty=q.difficulty,
                knowledge_point=q.knowledge_point,
            )
        )
    db.commit()

    msg = "已基于所选来源生成题目" if mode == "llm" else "本地模式已生成题目（未使用 AI，题型较简单；可在「API 设置」配置自有 Key 升级）"
    return {"questions": questions, "mode": mode, "message": msg}


# ------------------------- 判分 + 回写错题本 -------------------------
def grade_quiz(db: Session, user_id: int, answers: list[QuizAnswerItem]) -> dict:
    total = len(answers)
    correct = 0
    wrong_items: list[QuizAnswerItem] = []
    for a in answers:
        ok = _is_correct(a.user_answer, a.answer, a.q_type if hasattr(a, "q_type") else "")
        if ok:
            correct += 1
        else:
            wrong_items.append(a)

    wrong = total - correct
    score = round(correct / total * 100) if total else 0

    # 答错的题回写错题本
    for w in wrong_items:
        db.add(
            Mistake(
                user_id=user_id,
                question=w.question,
                my_answer=w.user_answer,
                correct_answer=w.answer,
                error_reason=f"练习作答错误（来源：{w.source}）。解析：{w.explanation or '（无）'}",
                subject=w.subject,
            )
        )
    if wrong_items:
        db.commit()

    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "score": score,
        "wrong_items": wrong_items,
    }


def _is_correct(user_answer: str, answer: str, q_type: str) -> bool:
    ua = (user_answer or "").strip()
    an = (answer or "").strip()
    if not ua or not an:
        return False
    if q_type == "judgment":
        # 容忍 对/错 与 正确/错误 的写法
        ua_norm = ua.replace("√", "正确").replace("×", "错误")
        return ua_norm == an
    # 选择题：若 user_answer 以 "A." 形式给出，提取字母与 answer 比对
    if q_type == "choice":
        ua_letter = re.match(r"^([A-Da-d])[.\）)、\s]", ua)
        an_letter = re.match(r"^([A-Da-d])[.\）)、\s]", an)
        if ua_letter and an_letter:
            return ua_letter.group(1).upper() == an_letter.group(1).upper()
    # 默认：包含式比对（宽松判分）
    return ua == an or an in ua or ua in an
