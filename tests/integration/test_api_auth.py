"""Auth API 集成测试"""
import pytest


class TestAuthEndpoints:
    async def test_health_check(self, async_client):
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    async def test_register(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={"username": "newuser", "password": "testpass123"},
        )
        assert response.status_code in (200, 401)

    async def test_login_fails_with_wrong_password(self, async_client):
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "wrongpass"},
        )
        assert response.status_code == 401
