"""测试公共 fixture：每个测试使用独立的临时 SQLite 数据库，避免数据污染。

通过重建数据库引擎与建表，保证测试间相互隔离（AI 宪法第七章：测试不破坏已有功能）。
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, SessionLocal, engine


@pytest.fixture(autouse=True)
def isolated_db(tmp_path):
    db_path = tmp_path / "test_kg_ai.db"
    test_engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        pool_pre_ping=True,
    )
    Base.metadata.create_all(bind=test_engine)

    TestSessionLocal = sessionmaker(
        bind=test_engine, autocommit=False, autoflush=False
    )

    import app.database as db_mod

    orig_engine = db_mod.engine
    orig_session = db_mod.SessionLocal

    db_mod.engine = test_engine
    db_mod.SessionLocal = TestSessionLocal

    yield

    db_mod.engine = orig_engine
    db_mod.SessionLocal = orig_session
    test_engine.dispose()
