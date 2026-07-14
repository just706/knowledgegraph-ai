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
    }
