"""通用响应模型。"""
from pydantic import BaseModel


class HealthCheck(BaseModel):
    status: str
    app_name: str
    version: str
