"""错题本相关校验与响应模型（Phase 7）。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MistakeCreate(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    my_answer: str = Field(default="", max_length=4000)
    correct_answer: str = Field(default="", max_length=4000)
    error_reason: str = Field(default="", max_length=4000)
    subject: str = Field(default="", max_length=64)


class MistakeReviewRequest(BaseModel):
    """复习动作：schedule=开始复习（进入间隔计划）；confirm=确认本次复习已答对。"""
    action: str = "schedule"  # schedule | confirm


class MistakeUpdate(BaseModel):
    question: str | None = Field(default=None, max_length=4000)
    my_answer: str | None = Field(default=None, max_length=4000)
    correct_answer: str | None = Field(default=None, max_length=4000)
    error_reason: str | None = Field(default=None, max_length=4000)
    subject: str | None = Field(default=None, max_length=64)
    mastered: bool | None = None
    review_stage: int | None = None
    next_review_at: datetime | None = None
    last_review_at: datetime | None = None


class MistakeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    question: str
    my_answer: str
    correct_answer: str
    error_reason: str
    subject: str
    mastered: bool
    review_count: int
    review_stage: int
    next_review_at: datetime | None
    last_review_at: datetime | None
    created_at: datetime
    updated_at: datetime


class MistakeExplainResponse(BaseModel):
    explanation: str          # AI 生成的错题解析
    mode: str                 # llm / local


class WeaknessAnalysisResponse(BaseModel):
    analysis: str             # AI 生成的薄弱点分析 + 推荐学习路径
    mode: str                 # llm / local
    weak_subjects: list[str]  # 高频薄弱主题（本地模式也会给出）
