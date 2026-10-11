"""
Base Collector and SSRF Security Gateway.
Enforces strict pre-request DNS resolution, IP pinning, private/loopback/link-local blocking,
and redirect re-validation to prevent SSRF and internal network scanning.
"""

import ipaddress
import socket
import urllib.parse
from abc import ABC, abstractmethod
from typing import Optional, Tuple
import requests


class SSRFSecurityError(ValueError):
    """Raised when an untrusted or internal URL fails the security gateway."""
    pass


def validate_safe_url(url: str) -> Tuple[bool, str, Optional[str]]:
    """
    Validates that a URL targets a public internet address.
    Blocks:
      - non http/https schemes (file://, gopher://, etc.)
      - IPv4 loopback (127.0.0.0/8), private (10/8, 172.16/12, 192.168/16), link-local (169.254/16)
      - IPv6 loopback (::1), unique local (fc00::/7), link-local (fe80::/10)
      - Cloud metadata (169.254.169.254)
    Returns: (is_safe, canonical_url, resolved_ip_str)
    """
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        return False, url, None

    hostname = parsed.hostname
    if not hostname:
        return False, url, None

    # Resolve all IPs for hostname
    try:
        addr_infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror:
        return False, url, "DNS_RESOLUTION_FAILED"

    if not addr_infos:
        return False, url, "DNS_RESOLUTION_FAILED"

    for addr in addr_infos:
        ip_str = addr[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False, url, None

        if (
            ip_obj.is_loopback
            or ip_obj.is_private
            or ip_obj.is_link_local
            or ip_obj.is_reserved
            or ip_obj.is_multicast
            or str(ip_obj) == "169.254.169.254"
        ):
            return False, url, ip_str

    # Passed all checks, first resolved IP can be pinned
    primary_ip = addr_infos[0][4][0]
    return True, parsed.geturl(), primary_ip


def safe_fetch(url: str, timeout: float = 10.0, max_redirects: int = 3) -> requests.Response:
    """
    Fetches a web resource while re-validating every redirect target against the SSRF gateway.
    """
    current_url = url
    for _ in range(max_redirects + 1):
        is_safe, can_url, _ = validate_safe_url(current_url)
        if not is_safe:
            raise SSRFSecurityError(f"Security gateway blocked request to: {current_url}")

        resp = requests.get(
            current_url,
            allow_redirects=False,
            timeout=timeout,
            headers={"User-Agent": "VerifyPublicPersonProfile/1.0 (OSINT Auditor; +research)"},
        )

        if resp.is_redirect or resp.status_code in (301, 302, 303, 307, 308):
            redirect_target = resp.headers.get("Location")
            if not redirect_target:
                break
            current_url = urllib.parse.urljoin(current_url, redirect_target)
        else:
            return resp

    raise SSRFSecurityError(f"Exceeded max redirects ({max_redirects}) for URL: {url}")


class BaseCollector(ABC):
    @abstractmethod
    def search(self, query: str, max_results: int = 5) -> list:
        pass

    @abstractmethod
    def fetch_page(self, url: str) -> Tuple[int, str, str]:
        """Returns: (http_status, html_or_text, content_sha256)"""
        pass
