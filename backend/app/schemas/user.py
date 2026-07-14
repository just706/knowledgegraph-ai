"""用户相关校验/响应模型。

遵循 AI 宪法第三章：保持模块化；输入与响应模型分离，避免泄露敏感字段。
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    display_name: str | None = Field(default=None, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    display_name: str | None
    is_active: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LLMSettingsUpdate(BaseModel):
    """用户更新自有 LLM 凭证（仅本人可改）。

    所有字段均可选；传 null/空字符串表示清空该项。
    api_key 写入数据库前会被加密，返回时脱敏。
    """

    provider: str | None = Field(default=None, description="厂商标识，如 openai/deepseek/anthropic/gemini")
    api_key: str | None = Field(default=None, description="自有 LLM API Key，留空表示清除")
    base_url: str | None = Field(default=None, description="API 接入点，如 https://api.deepseek.com/v1")
    model: str | None = Field(default=None, description="模型名，如 deepseek-chat")


class LLMSettingsView(BaseModel):
    """返回给前端的凭证状态（不泄露明文 key，只给脱敏预览与模式信息）。"""

    has_own_key: bool = False
    # 当前选中的厂商标识（用于前端下拉回显）
    provider: str | None = None
    # 脱敏后的 key 预览，如 "sk-ab12****ef78"，无则空
    api_key_masked: str | None = None
    base_url: str | None = None
    model: str | None = None
    # 本次 LLM 调用将使用的计费模式：own（用户自己）/ fallback（全局兜底）/ none（不可用）
    effective_mode: str = "none"
    # 厂商预设列表（前端下拉用，不含敏感信息）
    provider_presets: list[dict] | None = None
