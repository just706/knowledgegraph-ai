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
from app.services.llm_client import chat_completion, is_llm_enabled


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

# 通用概念后缀（跨领域适用，不再仅限 AI/计算机）
_CONCEPT_SUFFIXES = (
    # 方法论类
    "方法", "方法论", "理论", "定理", "定律", "原理", "假说", "学说",
    "模型", "模式", "范式", "框架", "体系", "机制", "策略", "方案",
    # 结构与系统
    "系统", "结构", "架构", "网络", "平台", "模块", "组件",
    # 学科与技术
    "算法", "函数", "公式", "方程", "定理", "引理", "推论",
    "技术", "工艺", "流程", "协议", "标准", "规范",
    # 概念与术语
    "效应", "现象", "过程", "周期", "阶段", "类型", "分类",
    "主义", "思想", "学派", "运动", "革命", "时代",
    # 领域通用（经济/政治/法律/社会学）
    "政策", "制度", "体制", "机制", "市场", "契约", "权利", "义务",
    "法则", "规则", "准则", "定义", "概念", "命题", "论证",
    "关系", "特征", "属性", "结构",
    # 历史/人文
    "文明", "文化", "帝国", "王朝", "战争", "条约", "宣言",
    "论", "学", "派", "观", "说",
)
# 英文术语
_ENGLISH_TERMS = re.compile(r"^[A-Za-z][A-Za-z0-9\-\.+]{1,}$")
# 中文停用词（常见非概念词）
_CN_STOP = {
    "我们", "他们", "它们", "这种", "这些", "那些", "一种", "以及", "或者",
    "因为", "所以", "如果", "但是", "然而", "例如", "包括", "通过", "对于",
    "由于", "其中", "目前", "主要", "可以", "需要", "进行", "实现", "使用",
    "基于", "采用", "提出", "表明", "得到", "使得", "从而", "此外", "同时",
    "第一", "第二", "第三", "第四", "第五", "一个", "一种", "这个", "那个",
    "时候", "方面", "问题", "方法", "研究", "分析", "结果", "数据", "模型",
    "具有", "存在", "不同", "之间", "非常", "更加", "可能", "能够", "是否",
    "一些", "很多", "所有", "每个", "任何", "整个", "其他", "分别",
    "如何", "怎么", "什么", "为什么", "不是", "没有", "不会", "不可",
    "机制", "理论", "规范", "标准", "规则", "概念", "定义", "关系", "结构", "特征",
    "过程", "方法", "技术", "策略", "政策", "制度", "系统", "网络",
    "结构", "模型", "模式", "类型", "分类", "周期", "阶段",
}
# 弱关系类型（仅本地降级使用，LLM 模式禁止）
_COOCCUR_RELATION = "相关"


def _normalize_entity(name: str) -> str:
    """清洗并归一化实体名。"""
    name = name.strip().strip("（）()[]【】\"'\"'.,，。、：:；;")
    return name


