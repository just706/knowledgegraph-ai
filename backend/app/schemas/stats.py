"""学习仪表盘统计响应模型（Phase 8）。"""
from pydantic import BaseModel


class CountItem(BaseModel):
    name: str
    count: int


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
