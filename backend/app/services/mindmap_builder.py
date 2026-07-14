"""思维导图（学习地图）生成（Phase 6）。

将 Phase 5 的知识图谱"投影"成树形思维导图，便于按层次学习。
所有操作按 user_id 隔离。

生成策略（可降级）：
- 有 OPENAI_API_KEY 时：把实体/关系清单交给 LLM，生成语义化的学习路径树；
- 无 key 时（默认本地演示）：用图算法自动生成层次树——
  以"关联度/频次最高"的核心概念为根，按类型（概念/方法/结构/术语）分叉，
  BFS 将邻居逐层归类，形成可折叠的思维导图。
"""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models.graph import Entity, Relation

# 实体类型 → 思维导图分支名
LABEL_BRANCHES = {
    "概念": "核心概念",
    "方法": "方法与技术",
    "结构": "结构与系统",
    "术语": "关键术语",
    "人物": "相关人物",
    "其他": "其他",
}

# 本地模式：按频次排序挑选根节点（中心主题）时使用的类型优先级
ROOT_PRIORITY = ["概念", "结构", "方法", "术语", "人物", "其他"]


@dataclass
class MindNode:
    """思维导图节点（可嵌套）。"""

    name: str
    kind: str = "topic"  # topic(分支) / leaf(实体)
    entity_id: int | None = None
    children: list["MindNode"] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "entity_id": self.entity_id,
            "meta": self.meta,
            "children": [c.to_dict() for c in self.children],
        }


def _build_adjacency(
    entities: list[Entity], relations: list[Relation]
) -> tuple[dict[int, set[int]], dict[int, str], dict[int, int]]:
    """从实体/关系构建无向邻接表、label 映射、mentions 映射。"""
    adj: dict[int, set[int]] = defaultdict(set)
    labels: dict[int, str] = {}
    mentions: dict[int, int] = {}
    for e in entities:
        adj[e.id] = set()
        labels[e.id] = e.label
        mentions[e.id] = e.mention_count
    for r in relations:
        if r.source_id in adj and r.target_id in adj:
            adj[r.source_id].add(r.target_id)
            adj[r.target_id].add(r.source_id)
    return adj, labels, mentions


def _select_roots(
    entities: list[Entity], labels: dict[int, str], mentions: dict[int, int]
) -> list[Entity]:
    """挑选中心主题（根）实体：优先高频、高关联度的核心概念。"""
    if not entities:
        return []
    # 计算每个实体的度数
    adj, _, _ = _build_adjacency(entities, [])
    degree = {e.id: len(adj[e.id]) for e in entities}

    # 评分：mentions * 2 + degree，优先 label 优先级高的类型
    def score(e: Entity) -> tuple[int, int, int]:
        prio = ROOT_PRIORITY.index(e.label) if e.label in ROOT_PRIORITY else len(ROOT_PRIORITY)
        return (mentions[e.id] * 2 + degree[e.id], -prio, -e.id)

    ordered = sorted(entities, key=score, reverse=True)
    # 取关联度最高且确有关联的单一中心主题
    top = [ordered[0]] if ordered else []
    return top


def _local_mindmap(db: Session, user_id: int) -> MindNode:
    """本地图算法生成思维导图树（单一中心主题 + 按类型分层的分支）。

    策略：
    1. 选关联度/频次最高的实体作为中心主题（root 的子节点之一）；
    2. 其余所有实体按 label 归入"核心概念/方法与技术/结构与系统/关键术语"等分支；
    3. 与中心主题有直接关系的实体，额外作为中心主题的"直接相关"子节点；
    4. 避免堆出庞大的"其他概念"分支。
    """
    entities = db.scalars(select(Entity).where(Entity.user_id == user_id)).all()
    relations = db.scalars(select(Relation).where(Relation.user_id == user_id)).all()

    if not entities:
        return MindNode(name="我的学习地图", kind="root", children=[])

    adj, labels, mentions = _build_adjacency(entities, relations)
    roots = _select_roots(entities, labels, mentions)
    root = MindNode(name="我的学习地图", kind="root")

    if not roots:
        # 退化情况：直接按 label 分分支展示
        for label in ROOT_PRIORITY:
            group = [e for e in entities if e.label == label]
            if not group:
                continue
            branch = MindNode(name=LABEL_BRANCHES.get(label, label), kind="topic")
            for e in sorted(group, key=lambda x: mentions[x.id], reverse=True):
                branch.children.append(
                    MindNode(name=e.name, kind="leaf", entity_id=e.id,
                             meta={"mentions": e.mention_count, "label": e.label})
                )
            root.children.append(branch)
        return root

    center = roots[0]
    center_node = MindNode(name=center.name, kind="topic", entity_id=center.id)

    # 与中心主题有直接关系的实体集合
    direct = set(adj[center.id])

    # 分支：按 label 聚合所有非中心实体
    branches: dict[str, MindNode] = {}
    for e in entities:
        if e.id == center.id:
            continue
        label = e.label
        branch_name = LABEL_BRANCHES.get(label, label)
        if branch_name not in branches:
            branches[branch_name] = MindNode(name=branch_name, kind="topic")
        leaf = MindNode(
            name=e.name, kind="leaf", entity_id=e.id,
            meta={"mentions": mentions.get(e.id, 0), "label": label},
        )
        branches[branch_name].children.append(leaf)

    # 把"直接相关"的实体提升为 center 的直接子节点（便于从主题展开学习）
    related_branch = MindNode(name="直接相关", kind="topic")
    for nb in sorted(direct, key=lambda x: mentions.get(x, 0), reverse=True):
        if nb == center.id:
            continue
        related_branch.children.append(
            MindNode(
                name=_entity_name(db, nb), kind="leaf", entity_id=nb,
                meta={"mentions": mentions.get(nb, 0), "label": labels.get(nb, "其他")},
            )
        )
    if related_branch.children:
        center_node.children.append(related_branch)

    # 其余按 label 分支挂在中心主题下
    for branch in branches.values():
        if branch.children:
            # 分支内按频次排序
            branch.children.sort(key=lambda c: c.meta.get("mentions", 0), reverse=True)
            center_node.children.append(branch)

    root.children.append(center_node)
    return root