def _extract_cn_entities(text: str) -> list[str]:
    """从中文文本启发式抽取候选实体。

    高质量实体判定：
    1. 必须以某个"概念后缀"结尾，或本身就是英文术语；
    2. 长度限制在 2~12 字；
    3. 向前扩展修饰成分最多 8 字，构成"修饰+核心"实体名；
    4. 过滤以量词、介词、副词开头的碎片。
    """
    # 禁止出现在实体开头的词（量词/介词/副词/助词）
    _BAD_STARTS = re.compile(
        r"^(以|对|被|把|将|在|从|由|与|和|或|及|并|等|的|了|着|过"
        r"|一|两|三|四|五|六|七|八|九|十|百|千|万"
        r"|这|那|哪|每|各|某|其|之|所|而|则|也|又|都|就|才|只|不"
        r"|为|使|让|给|向|朝|比|跟|同|于|自|到|去|来|有|无|用|以)"
    )
    candidates: list[str] = []
    sentences = re.split(r"[，。！？；：、\n\r（）()\[\]【】\".!?;:\s]+", text)
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        for suf in _CONCEPT_SUFFIXES:
            for m in re.finditer(re.escape(suf), sent):
                start = m.start()
                # 单字后缀：要求前面至少有一个汉字（避免"讨论""教学"等）
                if len(suf) == 1 and (start == 0 or not ("\u4e00" <= sent[start - 1] <= "\u9fff")):
                    continue
                # 向前扩展取修饰成分（汉字/字母），最多 8 字
                i = start - 1
                max_back = 8
                while i >= 0 and (start - i) <= max_back and (
                    sent[i].isalnum() or "\u4e00" <= sent[i] <= "\u9fff"
                ) and not sent[i] in "的是与被在于由及或并通过用为来去从向朝。，！？；：":
                    i -= 1
                ent = sent[i + 1 : start + len(suf)]
                # 去掉开头的引导词/量词/介词/动词（递归直到无法再去掉）
                _CLEAN_PREFIX_RE = re.compile(
                    r"^(依赖|基于|通过|采用|使用|进行|利用|借助|依靠|包含|包括|实现"
                    r"|一种|一个|一些|某个|这个|那种|那些"
                    r"|其中|此外|另外|同时|首先|其次|最后"
                    r"|例如|比如|以及|还有|主张|强调|提出|认为|指出|表明"
                    r"|通过|用于|用来|可以|需要|能够|必须|应当|应该"
                    r"|主要|重要|关键|核心|基本|根本|本质|显著)"
                )
                prev = None
                while ent != prev:
                    prev = ent
                    ent = _CLEAN_PREFIX_RE.sub("", ent)
                # 过滤以介词/量词/副词开头的碎片
                if _BAD_STARTS.match(ent):
                    continue
                if not ent or ent in _CN_STOP:
                    continue
                # 剪掉结尾的虚词
                ent = re.sub(r"(的|了|着|过|与|和|及|或|并|等|中|上|下|内|外|是|为|被|将|把|对|在|从|由)$", "", ent)
                # 单字后缀（论/学/派/观/说）需要更长的最小长度，避免匹配到常见词
                min_len = 3 if len(suf) == 1 else 2
                if min_len <= len(ent) <= 12 and ent not in _CN_STOP:
                    # 跳过以英文字母开头的（英文术语由 _extract_en_entities 负责）
                    if not ent[0].isascii() or not ent[0].isalpha():
                        candidates.append(ent)
    # 去重：如果实体A是实体B的子串且位置重叠，保留更长的
    # 例如 "社会契约论" 和 "社会契约" 同时出现，只保留 "社会契约论"
    result: list[str] = []
    # 按出现顺序排序（保持稳定）
    for i, c in enumerate(candidates):
        keep = True
        for j, other in enumerate(candidates):
            if i != j and c in other and len(c) < len(other):
                # c 是 other 的子串，且 c 在原文中的位置与 other 重叠则丢弃 c
                # 简单判断：如果 c 是 other 的子串（且 other 更长），保留 other
                keep = False
                break
        if keep:
            result.append(c)
    return result


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


