"""Isolated synthetic credentials for offline API tests."""

import os

os.environ.setdefault("API_SECRET_KEY", "test-only-" * 4)
os.environ.setdefault("API_ADMIN_PASSWORD", "test-only-" * 2)
