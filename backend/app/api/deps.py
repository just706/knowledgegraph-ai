"""路由依赖：认证与数据库注入。"""
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User

DbSession = Annotated[Session, Depends(get_db)]

# tokenUrl 指向登录接口，供 Swagger "Authorize" 使用
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_PREFIX}/users/login")


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: DbSession) -> User:
    """从 JWT 解析当前用户，无效则 401（AI 宪法第五章：用户数据权限控制）。"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或过期的凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    subject = decode_access_token(token)
    if subject is None:
        raise credentials_exception
    user = db.get(User, int(subject))
    if user is None or not user.is_active:
        raise credentials_exception
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_current_admin_user(current_user: CurrentUser) -> User:
    """管理员权限校验：非 admin 用户访问管理接口返回 403。"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return current_user


CurrentAdminUser = Annotated[User, Depends(get_current_admin_user)]
