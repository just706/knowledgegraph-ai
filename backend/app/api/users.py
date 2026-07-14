"""用户路由：注册、登录、当前用户信息。

遵循 AI 宪法：
- 用户数据隔离（每个用户仅能访问自身数据）
- 密码不入库、不回传
- 异常输入友好提示
"""
from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, DbSession
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import (
    LLMSettingsUpdate,
    LLMSettingsView,
    Token,
    UserCreate,
    UserLogin,
    UserPublic,
)
from app.services.llm_client import get_provider_presets, resolve_credential

router = APIRouter(prefix="/users", tags=["users"])


def _mask_key(key: str | None) -> str | None:
    """将 API Key 脱敏为 sk-ab12****ef78 形式，避免泄露。"""
    if not key or len(key) < 8:
        return None
    return f"{key[:6]}****{key[-4:]}"


@router.post("/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: DbSession) -> UserPublic:
    # 用户数据隔离：邮箱唯一校验，避免越权/重复注册
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该邮箱已注册",
        )
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        display_name=payload.display_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return UserPublic.model_validate(user)


@router.post("/login", response_model=Token)
def login(payload: UserLogin, db: DbSession) -> Token:
    user = db.query(User).filter(User.email == payload.email).first()
    # 统一返回凭证错误，避免暴露邮箱是否存在
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="邮箱或密码错误",
        )
    access_token = create_access_token(subject=user.id)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserPublic)
def read_current_user(current_user: CurrentUser) -> UserPublic:
    # 受保护接口：需有效 JWT（由 get_current_user 校验）
    return UserPublic.model_validate(current_user)


@router.get("/me/llm-settings", response_model=LLMSettingsView)
def read_llm_settings(current_user: CurrentUser) -> LLMSettingsView:
    """读取当前用户的 LLM 凭证状态（key 脱敏，不泄露明文）。"""
    cred = resolve_credential(current_user)
    effective_mode = "none"
    if cred is not None:
        effective_mode = "own" if cred.is_user_owned else "fallback"
    return LLMSettingsView(
        has_own_key=current_user.has_own_llm_key,
        provider=current_user.llm_provider,
        api_key_masked=_mask_key(current_user.llm_api_key),
        base_url=current_user.llm_base_url,
        model=current_user.llm_model,
        effective_mode=effective_mode,
        provider_presets=get_provider_presets(),
    )


@router.put("/me/llm-settings", response_model=LLMSettingsView)
def update_llm_settings(
    payload: LLMSettingsUpdate, db: DbSession, current_user: CurrentUser
) -> LLMSettingsView:
    """更新当前用户的 LLM 凭证（仅本人）。

    - api_key 留空/null 表示清除；
    - 写入前自动加密存储；
    - 返回脱敏后的状态。
    """
    if payload.provider is not None:
        current_user.llm_provider = payload.provider or None
    if payload.api_key is not None:
        current_user.llm_api_key = payload.api_key or None
    if payload.base_url is not None:
        current_user.llm_base_url = payload.base_url or None
    if payload.model is not None:
        current_user.llm_model = payload.model or None
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    cred = resolve_credential(current_user)
    effective_mode = "none"
    if cred is not None:
        effective_mode = "own" if cred.is_user_owned else "fallback"
    return LLMSettingsView(
        has_own_key=current_user.has_own_llm_key,
        provider=current_user.llm_provider,
        api_key_masked=_mask_key(current_user.llm_api_key),
        base_url=current_user.llm_base_url,
        model=current_user.llm_model,
        effective_mode=effective_mode,
        provider_presets=get_provider_presets(),
    )


@router.post("/me/llm-test")
def test_llm_connection(
    current_user: CurrentUser,
    payload: LLMSettingsUpdate | None = None,
) -> dict:
    """用当前用户凭证（或前端临时传入但未保存的字段）做一次最小 chat 调用，
    验证 Key 是否有效、厂商是否可用。

    - 不传 payload：使用已保存的凭证（含全局兜底）。
    - 传 payload（provider/api_key/base_url/model）：仅用于本次测试，不写库。
      方便用户先试 Key 再决定是否保存。
    返回 ok / error 及可读原因。
    """
    from app.services.llm_client import chat_completion, resolve_credential

    if payload is not None and (payload.api_key or payload.provider):
        # 临时测试：用前端未保存的字段构造凭证，不改动数据库
        temp_user = current_user
        if payload.provider is not None:
            temp_user.llm_provider = payload.provider or None
        if payload.api_key is not None:
            temp_user.llm_api_key = payload.api_key or None
        if payload.base_url is not None:
            temp_user.llm_base_url = payload.base_url or None
        if payload.model is not None:
            temp_user.llm_model = payload.model or None
        cred = resolve_credential(temp_user)
        test_provider = temp_user.llm_provider
    else:
        cred = resolve_credential(current_user)
        test_provider = current_user.llm_provider

    if cred is None:
        return {
            "ok": False,
            "provider": test_provider,
            "error": "NO_CREDENTIAL",
            "detail": "未配置有效的 LLM Key（也没有可用的全局兜底 Key）。",
        }
    try:
        chat_completion(
            temp_user if (payload is not None and (payload.api_key or payload.provider)) else current_user,
            system_prompt="你是连接测试助手。",
            user_prompt="请只回复两个字：成功",
            temperature=0,
            timeout=20,
        )
        return {
            "ok": True,
            "provider": test_provider,
            "kind": cred.kind,
            "model": cred.model,
            "detail": "连接成功，Key 有效。",
        }
    except Exception as exc:  # noqa: BLE001
        # 把底层错误（如 401/404/超时/协议不支持）原样透出，便于用户定位
        err_msg = str(exc)
        tried_url = ""
        if "url=" in err_msg:
            tried_url = err_msg.split("url=", 1)[1]
        if "404" in err_msg or "Not Found" in err_msg:
            reason = (
                "接入点路径错误（404）：Base URL 与所选厂商不匹配。"
                "请确认 Base URL 正确，例如 DeepSeek 应填 https://api.deepseek.com/v1，"
                "OpenAI 兼容接口路径为 /chat/completions。"
            )
        elif "401" in err_msg or "Authentication" in err_msg or "auth" in err_msg.lower():
            reason = "鉴权失败（401）：Key 无效或与所选厂商不匹配。"
        elif "403" in err_msg:
            reason = "权限不足（403）：该 Key 无当前模型/接口的调用权限。"
        elif "timeout" in err_msg.lower() or "timed out" in err_msg.lower():
            reason = "请求超时：网络异常或 base_url 不可达。"
        elif "Connection" in err_msg or "NameResolution" in err_msg or "Failed to resolve" in err_msg:
            reason = "无法连接：base_url 域名解析失败或不可达。"
        else:
            reason = f"调用失败：{err_msg}"
        if tried_url:
            reason += f"（实际请求：{tried_url}）"
        return {
            "ok": False,
            "provider": test_provider,
            "kind": cred.kind,
            "model": cred.model,
            "error": "CALL_FAILED",
            "detail": reason,
        }
