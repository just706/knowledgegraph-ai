"""用户接口测试（AI 宪法第七章：覆盖正常 + 异常输入）。"""
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

VALID_EMAIL = "student@example.com"
VALID_PASSWORD = "learning123"


def _register(email: str = VALID_EMAIL, password: str = VALID_PASSWORD) -> dict:
    resp = client.post(
        "/api/v1/users/register",
        json={"email": email, "password": password, "display_name": "测试用户"},
    )
    return resp


def test_register_success() -> None:
    resp = _register(email="a@example.com")
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert "hashed_password" not in body  # 敏感字段不回传


def test_register_duplicate_email() -> None:
    _register(email="dup@example.com")
    resp = _register(email="dup@example.com")
    assert resp.status_code == 409


def test_register_short_password() -> None:
    # 异常输入：密码过短
    resp = _register(email="short@example.com", password="123")
    assert resp.status_code == 422


def test_register_invalid_email() -> None:
    # 异常输入：非法邮箱
    resp = client.post(
        "/api/v1/users/register",
        json={"email": "not-an-email", "password": "learning123"},
    )
    assert resp.status_code == 422


def test_login_success_and_me() -> None:
    _register(email="login@example.com", password="learning123")
    resp = client.post(
        "/api/v1/users/login",
        json={"email": "login@example.com", "password": "learning123"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    assert token

    # 携带 token 访问受保护接口
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "login@example.com"


def test_login_wrong_password() -> None:
    _register(email="wrong@example.com", password="learning123")
    resp = client.post(
        "/api/v1/users/login",
        json={"email": "wrong@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_me_without_token() -> None:
    # 异常输入：无 token 访问受保护接口
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_me_with_invalid_token() -> None:
    resp = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert resp.status_code == 401
