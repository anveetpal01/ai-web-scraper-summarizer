import asyncio

import pytest

from app.errors import AppError
from app.url_safety import ensure_public_url, normalize_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("example.com", "https://example.com"),
        ("  https://example.com/post?id=1  ", "https://example.com/post?id=1"),
        ("http://example.com", "http://example.com"),
    ],
)
def test_normalize_url_adds_scheme_and_trims(raw: str, expected: str) -> None:
    assert normalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "not a url", "https://", "ftp://example.com", "javascript:alert(1)", "file:///etc/passwd"],
)
def test_normalize_url_rejects_invalid_input(raw: str) -> None:
    with pytest.raises(AppError) as error:
        normalize_url(raw)
    assert error.value.status_code == 400


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost:8000",
        "http://api.localhost",
        "http://127.0.0.1",
        "http://0.0.0.0",
        "http://10.0.0.5",
        "http://172.16.4.2",
        "http://192.168.1.10",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://[fd00::1]/",
    ],
)
def test_private_addresses_are_blocked(url: str) -> None:
    with pytest.raises(AppError, match="private network"):
        asyncio.run(ensure_public_url(url))


def test_public_ip_is_allowed() -> None:
    asyncio.run(ensure_public_url("http://8.8.8.8/"))
