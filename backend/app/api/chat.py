"""对话路由（Phase 4 RAG 问答 + 多会话历史）。

所有操作按当前用户隔离（AI 宪法第五章）。问答基于用户已上传并向量化的资料切片，
并通过 chat_sessions / chat_messages 两张表持久化，支持多会话与分页查看历史。
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.deps import CurrentUser, DbSession
from app.models.chat import ChatMessage, ChatSession
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatMessageOut,
    ChatSessionOut,
    ChatSessionCreate,
    PaginatedChatSessions,
    PaginatedChatMessages,
)
from app.services.rag import answer as rag_answer

router = APIRouter(prefix="/chat", tags=["chat"])


# ---------------------------------------------------------------------------
# 会话管理
# ---------------------------------------------------------------------------
@router.get("/sessions", response_model=PaginatedChatSessions)
def list_sessions(
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedChatSessions:
    """分页列出当前用户的对话会话（按最近更新倒序）。"""
    from sqlalchemy import func, select

    total = db.scalar(
        select(func.count()).select_from(ChatSession).where(ChatSession.user_id == current_user.id)
    )
    stmt = (
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list(db.scalars(stmt).all())
    return PaginatedChatSessions(
        total=total or 0,
        page=page,
        page_size=page_size,
        items=[ChatSessionOut.model_validate(r) for r in rows],
    )


@router.post("/sessions", response_model=ChatSessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: ChatSessionCreate, db: DbSession, current_user: CurrentUser
) -> ChatSessionOut:
    """显式新建一个空白会话（标题可空，首条消息后自动命名）。"""
    session = ChatSession(user_id=current_user.id, title=payload.title or "新对话")
    db.add(session)
    db.commit()
    db.refresh(session)
    return ChatSessionOut.model_validate(session)


@router.get("/sessions/{session_id}", response_model=PaginatedChatMessages)
def get_session_messages(
    session_id: int,
    db: DbSession,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
) -> PaginatedChatMessages:
    """分页获取某会话的消息（按时间正序），用于回看历史。"""
    from sqlalchemy import func, select

    session = _get_owned_session(db, session_id, current_user.id)
    total = db.scalar(
        select(func.count())
        .select_from(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.user_id == current_user.id)
    )
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id, ChatMessage.user_id == current_user.id)
        .order_by(ChatMessage.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = list(db.scalars(stmt).all())
    return PaginatedChatMessages(
        total=total or 0,
        page=page,
        page_size=page_size,
        items=[ChatMessageOut.model_validate(r) for r in rows],
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: int, db: DbSession, current_user: CurrentUser) -> None:
    """删除一个会话及其全部消息（仅本人）。"""
    session = _get_owned_session(db, session_id, current_user.id)
    db.query(ChatMessage).filter(
        ChatMessage.session_id == session_id, ChatMessage.user_id == current_user.id
    ).delete()
    db.delete(session)
    db.commit()


# ---------------------------------------------------------------------------
# 问答（带持久化）
# ---------------------------------------------------------------------------
@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, db: DbSession, current_user: CurrentUser) -> ChatResponse:
    """基于用户知识库进行 RAG 问答，并持久化到会话历史。

    - session_id 为空：自动新建会话（标题取首条问题前 30 字）。
    - session_id 非空：追加到该会话（需属于当前用户）。
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="问题不能为空")

    # 解析/创建会话
    session = None
    if payload.session_id:
        session = _get_owned_session(db, payload.session_id, current_user.id)
    else:
        session = ChatSession(user_id=current_user.id, title=payload.query.strip()[:30] or "新对话")
        db.add(session)
        db.flush()

    # 持久化用户提问
    user_msg = ChatMessage(
        session_id=session.id, user_id=current_user.id, role="user", content=payload.query
    )
    db.add(user_msg)

    result = rag_answer(
        db=db,
        user_id=current_user.id,
        query=payload.query,
        top_k=payload.top_k or 5,
        mode=payload.mode or "normal",
        user=current_user,
        history=payload.history,
    )

    # 持久化助手回答
    assistant_msg = ChatMessage(
        session_id=session.id,
        user_id=current_user.id,
        role="assistant",
        content=result["answer"],
        sources_json=_serialize_sources(result.get("sources", [])),
        gen_mode=result.get("mode"),
    )
    db.add(assistant_msg)
    db.commit()

    return ChatResponse(
        session_id=session.id,
        session_title=session.title,
        answer=result["answer"],
        sources=result.get("sources", []),
        mode=result.get("mode", "local"),
    )


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------
def _get_owned_session(db: DbSession, session_id: int, user_id: int) -> ChatSession:
    """取属于当前用户的会话，否则 404。"""
    from sqlalchemy import select

    session = db.scalar(
        select(ChatSession).where(
            ChatSession.id == session_id, ChatSession.user_id == user_id
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="会话不存在或无权访问")
    return session


def _serialize_sources(sources: list[dict]) -> str | None:
    """将引用来源列表序列化为 JSON 字符串存储；空则存 None。"""
    if not sources:
        return None
    import json

    return json.dumps(sources, ensure_ascii=False)
