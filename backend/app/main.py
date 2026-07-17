"""FastAPI 应用入口。

Phase 1 目标：可运行的后端骨架，提供 Swagger 文档，所有配置走环境变量。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.graph import router as graph_router
from app.api.health import router as health_router
from app.api.mindmap import router as mindmap_router
from app.api.mistakes import router as mistakes_router
from app.api.plan import router as plan_router
from app.api.quiz import router as quiz_router
from app.api.stats import router as stats_router
from app.api.users import router as users_router
from app.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：启动时建表（MVP 阶段用 create_all 占位，后续改用迁移）。"""
    from app.database import Base, engine
    from app import models  # noqa: F401 确保模型被导入注册

    Base.metadata.create_all(bind=engine)
    # 兼容已存在的 SQLite 库：create_all 不会给旧表追加新列，这里幂等补列。
    # 后续正式迁移工具就绪后可移除本段。
    _migrate_add_user_llm_columns(engine)
    _migrate_add_document_graph_columns(engine)
    _migrate_add_document_category_column(engine)
    _migrate_add_mistake_review_columns(engine)
    yield


def _migrate_add_user_llm_columns(engine) -> None:
    """为 users 表补齐 llm_api_key / llm_base_url / llm_model / role / created_at 列（若不存在）。"""
    expected = {
        "llm_api_key": "VARCHAR(512)",
        "llm_base_url": "VARCHAR(255)",
        "llm_model": "VARCHAR(128)",
        "llm_provider": "VARCHAR(64)",
        "role": "VARCHAR(16) DEFAULT 'user'",
        "created_at": "DATETIME",
    }
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(__import__("sqlalchemy").text("PRAGMA table_info(users)"))}
        for col, col_type in expected.items():
            if col not in existing:
                conn.execute(__import__("sqlalchemy").text(f"ALTER TABLE users ADD COLUMN {col} {col_type}"))
        conn.commit()


def _migrate_add_document_graph_columns(engine) -> None:
    """为 documents 表补齐 graph_status / graph_error 列（若不存在）。"""
    expected = {
        "graph_status": "VARCHAR(32) DEFAULT 'pending'",
        "graph_error": "TEXT",
    }
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(__import__("sqlalchemy").text("PRAGMA table_info(documents)"))}
        for col, col_type in expected.items():
            if col not in existing:
                conn.execute(__import__("sqlalchemy").text(f"ALTER TABLE documents ADD COLUMN {col} {col_type}"))
        conn.commit()


def _migrate_add_document_category_column(engine) -> None:
    """为 documents 表补齐 category 列（若不存在）。"""
    expected = {
        "category": "VARCHAR(64) DEFAULT '未分类'",
    }
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(__import__("sqlalchemy").text("PRAGMA table_info(documents)"))}
        for col, col_type in expected.items():
            if col not in existing:
                conn.execute(__import__("sqlalchemy").text(f"ALTER TABLE documents ADD COLUMN {col} {col_type}"))
        conn.commit()


def _migrate_add_mistake_review_columns(engine) -> None:
    """为 mistakes 表补齐间隔重复复习字段（若不存在）。"""
    expected = {
        "review_stage": "INTEGER DEFAULT 0",
        "next_review_at": "DATETIME",
        "last_review_at": "DATETIME",
    }
    with engine.connect() as conn:
        existing = {row[1] for row in conn.execute(__import__("sqlalchemy").text("PRAGMA table_info(mistakes)"))}
        for col, col_type in expected.items():
            if col not in existing:
                conn.execute(__import__("sqlalchemy").text(f"ALTER TABLE mistakes ADD COLUMN {col} {col_type}"))
        conn.commit()


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    description="基于 LLM + RAG + 知识图谱的智能学习助手（MVP Phase 1 骨架）",
    debug=settings.DEBUG,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册（MVP 阶段所有版本路由挂在 /api/v1 下）
app.include_router(health_router, prefix=settings.API_V1_PREFIX)
app.include_router(users_router, prefix=settings.API_V1_PREFIX)
app.include_router(documents_router, prefix=settings.API_V1_PREFIX)
app.include_router(chat_router, prefix=settings.API_V1_PREFIX)
app.include_router(graph_router, prefix=settings.API_V1_PREFIX)
app.include_router(mindmap_router, prefix=settings.API_V1_PREFIX)
app.include_router(mistakes_router, prefix=settings.API_V1_PREFIX)
app.include_router(quiz_router, prefix=settings.API_V1_PREFIX)
app.include_router(stats_router, prefix=settings.API_V1_PREFIX)
app.include_router(plan_router, prefix=settings.API_V1_PREFIX)
app.include_router(admin_router, prefix=settings.API_V1_PREFIX)

