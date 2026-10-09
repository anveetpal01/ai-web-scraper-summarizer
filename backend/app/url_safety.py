"""URL validation, plus protection against requests to private networks (SSRF)."""

import asyncio
import ipaddress
import re
import socket
from urllib.parse import urlsplit

from app.errors import AppError

MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = ("http", "https")
BLOCKED_HOST_SUFFIXES = (".localhost", ".local", ".internal")

INVALID_URL_MESSAGE = "That doesn't look like a valid URL."
PRIVATE_ADDRESS_MESSAGE = "Local and private network addresses can't be summarized."

_SCHEME_RE = re.compile(r"^[a-z][a-z\d+.-]*://", re.IGNORECASE)
_INVALID_HOST_CHARS = set('<>"{}|\\^`')

IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


def normalize_url(raw: str) -> str:
    """Turns user input like "example.com/post" into a full http(s) URL."""
    value = raw.strip()
    if not value:
        raise AppError("Please paste a URL first.")
    if len(value) > MAX_URL_LENGTH:
        raise AppError("That URL is too long.")

    if not _SCHEME_RE.match(value):
        value = f"https://{value}"

    try:
        parts = urlsplit(value)
        parts.port  # raises ValueError for an invalid port
    except ValueError:
        raise AppError(INVALID_URL_MESSAGE) from None

    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise AppError("Only http:// and https:// URLs are supported.")

    host = parts.hostname
    if not host or any(char.isspace() or char in _INVALID_HOST_CHARS for char in host):
        raise AppError(INVALID_URL_MESSAGE)

    return value


async def ensure_public_url(url: str) -> None:
    """Rejects URLs that point at localhost or a private network address."""
    parts = urlsplit(url)
    if parts.scheme.lower() not in ALLOWED_SCHEMES:
        raise AppError("Only http:// and https:// URLs are supported.")

    host = (parts.hostname or "").lower()
    if not host:
        raise AppError(INVALID_URL_MESSAGE)
    if host == "localhost" or host.endswith(BLOCKED_HOST_SUFFIXES):
        raise AppError(PRIVATE_ADDRESS_MESSAGE)

    for address in await _resolve(host):
        if not _is_public(address):
            raise AppError(PRIVATE_ADDRESS_MESSAGE)


async def _resolve(host: str) -> list[IPAddress]:
    try:
        return [ipaddress.ip_address(host)]
    except ValueError:
        pass  # not an IP literal, so look the domain up

    try:
        results = await _lookup(host)
    except (socket.gaierror, UnicodeError):
        raise AppError(f'Couldn\'t find the website "{host}". Check the URL for typos.') from None

    return [ipaddress.ip_address(sockaddr[0]) for *_, sockaddr in results]


async def _lookup(host: str) -> list:
    loop = asyncio.get_running_loop()
    try:
        return await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        # DNS lookups occasionally fail transiently, so give it one more try.
        await asyncio.sleep(0.3)
        return await loop.getaddrinfo(host, None, type=socket.SOCK_STREAM)


def _is_public(address: IPAddress) -> bool:
    if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped
    return address.is_global and not address.is_multicast
