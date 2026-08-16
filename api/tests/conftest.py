"""Pytest fixtures.

For unit tests we use the FastAPI app in-process via httpx. v0.2 will
add a Postgres TestContainer fixture for integration tests.
"""
import pytest


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"
