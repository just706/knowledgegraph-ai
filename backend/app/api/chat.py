"""对话路由（Phase 4 RAG 问答）。

所有操作按当前用户隔离（AI 宪法第五章）。问答基于用户已上传并向量化的资料切片。
"""
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.rag import answer as rag_answer

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: DbSession, current_user: CurrentUser) -> ChatResponse:
    """基于用户知识库进行 RAG 问答。"""
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    result = rag_answer(
        db=db,
        user_id=current_user.id,
        query=payload.query,
        top_k=payload.top_k or 5,
    )
    return ChatResponse(**result)