# 人文/古诗类资料专用：书名号包裹的篇名、著作
_BOOK_TITLE_RE = re.compile(r"[《〈]([^《〈》〉]{1,20})[》〉]")
# 常见朝代/时期专名（人文资料高频，且不以概念后缀结尾）
_DYNASTY_TERMS = {
    "先秦", "春秋", "战国", "秦代", "汉代", "西汉", "东汉", "三国", "魏晋", "南北朝",
    "隋代", "唐代", "唐朝", "宋代", "北宋", "南宋", "元代", "明代", "清代", "清朝",
    "初唐", "盛唐", "中唐", "晚唐", "近代", "现代", "当代",
}
# 已知重要诗人/词人/文学家（高置信人名白名单，避免从文本滑窗切出碎片）
_KNOWN_AUTHORS = {
    "李白", "杜甫", "白居易", "王维", "孟浩然", "王昌龄", "王之涣", "李商隐", "杜牧",
    "苏轼", "辛弃疾", "李清照", "柳永", "陆游", "欧阳修", "王安石", "陶渊明", "屈原",
    "司马迁", "曹操", "曹植", "陶渊明", "韩愈", "柳宗元", "刘禹锡", "岑参", "高适",
    "李煜", "纳兰性德", "龚自珍", "文天祥", "范仲淹", "晏殊", "晏几道", "周邦彦",
    "温庭筠", "韦应物", "王勃", "杨万里", "范成大", "陈子昂", "贺知章", "张九龄",
}
# 常见古诗篇名关键词（高置信著作，配合书名号使用；此处作为兜底白名单）
_KNOWN_POEMS = {
    "静夜思", "登高", "春望", "望岳", "使至塞上", "饮酒", "归园田居", "念奴娇",
    "水调歌头", "声声慢", "如梦令", "破阵子", "永遇乐", "蜀道难", "将进酒",
    "茅屋为秋风所破歌", "琵琶行", "长恨歌", "观沧海", "龟虽寿", "观书有感",
}


def _extract_human_entities(text: str) -> list[tuple[str, str]]:
    """人文/古诗类资料的实体重提取通道（不依赖概念后缀）。

    仅保留**高置信度**专名，避免从长段无标点文本滑窗切出碎片噪声：
    1. 书名号包裹的篇名/著作（如《静夜思》《登高》）→ 著作
    2. 明确的朝代/时期专名（唐代、盛唐…）→ 时期
    3. 已知诗人/词人白名单（李白、杜甫…）→ 人物
    不做通用"2~4字滑窗"抽取（会产生大量碎片，已弃用）。
    """
    found: list[tuple[str, str]] = []

    # 1) 书名号著作
    for m in _BOOK_TITLE_RE.finditer(text):
        title = m.group(1).strip()
        if 1 <= len(title) <= 16 and title not in _CN_STOP:
            found.append((title, "著作"))

    # 2) 朝代/时期
    for d in _DYNASTY_TERMS:
        if d in text:
            found.append((d, "时期"))

    # 3) 已知诗人/词人白名单
    for name in _KNOWN_AUTHORS:
        if name in text:
            found.append((name, "人物"))

    # 4) 已知篇名白名单（兜底，防止书名号被漏解析）
    for name in _KNOWN_POEMS:
        if name in text:
            found.append((name, "著作"))

    return found


