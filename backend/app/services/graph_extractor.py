"""知识图谱抽取服务（Phase 5）。

从用户资料切片中抽取实体（Entity）与关系（Relation）。

设计遵循"可降级"原则（与 Phase 4 一致）：
- 配置了 LLM key 时，调用 LLM 做结构化抽取（实体类型 + 关系三元组），更准确。
- 未配置 key 时，降级为本地算法：
  * 实体：从文本中识别"名词性短语"（中英文混合，基于词典/词频/标点启发式）。
  * 关系：基于同一切片内的实体共现，推断"相关/属于"等弱关系，供图谱可视化。

本地抽取不依赖任何外部服务，保证开发环境也能完整跑通图谱功能。
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from itertools import combinations
from typing import Iterable

import requests

from app.config import settings


@dataclass
class ExtractedEntity:
    name: str
    label: str = "概念"
    mentions: int = 1


@dataclass
class ExtractedRelation:
    source: str
    relation: str
    target: str
    weight: int = 1


@dataclass
class GraphData:
    entities: list[ExtractedEntity] = field(default_factory=list)
    relations: list[ExtractedRelation] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 本地抽取（无 LLM 依赖）
# ---------------------------------------------------------------------------

# 常见中文学术/技术名词后缀，用于启发式识别实体
_CONCEPT_SUFFIXES = (
    "网络", "模型", "算法", "机制", "学习", "误差", "梯度", "函数", "定理",
    "定律", "理论", "系统", "结构", "特征", "向量", "矩阵", "网络", "处理器",
    "模块", "框架", "方法", "策略", "过程", "技术", "语言", "协议", "数据集",
)
# 英文技术词（全小写匹配）
_ENGLISH_TERMS = re.compile(r"^[A-Za-z][A-Za-z0-9\-\.+]{1,}$")
# 中文实词候选（去除单字与纯标点/停用词）
_CN_STOP = {
    "我们", "他们", "它们", "这种", "这些", "那些", "一种", "以及", "或者",
    "因为", "所以", "如果", "但是", "然而", "例如", "包括", "通过", "对于",
    "由于", "其中", "目前", "主要", "可以", "需要", "进行", "实现", "使用",
    "基于", "采用", "提出", "表明", "得到", "使得", "从而", "此外", "同时",
    "第一", "第二", "第三", "第四", "第五", "一个", "一种", "这个", "那个",
    "时候", "方面", "问题", "方法", "研究", "分析", "结果", "数据", "模型",
}
# 弱关系类型（共现推断）
_COOCCUR_RELATION = "相关"


def _normalize_entity(name: str) -> str:
    """清洗并归一化实体名。"""
    name = name.strip().strip("（）()[]【】\"'\"'.,，。、：:；;")
    return name


def _extract_cn_entities(text: str) -> list[str]:
    """从中文文本启发式抽取候选实体。

    高质量实体判定（降低噪声，避免"深度学习是机器学习"这类长串碎片）：
    1. 必须以某个"概念后缀"结尾（网络/模型/算法/机制…），或本身就是英文术语；
    2. 长度限制在 2~10 字，且不含句末虚词；
    3. 向前扩展修饰成分（形容词/名词）最多 6 字，构成"修饰+核心"实体名。
    """
    candidates: list[str] = []
    sentences = re.split(r"[，。！？；：、\n\r（）()\[\]【】\".!?;:\s]+", text)
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        for suf in _CONCEPT_SUFFIXES:
            for m in re.finditer(re.escape(suf), sent):
                start = m.start()
                # 向前扩展取修饰成分（汉字/字母），最多 6 字
                i = start - 1
                while i >= 0 and (
                    sent[i].isalnum() or "\u4e00" <= sent[i] <= "\u9fff"
                ) and not sent[i] in "的是与被在对于由及或并":
                    i -= 1
                ent = sent[i + 1 : start + len(suf)]
                # 去掉开头的引导性动词，保留核心概念
                ent = re.sub(r"^(依赖|基于|通过|采用|使用|进行|利用|借助|依靠|包含|包括|实现)", "", ent)
                # 去掉结尾的修饰性动词短语
                ent = re.sub(r"进行表示学习$", "表示学习", ent)
                if 2 <= len(ent) <= 10 and ent not in _CN_STOP:
                    candidates.append(ent)
    return [c for c in candidates if c]


def _extract_en_entities(text: str) -> list[str]:
    """抽取英文术语（如 Transformer、CNN、LSTM、RNN）。"""
    found: list[str] = []
    for m in re.finditer(r"[A-Za-z][A-Za-z0-9\-\.+]{1,}", text):
        tok = m.group(0)
        if _ENGLISH_TERMS.match(tok) and tok.lower() not in {
            "the", "and", "for", "with", "via", "from", "into", "that", "this",
        }:
            found.append(tok)
    return found


def _has_concept_suffix(name: str) -> bool:
    """判断实体是否以概念后缀结尾（区分"实实体"与碎片）。"""
    return any(name.endswith(s) for s in _CONCEPT_SUFFIXES)


def _local_extract(chunks: Iterable[str]) -> GraphData:
    """本地抽取：实体词频 + 同一句子内的实体共现关系（降低噪声）。"""
    entity_counter: Counter[str] = Counter()
    cooccur: dict[frozenset, int] = defaultdict(int)
    label_map: dict[str, str] = {}

    for chunk in chunks:
        # 按句子拆分，仅在句内做实体共现
        sentences = re.split(r"[。！？；\n\r]+", chunk)
        for sent in sentences:
            sent = sent.strip()
            if not sent:
                continue
            cn = _extract_cn_entities(sent)
            en = _extract_en_entities(sent)
            raw = [_normalize_entity(e) for e in cn + en]
            # 仅保留"实实体"（带概念后缀或英文术语）
            ents = [e for e in raw if e and (_has_concept_suffix(e) or e.isascii())]
            # 句内去重
            seen = set()
            uniq = []
            for e in ents:
                if e not in seen:
                    seen.add(e)
                    uniq.append(e)
            # 限制单句实体规模，避免稠密全连接
            if len(uniq) > 12:
                uniq = uniq[:12]
            for e in uniq:
                entity_counter[e] += 1
                if e.isascii():
                    label_map[e] = "术语"
                elif any(e.endswith(s) for s in ("网络", "结构", "系统", "框架", "模块")):
                    label_map[e] = "结构"
                elif any(e.endswith(s) for s in ("算法", "方法", "策略", "机制", "技术")):
                    label_map[e] = "方法"
                elif any(e.endswith(s) for s in ("定律", "定理", "理论", "模型", "函数", "语言")):
                    label_map[e] = "概念"
                else:
                    label_map[e] = "概念"
            # 句内共现（两两组合）
            for a, b in combinations(uniq, 2):
                cooccur[frozenset((a, b))] += 1

    data = GraphData()
    for name, cnt in entity_counter.most_common(200):
        data.entities.append(
            ExtractedEntity(name=name, label=label_map.get(name, "概念"), mentions=cnt)
        )
    # 仅保留权重≥2 的共现关系，进一步降噪
    name_set = {e.name for e in data.entities}
    for pair, w in cooccur.items():
        if w < 2:
            continue
        (a, b) = tuple(pair)
        if a in name_set and b in name_set:
            data.relations.append(
                ExtractedRelation(source=a, relation=_COOCCUR_RELATION, target=b, weight=w)
            )
    return data


# ---------------------------------------------------------------------------
# LLM 抽取（配置 key 时）
# ---------------------------------------------------------------------------

_LLM_SYSTEM = (
    "你是一个知识图谱抽取助手。从给定文本中抽取实体与关系三元组。"
    "只输出 JSON，格式：{\"entities\":[{\"name\":\"\",\"label\":\"\"}],"
    "\"relations\":[{\"source\":\"\",\"relation\":\"\",\"target\":\"\"}]}。"
    "label 取值：概念/方法/结构/术语/人物/其他。"
)

_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "knowledge_graph",
        "schema": {
            "type": "object",
            "properties": {
                "entities": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "label": {"type": "string"},
                        },
                    },
                },
                "relations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "source": {"type": "string"},
                            "relation": {"type": "string"},
                            "target": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}


def _llm_extract(chunks: Iterable[str]) -> GraphData | None:
    """调用 LLM 抽取；失败时返回 None 以降级。"""
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        return None
    text = "\n".join(chunks)
    if not text.strip():
        return None
    try:
        resp = requests.post(
            f"{settings.OPENAI_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": settings.LLM_MODEL,
                "messages": [
                    {"role": "system", "content": _LLM_SYSTEM},
                    {"role": "user", "content": text[:12000]},
                ],
                "response_format": _SCHEMA,
                "temperature": 0,
            },
            timeout=60,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        data = GraphData()
        for e in parsed.get("entities", []):
            name = _normalize_entity(e.get("name", ""))
            if name:
                data.entities.append(
                    ExtractedEntity(name=name, label=e.get("label", "概念"))
                )
        for r in parsed.get("relations", []):
            s, t = _normalize_entity(r.get("source", "")), _normalize_entity(r.get("target", ""))
            rel = r.get("relation", "相关") or "相关"
            if s and t and s != t:
                data.relations.append(
                    ExtractedRelation(source=s, relation=rel, target=t)
                )
        return data
    except Exception:  # noqa: BLE001 任意异常都降级到本地
        return None


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

def extract_graph(chunks: Iterable[str]) -> GraphData:
    """抽取图谱数据：优先 LLM，失败/无 key 时本地降级。"""
    llm_data = _llm_extract(chunks)
    if llm_data is not None and (llm_data.entities or llm_data.relations):
        return llm_data
    return _local_extract(chunks)
