"""后端接口测试（AI 宪法第七章：每个模块必须经过接口测试）。"""
from fastapi.testclient import TestClient


def test_health_check(client: TestClient) -> None:
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "app_name" in body
