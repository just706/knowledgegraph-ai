"""用户模型（Phase 2 用户系统的基础表）。

MVP 优先：先定义最小用户实体，后续按迁移管理扩展（AI 宪法第五章：结构修改必须通过迁移）。
用户数据隔离通过 user_id 行级隔离实现。
"""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.crypto import decrypt_field, encrypt_field
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True)

    # 用户私有 LLM 凭证（密文存储于 _llm_api_key，明文经属性透明解密）
    # 仅当用户填写后，LLM 调用才扣该用户的额度；否则回退到全局 .env 兜底 key。
    _llm_api_key: Mapped[str | None] = mapped_column("llm_api_key", String(512), nullable=True)
    llm_base_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    # 厂商标识：openai / deepseek / qwen / zhipu / moonshot / minimax / ollama / anthropic / gemini / custom
    # 仅作协议路由与预设回填用，非敏感字段，明文存储即可。
    llm_provider: Mapped[str | None] = mapped_column(String(64), nullable=True)

    @property
    def llm_api_key(self) -> str | None:
        """明文 API Key（从密文透明解密）。"""
        return decrypt_field(self._llm_api_key)

    @llm_api_key.setter
    def llm_api_key(self, value: str | None) -> None:
        self._llm_api_key = encrypt_field(value)

    @property
    def has_own_llm_key(self) -> bool:
        """是否已配置自有 Key（用于前端判断是否启用个人额度）。"""
        return bool(self._llm_api_key)
