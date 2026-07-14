"""字段级对称加密工具：用于安全地存储用户私有凭证（如个人 LLM API Key）。

设计原则：
- 主密钥来自环境变量 LLM_KEY_MASTER（未配置时用 SECRET_KEY 派生，仅用于本地开发）。
- 使用 cryptography.fernet（AES-128-CBC + HMAC），对单字段做透明加解密。
- 加密失败（缺依赖/缺密钥）时安全降级：返回原值并打告警，绝不静默丢失数据。
"""
from __future__ import annotations

import base64
import hashlib
import logging

from app.config import settings

logger = logging.getLogger(__name__)

_FERNET = None


def _get_fernet():
    global _FERNET
    if _FERNET is not None:
        return _FERNET
    try:
        from cryptography.fernet import Fernet

        master = (settings.LLM_KEY_MASTER or settings.SECRET_KEY or "dev").encode("utf-8")
        # 将任意主密钥派生为 32 字节 URL-safe base64 key
        derived = base64.urlsafe_b64encode(hashlib.sha256(master).digest())
        _FERNET = Fernet(derived)
    except Exception:  # noqa: BLE001  依赖缺失等
        _FERNET = False
    return _FERNET


def encrypt_field(plain: str | None) -> str | None:
    """加密字段；plain 为空直接返回空；失败降级返回原值。"""
    if not plain:
        return plain
    f = _get_fernet()
    if not f:
        logger.warning("加密模块不可用，API Key 将以明文存储，请检查 cryptography 依赖")
        return plain
    try:
        return f.encrypt(plain.encode("utf-8")).decode("utf-8")
    except Exception:  # noqa: BLE001
        logger.warning("加密失败，API Key 将以明文存储")
        return plain


def decrypt_field(cipher: str | None) -> str | None:
    """解密字段；为空直接返回空；失败降级返回原值（可能仍是密文，由调用方感知）。"""
    if not cipher:
        return cipher
    f = _get_fernet()
    if not f:
        return cipher
    try:
        return f.decrypt(cipher.encode("utf-8")).decode("utf-8")
    except Exception:  # noqa: BLE001  非密文或密钥不匹配
        return cipher