def _entity_name(db: Session, entity_id: int) -> str:
    e = db.get(Entity, entity_id)
    return e.name if e else "?"


def _llm_mindmap(db: Session, user_id: int) -> MindNode | None:
    """LLM 增强：生成更语义化的学习路径树。无 key 或失败返回 None。"""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return None
    try:
        import openai  # noqa: F401
    except ImportError:
        return None

    entities = db.scalars(select(Entity).where(Entity.user_id == user_id)).all()
    relations = db.scalars(select(Relation).where(Relation.user_id == user_id)).all()
    if not entities:
        return MindNode(name="我的学习地图", kind="root", children=[])

    ents = [{"name": e.name, "label": e.label, "mentions": e.mention_count} for e in entities]
    rels = [
        {"source": _entity_name(db, r.source_id), "relation": r.relation,
         "target": _entity_name(db, r.target_id)}
        for r in relations
    ]
    prompt = (
        "你是一个学习路径规划助手。下面是用户资料中抽取出的知识实体与关系，"
        "请将它们组织成一张层次化的思维导图 JSON，便于循序渐进地学习。\n"
        "要求：根节点为整体主题；第二层为主要知识分支；再往下为具体概念。\n"
        "直接使用已给出的实体名称，不要编造新概念。\n"
        "只输出 JSON，格式：\n"
        '{"name":"主题","children":[{"name":"分支","children":[{"name":"概念"}]}]}\n'
        f"实体：{json.dumps(ents, ensure_ascii=False)}\n"
        f"关系：{json.dumps(rels, ensure_ascii=False)}\n"
    )
    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key, base_url=settings.OPENAI_BASE_URL)
        resp = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            response_format={"type": "json_object"},
            timeout=30,
        )
        text = resp.choices[0].message.content or "{}"
        data = json.loads(text)
        return _dict_to_mind(data)
    except Exception:  # noqa: BLE001  LLM 失败降级到本地算法
        return None


def _dict_to_mind(data: dict) -> MindNode:
    """将 LLM 返回的 dict 转为 MindNode（带防御）。"""
    children_data = data.get("children", []) or []
    node = MindNode(
        name=str(data.get("name", "主题")),
        kind="root" if not children_data else "topic",
    )
    for child in children_data:
        node.children.append(_dict_to_mind(child))
    # 叶子节点标记为 leaf，便于前端区分
    if not node.children:
        node.kind = "leaf"
    return node


def get_mindmap(db: Session, user_id: int) -> dict:
    """返回当前用户的思维导图树。

    优先尝试 LLM 生成；失败或无 key 时回退到本地图算法。
    同时返回生成模式（llm / local）便于前端提示。
    """
    mode = "local"
    tree = _llm_mindmap(db, user_id)
    if tree is None:
        tree = _local_mindmap(db, user_id)
    else:
        mode = "llm"

    # 统计叶子数
    def count_leaves(n: MindNode) -> int:
        if not n.children:
            return 1
        return sum(count_leaves(c) for c in n.children)

    return {
        "mode": mode,
        "root": tree.to_dict(),
        "node_count": count_leaves(tree),
    }
