"""Unit tests for security startup and login controls."""

from dataclasses import replace
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from routers.auth import check_login_rate

from config import settings


def test_security_rejects_weak_jwt():
    with pytest.raises(RuntimeError, match="API_SECRET_KEY"):
        replace(settings, secret_key="weak").validate_security()


def test_security_rejects_weak_admin():
    with pytest.raises(RuntimeError, match="API_ADMIN_PASSWORD"):
        replace(settings, secret_key="x" * 32, admin_password="weak").validate_security()


def test_login_limit_and_reset():
    with patch("routers.auth.time.monotonic", return_value=100):
        for _ in range(10):
            check_login_rate("test-rate-client")
        with pytest.raises(HTTPException) as exc:
            check_login_rate("test-rate-client")
        assert exc.value.status_code == 429
    with patch("routers.auth.time.monotonic", return_value=161):
        check_login_rate("test-rate-client")
