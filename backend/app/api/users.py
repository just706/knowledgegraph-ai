"""用户路由（注册登录占位，Phase 2 完整实现 JWT）。

MVP Phase 1 仅搭建骨架与路由结构，注册/登录业务逻辑在 Phase 2 实现。
当前提供结构占位，保证应用可启动、Swagger 文档完整。
"""
from fastapi import APIRouter

from app.api.deps import DbSession
from app.schemas.user import UserCreate, UserLogin, UserPublic, Token

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserPublic, status_code=201)
def register(payload: UserCreate, db: DbSession) -> UserPublic:
    # TODO(Phase 2): 密码哈希、创建用户、用户数据隔离校验
    raise NotImplementedError("用户注册将在 Phase 2 实现")


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: DbSession) -> Token:
    # TODO(Phase 2): 校验凭证、签发 JWT
    raise NotImplementedError("用户登录将在 Phase 2 实现")