def _local_extract(chunks: Iterable[str]) -> GraphData:
    """本地抽取：实体词频 + 同一句子内的实体共现关系（降低噪声）。

    增强：
    1. 实体数限制提升到 150（更丰富的后缀覆盖）
    2. 共现权重阈值提升到 3（更严格，减少随机连线）
    3. 按句子拆分确保关系语义内聚
    """
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
            # 人文/古诗类通道：书名号著作、朝代、2~4字专名（不依赖概念后缀）
            # 放在 seen/uniq 定义之后，避免引用未初始化变量
            human = _extract_human_entities(sent)
            for hname, hlabel in human:
                if hname and hname not in entity_counter:
                    label_map[hname] = hlabel
                if hname and hname not in seen:
                    seen.add(hname)
                    uniq.append(hname)
            # 限制单句实体规模，避免稠密全连接
            if len(uniq) > 10:
                uniq = uniq[:10]
            for e in uniq:
                entity_counter[e] += 1
                if e.isascii():
                    label_map[e] = "术语"
                elif any(e.endswith(s) for s in ("系统", "结构", "架构", "网络", "平台", "框架", "模块", "体系")):
                    label_map[e] = "结构"
                elif any(e.endswith(s) for s in ("算法", "方法", "方法论", "策略", "机制", "技术", "方案", "流程")):
                    label_map[e] = "方法"
                elif any(e.endswith(s) for s in ("定律", "定理", "理论", "原理", "公式", "方程", "引理", "推论")):
                    label_map[e] = "理论"
                elif any(e.endswith(s) for s in ("主义", "思想", "学派", "学说", "运动")):
                    label_map[e] = "学派"
                elif any(e.endswith(s) for s in ("效应", "现象", "革命", "时代", "周期")):
                    label_map[e] = "事件"
                else:
                    label_map[e] = "概念"
            # 句内共现（两两组合）
            for a, b in combinations(uniq, 2):
                cooccur[frozenset((a, b))] += 1

    data = GraphData()
    for name, cnt in entity_counter.most_common(150):
        data.entities.append(
            ExtractedEntity(name=name, label=label_map.get(name, "概念"), mentions=cnt)
        )
    # 仅保留权重≥2 的共现关系，降噪同时提升图谱连通性（从 3→2）
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
    "你是一个专业的知识图谱抽取助手。你的任务是从任意领域的文本中抽取高质量的知识实体与关系三元组。\n\n"
    "## 领域识别与策略\n"
    "先判断文本所属领域（如：计算机/AI、数学、物理、化学、生物、医学、历史、哲学、经济学、社会学、文学、法学等），"
    "然后采用该领域的专业知识进行抽取。\n\n"
    "## 实体抽取规则\n"
    "1. **只抽取有独立知识价值的核心概念**：学科术语、理论名称、重要人物、关键方法、核心结构、经典著作、历史事件、定律定理等。\n"
    "2. **不要抽取**：通用描述词（如\"研究\"\"分析\"\"问题\"）、代词、数量词、章节标题、作者署名、引用编号。\n"
    "3. **实体名必须完整、规范**：如\"卷积神经网络\"而非\"卷积\"，\"相对论\"而非\"相对\"。\n"
    "4. **每篇文档实体数量控制在 8-30 个**，宁缺毋滥。若文本信息密度低，可少于 8 个。\n\n"
    "## 关系抽取规则\n"
    "1. **只保留有明确语义的关系**：如\"属于\"\"提出\"\"证明\"\"用于\"\"包含\"\"影响\"\"反对\"\"推导\"\"改进\"\"应用于\"等。\n"
    "2. **禁止使用\"相关\"作为关系**——必须写明具体的语义关系。\n"
    "3. **关系必须双向可读**：source 和 target 都必须已在 entities 中出现。\n"
    "4. **一个关系只连接两个实体，不要串联多个**。\n"
    "5. **若两个实体之间没有明确关系，不要强行连线**。宁可少画，不可乱画。\n\n"
    "## 输出格式\n"
    "只输出 JSON，格式：\n"
    "{\"entities\":[{\"name\":\"实体名\",\"label\":\"领域分类\"}],"
    "\"relations\":[{\"source\":\"源实体名\",\"relation\":\"具体关系\",\"target\":\"目标实体名\"}]}\n\n"
    "## label 分类体系（根据领域灵活选用）\n"
    "- 理论/定理/定律、方法/算法/技术、结构/系统/框架、人物/学派、著作/文献、概念/术语、"
    "事件/现象、工具/平台、公式/模型、其他\n\n"
    "## 示例\n"
    "输入：\"卷积神经网络（CNN）由 Yann LeCun 于 1998 年提出，通过卷积层提取图像特征，"
    "配合池化层降维，最后经全连接层输出分类结果。反向传播算法用于训练网络权重。\"\n"
    "输出：{\"entities\":[{\"name\":\"卷积神经网络\",\"label\":\"结构/系统/框架\"},"
    "{\"name\":\"Yann LeCun\",\"label\":\"人物/学派\"},{\"name\":\"卷积层\",\"label\":\"概念/术语\"},"
    "{\"name\":\"池化层\",\"label\":\"概念/术语\"},{\"name\":\"全连接层\",\"label\":\"概念/术语\"},"
    "{\"name\":\"反向传播\",\"label\":\"方法/算法/技术\"},{\"name\":\"图像特征\",\"label\":\"概念/术语\"}],"
    "\"relations\":[{\"source\":\"Yann LeCun\",\"relation\":\"提出\",\"target\":\"卷积神经网络\"},"
    "{\"source\":\"卷积神经网络\",\"relation\":\"包含\",\"target\":\"卷积层\"},"
    "{\"source\":\"卷积神经网络\",\"relation\":\"包含\",\"target\":\"池化层\"},"
    "{\"source\":\"卷积神经网络\",\"relation\":\"包含\",\"target\":\"全连接层\"},"
    "{\"source\":\"卷积层\",\"relation\":\"提取\",\"target\":\"图像特征\"},"
    "{\"source\":\"反向传播\",\"relation\":\"用于\",\"target\":\"卷积神经网络\"}]}"
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


