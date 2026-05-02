"""安全模块测试"""
import pytest
from app.core.security import (
    get_hashed_password,
    verify_password,
    create_access_token,
    decode_token,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "secure_password_123"
        hashed = get_hashed_password(password)
        assert hashed != password
        assert verify_password(password, hashed)

    def test_wrong_password_fails(self):
        hashed = get_hashed_password("correct")
        assert not verify_password("wrong", hashed)

    def test_hash_is_deterministic_per_call(self):
        h1 = get_hashed_password("same")
        h2 = get_hashed_password("same")
        assert h1 != h2


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token("1:testuser")
        assert isinstance(token, str)
        payload = decode_token(token)
        assert payload["sub"] == "1:testuser"
        assert payload["type"] == "access"
        assert "exp" in payload

    def test_token_has_expiry(self):
        token = create_access_token("1:user")
        payload = decode_token(token)
        assert payload["exp"] > 0
