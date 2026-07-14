"""数据库引擎与会话管理（SQLAlchemy 2.0）。

MVP 阶段使用 SQLite 占位，保持简单（AI 宪法第八章：简单方案优先）。
后续切换 PostgreSQL 只需修改 DATABASE_URL 环境变量，无需改代码。
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# SQLite 需要 connect_args；PostgreSQL 不需要，这里做兼容判断。
_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(settings.DATABASE_URL, connect_args=_connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：提供数据库会话，请求结束自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
