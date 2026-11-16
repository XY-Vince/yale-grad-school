"""Collector base and bounded, address-pinned public HTTP retrieval."""

import ipaddress
import socket
import urllib.parse
from abc import ABC, abstractmethod
from typing import Mapping, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter


class SSRFSecurityError(ValueError):
    """An address is disallowed by the public-only URL policy."""


class ResponseTooLargeError(requests.RequestException):
    """The response exceeds the configured decoded-byte limit."""


DEFAULT_MAX_RESPONSE_BYTES = 25 * 1024 * 1024


def validate_safe_url(url: str) -> Tuple[bool, str, Optional[str]]:
    """Resolve a public HTTP(S) URL and reject any non-public DNS answer.

    Return the first address for connection pinning; a DNS failure uses the
    existing ``DNS_RESOLUTION_FAILED`` sentinel for legacy callers.
    """
    try:
        parsed = urllib.parse.urlsplit(url)
        hostname = parsed.hostname
        port = parsed.port
        if (
            parsed.scheme.lower() not in ("http", "https")
            or not hostname
            or parsed.username is not None
            or parsed.password is not None
            or port == 0
        ):
            return False, url, None
        hostname = hostname.encode("idna").decode("ascii")
    except (ValueError, UnicodeError):
        return False, url, None

    try:
        addr_infos = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False, url, "DNS_RESOLUTION_FAILED"
    if not addr_infos:
        return False, url, "DNS_RESOLUTION_FAILED"

    addresses = []
    for addr in addr_infos:
        ip_str = addr[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, url, None
        if not ip_obj.is_global or ip_obj.is_multicast:
            return False, url, ip_str
        addresses.append(str(ip_obj))
    return True, parsed.geturl(), addresses[0]


class _PinnedHTTPSAdapter(HTTPAdapter):
    """Connect to the selected IP while verifying TLS for the URL hostname."""

    def __init__(self, hostname: str):
        self._hostname = hostname
        super().__init__()

    def init_poolmanager(self, connections, maxsize, block=False, **pool_kwargs):
        pool_kwargs["server_hostname"] = self._hostname
        pool_kwargs["assert_hostname"] = self._hostname
        return super().init_poolmanager(connections, maxsize, block=block, **pool_kwargs)


def _pinned_request_url(url: str, ip: str) -> Tuple[str, str, str]:
    parsed = urllib.parse.urlsplit(url)
    hostname = parsed.hostname.encode("idna").decode("ascii")
    port = parsed.port
    ip_host = f"[{ip}]" if ":" in ip else ip
    pinned_netloc = f"{ip_host}:{port}" if port is not None else ip_host
    host = f"[{hostname}]" if ":" in hostname else hostname
    if port is not None:
        host = f"{host}:{port}"
    return urllib.parse.urlunsplit(
        (parsed.scheme, pinned_netloc, parsed.path, parsed.query, "")
    ), host, hostname


def safe_fetch(
    url: str,
    timeout: float = 10.0,
    max_redirects: int = 3,
    max_response_bytes: int = DEFAULT_MAX_RESPONSE_BYTES,
    *,
    method: str = "GET",
    data: Optional[bytes] = None,
    headers: Optional[Mapping[str, str]] = None,
) -> requests.Response:
    """Fetch each redirect via a checked IP, with proxies disabled and bounded bytes."""
    if max_redirects < 0 or max_response_bytes <= 0:
        raise ValueError("max_redirects must be nonnegative and max_response_bytes positive")
    method = method.upper()
    if method not in {"GET", "POST"} or (method == "GET" and data is not None):
        raise ValueError("Only GET without data and POST are supported")
    allowed_headers = {"user-agent", "accept", "content-type", "referer"}
    if headers and any(key.lower() not in allowed_headers for key in headers):
        raise ValueError("Unsupported request header")
    request_headers = {
        "User-Agent": "VerifyPublicPersonProfile/1.0 (OSINT Auditor; +research)",
        **(headers or {}),
    }
    current_url = url
    for hop in range(max_redirects + 1):
        is_safe, canonical_url, ip_or_reason = validate_safe_url(current_url)
        if not is_safe:
            if ip_or_reason == "DNS_RESOLUTION_FAILED":
                raise requests.ConnectionError(f"DNS resolution failed for URL: {current_url}")
            raise SSRFSecurityError(f"Security gateway blocked request to: {current_url}")

        pinned_url, host_header, hostname = _pinned_request_url(canonical_url, ip_or_reason)
        with requests.Session() as session:
            session.trust_env = False
            if pinned_url.lower().startswith("https://"):
                session.mount("https://", _PinnedHTTPSAdapter(hostname))
            options = {
                "allow_redirects": False,
                "timeout": timeout,
                "stream": True,
                "headers": {**request_headers, "Host": host_header},
            }
            response = (session.post(pinned_url, data=data, **options)
                        if method == "POST" else session.get(pinned_url, **options))
            try:
                location = response.headers.get("Location")
                if response.status_code in (301, 302, 303, 307, 308) and location:
                    if hop == max_redirects:
                        raise requests.TooManyRedirects(
                            f"Exceeded max redirects ({max_redirects}) for URL: {url}"
                        )
                    next_url = urllib.parse.urljoin(canonical_url, location)
                    if method == "POST" and response.status_code in (307, 308):
                        previous = urllib.parse.urlsplit(canonical_url)
                        target = urllib.parse.urlsplit(next_url)
                        origin = lambda p: (p.scheme.lower(), p.hostname, p.port or (
                            443 if p.scheme.lower() == "https" else 80
                        ))
                        if origin(previous) != origin(target):
                            raise SSRFSecurityError("Cross-origin POST body redirect blocked")
                    elif method == "POST":
                        method, data = "GET", None
                        request_headers = {
                            key: value for key, value in request_headers.items()
                            if key.lower() != "content-type"
                        }
                    current_url = next_url
                    continue

                content_length = response.headers.get("Content-Length", "")
                if content_length.isdigit() and int(content_length) > max_response_bytes:
                    raise ResponseTooLargeError(
                        f"Response exceeds {max_response_bytes} bytes: {canonical_url}"
                    )
                chunks = []
                size = 0
                for chunk in response.iter_content(chunk_size=64 * 1024):
                    size += len(chunk)
                    if size > max_response_bytes:
                        raise ResponseTooLargeError(
                            f"Response exceeds {max_response_bytes} bytes: {canonical_url}"
                        )
                    chunks.append(chunk)
                response._content = b"".join(chunks)
                response._content_consumed = True
                response.url = canonical_url
                return response
            finally:
                response.close()
    raise requests.TooManyRedirects(f"Exceeded max redirects ({max_redirects}) for URL: {url}")


class BaseCollector(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list:
        pass

    @abstractmethod
    def fetch_page(self, url: str) -> Tuple[int, str, str]:
        """Returns: (http_status, html_or_text, content_sha256)"""
        pass
