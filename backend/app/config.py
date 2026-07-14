"""应用配置：所有配置通过环境变量管理（AI 宪法第五章 / 开发计划 Agent 规则 3）。"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 应用
    APP_NAME: str = "KnowledgeGraph AI"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # 安全
    SECRET_KEY: str = "dev-secret-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # 数据库
    DATABASE_URL: str = "sqlite:///./kg_ai.db"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # AI（后续 Phase 启用）
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4o-mini"

    # 向量库
    CHROMA_PERSIST_DIR: str = "./chroma"

    # 知识图谱
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
