"""FastAPI 应用入口。

Phase 1 目标：可运行的后端骨架，提供 Swagger 文档，所有配置走环境变量。
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.graph import router as graph_router
from app.api.health import router as health_router
from app.api.mindmap import router as mindmap_router
from app.api.mistakes import router as mistakes_router
from app.api.users import router as users_router
from app.config import settings


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """应用生命周期：启动时建表（MVP 阶段用 create_all 占位，后续改用迁移）。"""
    from app.database import Base, engine
    from app import models  # noqa: F401 确保模型被导入注册

    Base.metadata.create_all(bind=engine)
    yield


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

