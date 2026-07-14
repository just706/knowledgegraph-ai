"""智能出题相关校验与响应模型（Phase 8）。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class QuizGenerateRequest(BaseModel):
    """生成练习题目的请求。

    sources：题目来源，可多选，支持：
      - "knowledge" 基于知识库文档切片
      - "mistakes"  基于错题本未掌握题目（薄弱点定向出题）
      - "graph"     基于知识图谱实体与关系
    """

    sources: list[str] = Field(
        default=["knowledge", "mistakes", "graph"],
        description="题目来源，可多选：knowledge / mistakes / graph",
    )
    count: int = Field(default=5, ge=1, le=20, description="生成题目数量")
    subject: str | None = Field(default=None, max_length=64, description="限定主题/学科，可选")
    q_types: list[str] = Field(
        default=["choice"],
        description="题型，可多选：choice / fill / judgment / short",
    )


class QuizQuestion(BaseModel):
    """单道生成题（返回给前端用于答题）。"""

    source: str = "knowledge"
    q_type: str = "choice"
    subject: str = ""
    question: str
    options: list[str] = []
    answer: str
    explanation: str = ""
    difficulty: int = 2          # 难度 1-5（星数）
    knowledge_point: str = ""    # 关联知识点


class QuizGenerateResponse(BaseModel):
    questions: list[QuizQuestion]
    mode: str  # llm / local
    message: str = ""


class QuizAnswerItem(BaseModel):
    """用户提交的一道作答。"""

    question: str
    user_answer: str
    answer: str          # 原题目的标准答案（前端回传以便比对）
    source: str = "knowledge"
    subject: str = ""
    explanation: str = ""


class QuizSubmitRequest(BaseModel):
    """提交整张练习卷的作答用于判分。"""

    answers: list[QuizAnswerItem]


class QuizSubmitResponse(BaseModel):
    total: int
    correct: int
    wrong: int
    score: int                     # 百分制得分
    wrong_items: list[QuizAnswerItem]  # 答错的题（用于回写错题本）


class QuizOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    source: str
    q_type: str
    subject: str
    question: str
    options: str
    answer: str
    explanation: str
    created_at: datetime
