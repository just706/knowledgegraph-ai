"""路由依赖：认证与数据库注入。"""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import get_db

DbSession = Annotated[Session, Depends(get_db)]
