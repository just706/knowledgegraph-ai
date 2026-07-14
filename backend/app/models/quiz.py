"""智能出题模型（Phase 8）。

一条记录代表系统为用户生成的一道练习题目。题目由 LLM 基于用户的知识库
文档切片、错题本薄弱点、知识图谱实体关系三种来源之一生成，并保留来源
标记以便溯源（AI 宪法：答案可溯源）。

用户数据隔离：quiz 带 user_id，所有查询按当前用户过滤。
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Quiz(Base):
    """系统为用户智能生成的一道练习题。"""

    __tablename__ = "quizzes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), index=True, nullable=False
    )
    # 题目来源：knowledge(知识库文档) / mistakes(错题本薄弱点) / graph(知识图谱)
    source: Mapped[str] = mapped_column(String(16), default="knowledge")
    # 题型：choice(单选) / fill(填空) / judgment(判断) / short(简答)
    q_type: Mapped[str] = mapped_column(String(16), default="choice")
    subject: Mapped[str] = mapped_column(String(64), default="")  # 主题/学科标签
    question: Mapped[str] = mapped_column(Text, nullable=False)    # 题干
    # 选项 JSON 字符串（选择题用），如 ["A. ...", "B. ..."]
    options: Mapped[str] = mapped_column(Text, default="[]")
    answer: Mapped[str] = mapped_column(Text, nullable=False)      # 正确答案/要点
    explanation: Mapped[str] = mapped_column(Text, default="")      # 解析/出处说明
    # 难度 1-5（星数）与关联知识点（前端展示用）
    difficulty: Mapped[int] = mapped_column(Integer, default=2)
    knowledge_point: Mapped[str] = mapped_column(String(128), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Quiz {self.id} source={self.source!r}>"
