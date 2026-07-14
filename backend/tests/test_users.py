"""用户接口测试（AI 宪法第七章：覆盖正常 + 异常输入）。"""
from fastapi.testclient import TestClient

VALID_EMAIL = "student@example.com"
VALID_PASSWORD = "learning123"


def _register(client: TestClient, email: str = VALID_EMAIL, password: str = VALID_PASSWORD) -> dict:
    return client.post(
        "/api/v1/users/register",
        json={"email": email, "password": password, "display_name": "测试用户"},
    )


def test_register_success(client: TestClient) -> None:
    resp = _register(client, email="a@example.com")
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "a@example.com"
    assert "hashed_password" not in body  # 敏感字段不回传


def test_register_duplicate_email(client: TestClient) -> None:
    _register(client, email="dup@example.com")
    resp = _register(client, email="dup@example.com")
    assert resp.status_code == 409


def test_register_short_password(client: TestClient) -> None:
    # 异常输入：密码过短
    resp = _register(client, email="short@example.com", password="123")
    assert resp.status_code == 422


def test_register_invalid_email(client: TestClient) -> None:
    # 异常输入：非法邮箱
    resp = client.post(
        "/api/v1/users/register",
        json={"email": "not-an-email", "password": "learning123"},
    )
    assert resp.status_code == 422


def test_login_success_and_me(client: TestClient) -> None:
    _register(client, email="login@example.com", password="learning123")
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


def test_login_wrong_password(client: TestClient) -> None:
    _register(client, email="wrong@example.com", password="learning123")
    resp = client.post(
        "/api/v1/users/login",
        json={"email": "wrong@example.com", "password": "wrongpass"},
    )
    assert resp.status_code == 401


def test_me_without_token(client: TestClient) -> None:
    # 异常输入：无 token 访问受保护接口
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401


def test_me_with_invalid_token(client: TestClient) -> None:
    resp = client.get(
        "/api/v1/users/me", headers={"Authorization": "Bearer invalid.token.here"}
    )
    assert resp.status_code == 401