# 需过滤的无意义实体名（纯数字、单字母、太短的中文等）
_INVALID_ENTITY_RE = re.compile(r"^(\d+|[a-zA-Z]{1,2}|.{1}|[，。！？；：、\s]+)$")
# 通用的无意义"关系"词，LLM 偶尔会偷懒输出
_BAD_RELATIONS = {"相关", "关联", "有关", "联系", "关系", "涉及", "包含关系", "有关系"}


def _llm_extract(chunks: Iterable[str], user=None) -> GraphData | None:
    """调用 LLM 抽取；失败时返回 None 以降级。

    增强：
    1. 分块输入（长文档分段抽取后合并去重）
    2. 后处理过滤无效实体和"相关"类弱关系
    3. 实体名规范化去重
    """
    if not is_llm_enabled(user):
        return None
    text = "\n".join(chunks)
    if not text.strip():
        return None

    # 长文本分块抽取（每块不超过 6000 字符），避免 LLM 输出截断
    max_chunk_size = 6000
    all_entities: list[ExtractedEntity] = []
    all_relations: list[ExtractedRelation] = []

    text_chunks = [text[i : i + max_chunk_size] for i in range(0, len(text), max_chunk_size)]

    for chunk in text_chunks:
        if not chunk.strip():
            continue
        try:
            content = chat_completion(
                user,
                system_prompt=_LLM_SYSTEM,
                user_prompt=chunk,
                temperature=0,
                timeout=90,
            )
            parsed = json.loads(content)

            # 解析实体
            for e in parsed.get("entities", []):
                name = _normalize_entity(e.get("name", ""))
                if not name or _INVALID_ENTITY_RE.match(name):
                    continue
                label = (e.get("label", "") or "概念").strip()
                all_entities.append(ExtractedEntity(name=name, label=label))

            # 解析关系
            for r in parsed.get("relations", []):
                s = _normalize_entity(r.get("source", ""))
                t = _normalize_entity(r.get("target", ""))
                rel = (r.get("relation", "") or "").strip()
                if not s or not t or s == t:
                    continue
                # 过滤"相关"类弱关系
                if rel in _BAD_RELATIONS:
                    continue
                all_relations.append(ExtractedRelation(source=s, relation=rel, target=t))
        except Exception:
            continue  # 单块失败不影响其他块

    if not all_entities:
        return None

    # 合并去重：同名实体合并，保留首次出现的 label
    data = GraphData()
    seen_names: dict[str, str] = {}
    for ent in all_entities:
        if ent.name not in seen_names:
            seen_names[ent.name] = ent.label
            data.entities.append(ExtractedEntity(name=ent.name, label=ent.label))

    # 关系去重：同一对实体只保留一条关系（取首次出现的）
    seen_rels: set[tuple] = set()
    entity_names = {e.name for e in data.entities}
    for rel in all_relations:
        if rel.source not in entity_names or rel.target not in entity_names:
            continue
        key = (rel.source, rel.relation, rel.target)
        if key not in seen_rels:
            seen_rels.add(key)
            data.relations.append(rel)

    return data if (data.entities or data.relations) else None


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

def extract_graph(chunks: Iterable[str], user=None) -> GraphData:
    """抽取图谱数据：优先 LLM（用户自有 key），失败/无 key 时本地降级。"""
    llm_data = _llm_extract(chunks, user=user)
    if llm_data is not None and (llm_data.entities or llm_data.relations):
        return llm_data
    return _local_extract(chunks)
