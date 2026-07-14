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
