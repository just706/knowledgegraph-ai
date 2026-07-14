"""知识图谱构建与查询（Phase 5）。

负责将抽取的实体/关系落库，并提供可视化所需的图数据查询。
所有操作按 user_id 隔离。
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.graph import Entity, Relation
from app.services.graph_extractor import GraphData, extract_graph

# 用户可标注的关系类型
MANUAL_RELATION_TYPES = ["属于", "包含", "相关", "对比", "因果", "举例", "用于", "其他"]


def build_graph(db: Session, user_id: int, chunks: Iterable[str], user=None) -> GraphData:
    """抽取并落库用户图谱；返回本次构建的图数据。

    采用"合并"策略：已存在同名实体则累加 mention_count；
    已存在相同三元组则累加 weight，避免重复构建时数据膨胀。
    仅处理 source='auto' 的关系，用户手动标注(manual)的关系始终保留。
    user 用于解析其 LLM 凭证（图谱语义抽取按其自有 key 计费）。
    """
    data = extract_graph(chunks, user=user)
    if not data.entities:
        return data

    # 加载已有实体，建立 name -> Entity 映射
    existing = {
        e.name: e for e in db.scalars(select(Entity).where(Entity.user_id == user_id)).all()
    }
    name_to_entity: dict[str, Entity] = dict(existing)

    for ent in data.entities:
        if ent.name in name_to_entity:
            name_to_entity[ent.name].mention_count += ent.mentions
        else:
            e = Entity(
                user_id=user_id,
                name=ent.name,
                label=ent.label,
                mention_count=ent.mentions,
            )
            db.add(e)
            db.flush()  # 拿到 id
            name_to_entity[ent.name] = e

    # 关系合并（仅 auto 来源；manual 由用户维护）
    existing_rels = {
        (r.source_id, r.target_id, r.relation): r
        for r in db.scalars(
            select(Relation).where(Relation.user_id == user_id, Relation.source == "auto")
        ).all()
    }
    for rel in data.relations:
        src = name_to_entity.get(rel.source)
        tgt = name_to_entity.get(rel.target)
        if not src or not tgt or src.id == tgt.id:
            continue
        key = (src.id, tgt.id, rel.relation)
        if key in existing_rels:
            existing_rels[key].weight += rel.weight
        else:
            r = Relation(
                user_id=user_id,
                source_id=src.id,
                target_id=tgt.id,
                relation=rel.relation,
                weight=rel.weight,
                source="auto",
            )
            db.add(r)
    db.commit()
    return data


def add_manual_relation(
    db: Session, user_id: int, source_id: int, target_id: int, relation: str
) -> Relation:
    """用户手动创建一条关系（标注）。返回新建/已存在的关系。

    复用 auto 同三元组（若存在则升级为 manual 并保留权重），避免重复边。
    """
    if source_id == target_id:
        raise ValueError("不能将实体关联到自身")
    if relation not in MANUAL_RELATION_TYPES:
        raise ValueError(f"不支持的关系类型：{relation}")

    # 校验实体归属
    src = db.get(Entity, source_id)
    tgt = db.get(Entity, target_id)
    if not src or not tgt or src.user_id != user_id or tgt.user_id != user_id:
        raise ValueError("实体不存在或无权限")

    # 查找已存在的同三元组（无论来源）
    existing = db.scalars(
        select(Relation).where(
            Relation.user_id == user_id,
            Relation.source_id == source_id,
            Relation.target_id == target_id,
            Relation.relation == relation,
        )
    ).first()
    if existing:
        existing.source = "manual"
        db.commit()
        return existing

    r = Relation(
        user_id=user_id,
        source_id=source_id,
        target_id=target_id,
        relation=relation,
        weight=1,
        source="manual",
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def delete_relation(db: Session, user_id: int, relation_id: int) -> None:
    """删除一条关系（仅限当前用户）。"""
    r = db.get(Relation, relation_id)
    if r is None or r.user_id != user_id:
        raise ValueError("关系不存在或无权限")
    db.delete(r)
    db.commit()


def get_graph(db: Session, user_id: int, min_weight: int = 1) -> dict:
    """返回可视化所需的图数据（节点 + 边）。

    节点：实体（含 label、mentions、degree）。
    边：关系（含 relation 类型、weight）。
    """
    entities = db.scalars(select(Entity).where(Entity.user_id == user_id)).all()
    relations = db.scalars(select(Relation).where(Relation.user_id == user_id)).all()

    degree: dict[int, int] = defaultdict(int)
    nodes = []
    for e in entities:
        nodes.append(
            {
                "id": e.id,
                "name": e.name,
                "label": e.label,
                "mentions": e.mention_count,
                "degree": 0,  # 稍后填充
            }
        )
        degree[e.id] = 0

    edges = []
    for r in relations:
        if r.weight < min_weight:
            continue
        if r.source_id not in degree or r.target_id not in degree:
            continue
        edges.append(
            {
                "id": r.id,
                "source": r.source_id,
                "target": r.target_id,
                "relation": r.relation,
                "weight": r.weight,
                "source_type": r.source,
            }
        )
        degree[r.source_id] += 1
        degree[r.target_id] += 1

    for n in nodes:
        n["degree"] = degree.get(n["id"], 0)

    return {"nodes": nodes, "edges": edges, "entity_count": len(nodes), "relation_count": len(edges)}


def clear_graph(db: Session, user_id: int) -> int:
    """清空用户图谱（删除所有实体与关系）。返回删除的实体数。"""
    ent_count = db.scalars(
        select(Entity).where(Entity.user_id == user_id)
    ).all()
    n = len(ent_count)
    db.execute(delete(Relation).where(Relation.user_id == user_id))
    db.execute(delete(Entity).where(Entity.user_id == user_id))
    db.commit()
    return n
