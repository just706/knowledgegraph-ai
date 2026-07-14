"""学习仪表盘统计响应模型（Phase 8）。"""
from pydantic import BaseModel


class CountItem(BaseModel):
    name: str
    count: int


class MasteryItem(BaseModel):
    name: str       # 知识点 / 学科
    value: int      # 掌握度 0-100，由真实练习/错题记录推导
    total: int      # 该知识点相关题目总数
    correct: int    # 已掌握/答对数量


class TrendItem(BaseModel):
    date: str      # YYYY-MM-DD
    count: int


class StatsOverview(BaseModel):
    # 概览卡片
    document_count: int
    chunk_count: int
    entity_count: int
    relation_count: int
    mistake_total: int
    mistake_mastered: int
    mastery_rate: float               # 0-100

    # 分布/趋势图
    entity_label_dist: list[CountItem]     # 实体类型分布
    mistake_subject_dist: list[CountItem]  # 错题主题分布
    mistake_trend_7d: list[TrendItem]      # 近 7 天错题录入趋势

    # 学习中心增强字段
    quiz_total: int = 0                     # 累计练习题目数
    knowledge_mastery: list[MasteryItem] = []  # 知识点掌握度（由真实练习/错题记录推导）
    mastered_entity_count: int = 0          # 已掌握知识点（实体）数（本地估算）
    study_hours: float = 0.0               # 累计学习时长（小时，本地估算）
    ability_radar: list[CountItem] = []     # 能力雷达：各维度得分 0-100
    recent_documents: list[dict] = []       # 最近学习资料（标题+时间）
    recent_mistakes: list[dict] = []        # 最近错题（题目+主题）
    ai_suggestion: str = ""                 # AI 学习建议（文本）
    today_goal: str = ""                    # 今日学习目标（基于用户真实记录推导）
