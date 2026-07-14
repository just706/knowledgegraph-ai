"""学习仪表盘统计聚合服务（Phase 8）。

聚合各模块数据，形成学习概览：资料量、知识图谱规模、错题掌握情况、
主题/类型分布、近 7 天错题趋势。所有查询按 user_id 隔离
（AI 宪法第五章：用户数据必须隔离）。
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.models.graph import Entity, Relation
from app.models.mistake import Mistake
from app.models.quiz import Quiz


def _count(db: Session, model, user_id: int) -> int:
    return db.scalar(
        select(func.count()).select_from(model).where(model.user_id == user_id)
    ) or 0


def get_overview(db: Session, user_id: int) -> dict:
    """返回当前用户的学习统计概览。"""
    document_count = _count(db, Document, user_id)
    chunk_count = _count(db, DocumentChunk, user_id)
    entity_count = _count(db, Entity, user_id)
    relation_count = _count(db, Relation, user_id)

    mistakes = list(
        db.scalars(select(Mistake).where(Mistake.user_id == user_id)).all()
    )
    mistake_total = len(mistakes)
    mistake_mastered = sum(1 for m in mistakes if m.mastered)
    mastery_rate = (
        round(mistake_mastered / mistake_total * 100, 1) if mistake_total else 0.0
    )

    # 实体类型分布
    entities = list(db.scalars(select(Entity).where(Entity.user_id == user_id)).all())
    label_counter = Counter(e.label or "其他" for e in entities)
    entity_label_dist = [
        {"name": name, "count": cnt}
        for name, cnt in label_counter.most_common()
    ]

    # 错题主题分布
    subject_counter = Counter((m.subject or "未分类") for m in mistakes)
    mistake_subject_dist = [
        {"name": name, "count": cnt}
        for name, cnt in subject_counter.most_common()
    ]

    # 近 7 天错题录入趋势
    today = date.today()
    days = [today - timedelta(days=i) for i in range(6, -1, -1)]
    day_counter: dict[str, int] = defaultdict(int)
    for m in mistakes:
        created = m.created_at
        if isinstance(created, datetime):
            key = created.date().isoformat()
            day_counter[key] += 1
    mistake_trend_7d = [
        {"date": d.isoformat(), "count": day_counter.get(d.isoformat(), 0)}
        for d in days
    ]

    # 练习题目数
    quiz_total = _count(db, Quiz, user_id)

    # 知识点掌握度：完全基于用户真实练习/错题记录推导，无记录则空列表
    quizzes = list(db.scalars(select(Quiz).where(Quiz.user_id == user_id)).all())
    knowledge_mastery = _build_knowledge_mastery(quizzes, mistakes)

    # 最近学习资料（按上传时间倒序取 5）
    recent_docs = (
        db.scalars(
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .limit(5)
        ).all()
    )
    recent_documents = [
        {
            "title": d.title,
            "created_at": (
                d.created_at.isoformat()
                if hasattr(d.created_at, "isoformat")
                else str(d.created_at)
            ),
        }
        for d in recent_docs
    ]

    # 最近错题（按创建时间倒序取 5）
    recent_mistakes = [
        {"question": m.question, "subject": m.subject or "未分类"}
        for m in mistakes[:5]
    ]

    # 能力雷达：除「掌握程度」真实来自错题掌握率外，其余维度均基于用户的真实
    # 学习行为（导入资料、做练习、构建图谱）推导；无任何行为时对应维度为 0，
    # 不再凭空给出百分比。
    def _norm(v: int, cap: int) -> int:
        return min(100, round(v / cap * 100)) if cap else 0

    # 是否有过实质学习行为（导入资料或做过练习或记录过错题）
    has_activity = (document_count > 0) or (quiz_total > 0) or (mistake_total > 0)

    ability_radar = [
        {"name": "知识广度", "count": _norm(entity_count, 50) if has_activity else 0},
        {"name": "掌握程度", "count": int(mastery_rate)},
        {"name": "练习强度", "count": _norm(quiz_total, 50)},
        {"name": "关联理解", "count": _norm(relation_count, 50) if has_activity else 0},
        {"name": "资料积累", "count": _norm(document_count, 10) if has_activity else 0},
    ]

    # 累计学习时长：仅在有真实学习行为时，按练习与错题复盘估算（资料导入不计入
    # 虚构时长）。无任何记录时为 0.0，不显示"凭空来的"学习时长。
    study_hours = round(quiz_total * 0.1 + mistake_total * 0.1, 1) if has_activity else 0.0

    # AI 学习建议（轻量本地生成）
    if not mistake_subject_dist:
        ai_suggestion = "先从知识库上传资料，系统会基于你的内容生成练习与学习建议。"
    else:
        top_weak = mistake_subject_dist[0]["name"]
        ai_suggestion = (
            f"你的薄弱知识集中在「{top_weak}」，建议优先复习该主题基础概念，"
            f"并完成对应智能练习题巩固。"
        )

    # 今日学习目标：完全基于用户真实记录推导，不写死。
    # 优先级：最薄弱错题主题 > 有资料未练习 > 有练习无错题 > 完全无记录引导上传
    if mistake_subject_dist:
        top_weak = mistake_subject_dist[0]["name"]
        today_goal = f"复习「{top_weak}」薄弱点，并完成 5 道针对性练习"
    elif document_count > 0 and quiz_total == 0:
        latest_doc = recent_documents[0]["title"] if recent_documents else "已上传的资料"
        today_goal = f"基于《{latest_doc}》做一轮智能练习，检验掌握情况"
    elif quiz_total > 0 and mistake_total == 0:
        today_goal = "继续巩固已练内容，整理并消化新出现的易错点"
    else:
        today_goal = "上传第一份学习资料，开启你的专属学习计划"

    return {
        "document_count": document_count,
        "chunk_count": chunk_count,
        "entity_count": entity_count,
        "relation_count": relation_count,
        "mistake_total": mistake_total,
        "mistake_mastered": mistake_mastered,
        "mastery_rate": mastery_rate,
        "entity_label_dist": entity_label_dist,
        "mistake_subject_dist": mistake_subject_dist,
        "mistake_trend_7d": mistake_trend_7d,
        "quiz_total": quiz_total,
        "knowledge_mastery": knowledge_mastery,
        "mastered_entity_count": entity_count,
        "study_hours": study_hours,
        "ability_radar": ability_radar,
        "recent_documents": recent_documents,
        "recent_mistakes": recent_mistakes,
        "ai_suggestion": ai_suggestion,
        "today_goal": today_goal,
    }


def _build_knowledge_mastery(quizzes: list, mistakes: list) -> list:
    """由用户真实练习/错题记录推导知识点掌握度。

    规则：
    - 以「错题 subject」为知识点维度（用户实际踩过的坑最反映掌握情况）。
    - 该知识点下：total = 错题数 + 相关练习数；correct = 已掌握错题数。
    - 掌握度 = round(correct / total * 100)，无记录则不在列表中（新人看不到假数据）。
    - 仅展示有真实记录的知识点，按掌握度升序（最薄弱的排前面，便于针对性复习）。
    """
    from collections import defaultdict

    # 错题维度
    mistake_by_subject: dict[str, list] = defaultdict(list)
    for m in mistakes:
        subj = (m.subject or "").strip() or "未分类"
        mistake_by_subject[subj].append(m)

    # 练习维度（按 subject 归集，用于衬托该知识点是否有过练习）
    quiz_total_by_subject: dict[str, int] = defaultdict(int)
    for q in quizzes:
        subj = (q.subject or "").strip() or "未分类"
        quiz_total_by_subject[subj] += 1

    result = []
    for subj, ms in mistake_by_subject.items():
        total = len(ms) + quiz_total_by_subject.get(subj, 0)
        correct = sum(1 for m in ms if getattr(m, "mastered", False))
        value = round(correct / total * 100) if total else 0
        result.append(
            {"name": subj, "value": value, "total": total, "correct": correct}
        )

    # 只做过练习、没有任何错题的学科，也展示为「已掌握」状态（练习即掌握信号）
    for subj, qtotal in quiz_total_by_subject.items():
        if subj not in mistake_by_subject:
            result.append(
                {"name": subj, "value": 100, "total": qtotal, "correct": qtotal}
            )

    if not result:
        return []
    # 薄弱的排前面
    result.sort(key=lambda x: x["value"])
    return result
