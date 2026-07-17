"""错题本服务（Phase 7）。

职责：
1. CRUD 数据访问（按 user_id 隔离）；
2. AI 错题解析：基于题目 / 我的答案 / 正确答案，调用 LLM 生成
   诊断式讲解（错在哪、为什么错、如何避免、相关知识点）。
   可降级：无 LLM key 或调用失败时，返回本地结构化模板解析。

遵循 AI 宪法：用户数据隔离、答案可溯源、失败不影响主流程。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.mistake import Mistake
from app.services.llm_client import chat_completion, is_llm_enabled

# 间隔重复（Anki 式）间隔天数：stage 1/2/3 分别对应 +1/+3/+7 天；
# stage>=3 且确认答对即判定真正掌握。
_REVIEW_INTERVALS = {1: 1, 2: 3, 3: 7}
_MAX_STAGE = 3


# ------------------------- CRUD -------------------------
def list_mistakes(
    db: Session, user_id: int, *, only_unmastered: bool = False, subject: str | None = None
) -> list[Mistake]:
    stmt = select(Mistake).where(Mistake.user_id == user_id)
    if only_unmastered:
        stmt = stmt.where(Mistake.mastered.is_(False))
    if subject:
        stmt = stmt.where(Mistake.subject == subject)
    stmt = stmt.order_by(Mistake.created_at.desc())
    return list(db.scalars(stmt).all())


def get_mistake(db: Session, user_id: int, mistake_id: int) -> Mistake | None:
    return db.scalars(
        select(Mistake).where(Mistake.id == mistake_id, Mistake.user_id == user_id)
    ).first()


def create_mistake(db: Session, user_id: int, data: dict) -> Mistake:
    mistake = Mistake(user_id=user_id, **data)
    db.add(mistake)
    db.commit()
    db.refresh(mistake)
    return mistake


def update_mistake(db: Session, mistake: Mistake, data: dict) -> Mistake:
    for key, value in data.items():
        if value is not None:
            setattr(mistake, key, value)
    db.commit()
    db.refresh(mistake)
    return mistake


def delete_mistake(db: Session, mistake: Mistake) -> None:
    db.delete(mistake)
    db.commit()


def list_subjects(db: Session, user_id: int) -> list[str]:
    """返回该用户错题涉及的全部主题（去重，供前端筛选）。"""
    rows = db.scalars(
        select(Mistake.subject)
        .where(Mistake.user_id == user_id, Mistake.subject != "")
        .distinct()
    ).all()
    return [r for r in rows if r]


# ------------------------- 间隔重复（掌握判定） -------------------------
def due_mistakes(db: Session, user_id: int) -> list[Mistake]:
    """返回当前已到复习时间、可确认掌握的错题（复习计划进行中且未超期等待）。"""
    now = datetime.utcnow()
    stmt = (
        select(Mistake)
        .where(
            Mistake.user_id == user_id,
            Mistake.mastered.is_(False),
            Mistake.review_stage > 0,
            Mistake.next_review_at <= now,
        )
        .order_by(Mistake.next_review_at.asc())
    )
    return list(db.scalars(stmt).all())


def schedule_review(db: Session, user_id: int, mistake_id: int) -> Mistake:
    """开始复习：进入间隔计划（stage=1，下次复习 = 现在 +1 天）。

    不直接置 mastered，需经过间隔计划、到期确认答对后才真正掌握。
    """
    m = get_mistake(db, user_id, mistake_id)
    if m is None:
        raise LookupError("错题不存在")
    now = datetime.utcnow()
    m.review_stage = 1
    m.last_review_at = now
    m.next_review_at = now + timedelta(days=_REVIEW_INTERVALS.get(1, 1))
    m.review_count = (m.review_count or 0) + 1
    db.commit()
    db.refresh(m)
    return m


def confirm_review(db: Session, user_id: int, mistake_id: int) -> Mistake:
    """确认本次复习已答对：推进间隔计划。

    - 若还未到 next_review_at，返回未到期（不做状态变更，前端应拦截）；
    - stage 递增，安排下一间隔；stage 达到上限且本次确认答对则 mastered=True。
    """
    m = get_mistake(db, user_id, mistake_id)
    if m is None:
        raise LookupError("错题不存在")
    now = datetime.utcnow()
    if m.next_review_at and now < m.next_review_at:
        raise ValueError("NOT_DUE")  # 尚未到复习时间，不能提前确认
    m.review_count = (m.review_count or 0) + 1
    m.last_review_at = now
    if m.review_stage >= _MAX_STAGE:
        m.mastered = True
        m.review_stage = _MAX_STAGE + 1  # 标记完成
        m.next_review_at = None
    else:
        m.review_stage = (m.review_stage or 0) + 1
        m.next_review_at = now + timedelta(days=_REVIEW_INTERVALS.get(m.review_stage, 7))
    db.commit()
    db.refresh(m)
    return m


def advance_on_correct(db: Session, user_id: int, question: str, subject: str | None = None) -> list[int]:
    """测验答对时，自动推进与之关联的错题复习进度（按题目文本匹配）。

    返回被推进/掌握的错题 id 列表。匹配规则：题目文本包含同一道错题的 question。
    """
    if not question:
        return []
    q = question.strip()
    stmt = select(Mistake).where(
        Mistake.user_id == user_id,
        Mistake.mastered.is_(False),
        Mistake.review_stage > 0,
    )
    if subject:
        stmt = stmt.where(Mistake.subject == subject)
    candidates = list(db.scalars(stmt).all())
    advanced: list[int] = []
    for m in candidates:
        if q and m.question and m.question.strip() and m.question.strip() in q:
            try:
                confirm_review(db, user_id, m.id)
                advanced.append(m.id)
            except ValueError:
                # NOT_DUE：尚未到复习时间，仅记录复习次数
                m.review_count = (m.review_count or 0) + 1
                db.commit()
    return advanced


# ------------------------- AI 解析 -------------------------
def explain_mistake(
    db: Session, user_id: int, mistake_id: int, user=None
) -> dict:
    """生成错题解析。优先 LLM（用户自有 key），失败/无 key 降级本地模板。"""
    mistake = get_mistake(db, user_id, mistake_id)
    if mistake is None:
        raise LookupError("错题不存在")

    if is_llm_enabled(user):
        try:
            return {
                "explanation": _remote_explain(mistake, user),
                "mode": "llm",
            }
        except Exception:  # noqa: BLE001  LLM 失败降级
            pass
    return {"explanation": _local_explain(mistake), "mode": "local"}


def _remote_explain(mistake: Mistake, user=None) -> str:
    prompt = (
        "你是一位耐心的学习辅导老师。下面是一条学生的错题记录，"
        "请据此生成诊断式讲解，帮助学生真正弄懂。\n"
        "讲解需包含：① 这道题/知识点在考什么；② 学生答案的问题出在哪里；"
        "③ 正确的思路与答案；④ 如何避免再错（记忆/方法提示）；"
        "⑤ 1-2 个相关知识点延伸。\n"
        "请用清晰的分点中文回答。\n\n"
        f"【题目/知识点】{mistake.question}\n"
        f"【我的答案】{mistake.my_answer or '（未作答）'}\n"
        f"【正确答案】{mistake.correct_answer or '（未提供）'}\n"
        f"【错误原因/反思】{mistake.error_reason or '（未填写）'}\n"
    )
    return chat_completion(
        user,
        system_prompt="你是 KnowledgeGraph AI 的学习辅导老师。",
        user_prompt=prompt,
        temperature=0.4,
        timeout=60,
    )


def _local_explain(mistake: Mistake) -> str:
    """本地降级解析：结构化模板，无网络也能用。"""
    lines = [
        "【错题诊断（本地模式）】",
        f"题目/知识点：{mistake.question}",
        f"我的答案：{mistake.my_answer or '（未作答）'}",
        f"正确答案：{mistake.correct_answer or '（未提供）'}",
        f"错误原因：{mistake.error_reason or '（未填写，建议补充便于复盘）'}",
        "",
        "提示：当前为本地模式（未使用 AI 解析），以上为记录回显。",
        "原因可能是未配置 LLM API Key，或本次 AI 调用失败。",
        "在「API 设置」中配置有效的自有 Key 后，将由 AI 生成诊断式讲解（错因分析 + 正确思路 + 防错方法）。",
    ]
    return "\n".join(lines)


# ------------------------- 薄弱点分析 -------------------------
def analyze_weakness(db: Session, user_id: int, user=None) -> dict:
    """基于用户全部错题，分析薄弱主题并给出学习建议。优先 LLM，无 key 降级本地。"""
    mistakes = list_mistakes(db, user_id)
    # 高频薄弱主题：未掌握且错误次数（review_count 高表示反复错）
    weak = [m for m in mistakes if not m.mastered and (m.subject or m.error_reason)]
    subject_counter: dict[str, int] = {}
    for m in weak:
        key = m.subject or "未分类"
        subject_counter[key] = subject_counter.get(key, 0) + 1
    weak_subjects = sorted(subject_counter.keys(), key=lambda k: -subject_counter[k])[:5]

    if is_llm_enabled(user) and mistakes:
        try:
            return {
                "analysis": _remote_analyze(mistakes, user),
                "mode": "llm",
                "weak_subjects": weak_subjects,
            }
        except Exception:  # noqa: BLE001
            pass
    return {
        "analysis": _local_analyze(mistakes, weak_subjects),
        "mode": "local",
        "weak_subjects": weak_subjects,
    }


def _remote_analyze(mistakes: list[Mistake], user=None) -> str:
    lines = []
    for i, m in enumerate(mistakes[:30], 1):
        lines.append(
            f"{i}. 主题={m.subject or '未分类'} | 题目={m.question} | "
            f"错误原因={m.error_reason or '（未填）'} | 已掌握={m.mastered}"
        )
    corpus = "\n".join(lines)
    prompt = (
        "你是一位学习诊断专家。下面是一名学生的错题记录（含主题、错误原因、是否掌握）。\n"
        "请分析其薄弱点，给出：① 主要问题（分点，2-4 条）；"
        "② 推荐学习路径（按优先级列出应先补哪些主题）；③ 一句鼓励。\n"
        "请用清晰分点的中文回答。\n\n错题记录：\n" + corpus
    )
    return chat_completion(
        user,
        system_prompt="你是 KnowledgeGraph AI 的学习诊断专家。",
        user_prompt=prompt,
        temperature=0.4,
        timeout=60,
    )


def _local_analyze(mistakes: list[Mistake], weak_subjects: list[str]) -> str:
    if not mistakes:
        return "暂无错题记录，继续学习并积累错题后，我就能帮你分析薄弱点了。"
    total = len(mistakes)
    unmastered = sum(1 for m in mistakes if not m.mastered)
    lines = [
        "【学习薄弱点分析（本地模式）】",
        f"你共有 {total} 条错题，其中 {unmastered} 条尚未掌握。",
    ]
    if weak_subjects:
        lines.append("高频薄弱主题：" + "、".join(weak_subjects))
    lines.append("")
    lines.append("推荐学习路径：")
    for i, s in enumerate(weak_subjects, 1):
        lines.append(f"  {i}. 优先复习「{s}」相关基础概念，再回来重做对应错题。")
    lines.append("")
    lines.append("提示：在「API 设置」中配置有效的自有 LLM Key 后，将由 AI 生成更深入的个性化诊断与建议。")
    return "\n".join(lines)
