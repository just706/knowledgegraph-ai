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


def build_graph(db: Session, user_id: int, chunks: Iterable[str]) -> GraphData:
    """抽取并落库用户图谱；返回本次构建的图数据。

    采用"合并"策略：已存在同名实体则累加 mention_count；
    已存在相同三元组则累加 weight，避免重复构建时数据膨胀。
    """
    data = extract_graph(chunks)
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

    # 关系合并
    existing_rels = {
        (r.source_id, r.target_id, r.relation): r
        for r in db.scalars(select(Relation).where(Relation.user_id == user_id)).all()
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
            )
            db.add(r)
    db.commit()
    return data


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
