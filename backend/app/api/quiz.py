"""智能出题路由（Phase 8）。

提供：基于知识库 / 错题本 / 知识图谱生成练习题目，以及提交作答判分。
所有操作按当前用户隔离（AI 宪法第五章）。
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.quiz import (
    QuizGenerateRequest,
    QuizGenerateResponse,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from app.services import quiz_generator as svc

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/generate", response_model=QuizGenerateResponse)
def generate_quiz(
    payload: QuizGenerateRequest,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> dict:
    """基于所选来源（知识库/错题本/图谱）生成练习题目。"""
    try:
        return svc.generate_quiz(
            db,
            current_user.id,
            sources=payload.sources,
            count=payload.count,
            subject=payload.subject,
            q_types=payload.q_types,
            user=current_user,
        )
    except LookupError:
        raise HTTPException(
            status_code=400,
            detail="暂无可用学习资料。请先上传知识库文档、记录错题或构建知识图谱后再出题。",
        )


@router.post("/grade", response_model=QuizSubmitResponse)
def grade_quiz(
    payload: QuizSubmitRequest,
    db: DbSession = None,
    current_user: CurrentUser = None,
) -> dict:
    """提交作答判分；答错的题自动回写错题本。"""
    if not payload.answers:
        raise HTTPException(status_code=400, detail="作答内容不能为空")
    return svc.grade_quiz(db, current_user.id, payload.answers)
