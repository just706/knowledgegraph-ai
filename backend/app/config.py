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

    # 用户私有凭证加密主密钥（用于加密存储用户各自的 LLM API Key）。
    # 生产环境务必单独配置；缺省时由 SECRET_KEY 派生（仅限本地开发）。
    LLM_KEY_MASTER: str = ""

    # 全局兜底 Key 开关：用户未配置自己的 Key 时，是否允许使用 .env 中的
    # OPENAI_API_KEY 作为兜底（即扣部署者的额度）。设为 False 则"没填 key 就用不了 LLM"。
    ALLOW_GLOBAL_LLM_FALLBACK: bool = True

    # 向量库
    CHROMA_PERSIST_DIR: str = "./chroma"

    # OCR：是否允许上传图片/扫描件（依赖本地 Tesseract 引擎，启动时探测）
    OCR_ENABLED: bool = True


# 知识图谱
NEO4J_URI: str = "bolt://localhost:7687"
NEO4J_USER: str = "neo4j"
NEO4J_PASSWORD: str = ""


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    # 用 parser 模块对 Tesseract 的运行时探测结果覆盖 OCR 开关，
    # 保证开关反映真实能力（未装引擎则自动禁用图片上传并提示）
    try:
        from app.services.parser import OCR_AVAILABLE as _OCR_AVAILABLE  # noqa: E402

        s.OCR_ENABLED = _OCR_AVAILABLE
    except Exception:  # noqa: BLE001 探测失败保持默认 True（由 parser 内部降级）
        pass
    return s


settings = get_settings()
