"""
Live Search and Web Collector (V4.3).
Executes real public search queries and fetches web pages with SHA-256 fingerprinting.
Never manufactures fake search results or synthetic snippets.
"""

import hashlib
import re
import urllib.parse
from typing import Dict, List, Optional, Tuple
from .base import BaseCollector, safe_fetch, SSRFSecurityError


class LiveSearchCollector(BaseCollector):
    def __init__(self, query_budget: int = 20, search_engine_url: Optional[str] = None):
        self.query_budget = query_budget
        self.search_engine_url = search_engine_url or "https://html.duckduckgo.com/html/?q="
        self.queries_executed = 0
        self.pages_fetched = 0
        self.errors: List[str] = []

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, str]]:
        """
        Executes a real web search. If network is unavailable or search endpoint fails,
        records the error in self.errors and returns an empty list.
        Never fabricates results.
        """
        if self.queries_executed >= self.query_budget:
            self.errors.append(f"Query budget exhausted ({self.query_budget})")
            return []

        self.queries_executed += 1
        encoded_q = urllib.parse.quote_plus(query.strip())
        target_url = f"{self.search_engine_url}{encoded_q}"

        try:
            resp = safe_fetch(target_url, timeout=6.0)
            if resp.status_code != 200:
                self.errors.append(f"Search endpoint HTTP {resp.status_code} for query: {query}")
                return []

            html = resp.text
            results = self._parse_search_html(html, max_results)
            return results
        except SSRFSecurityError as e:
            self.errors.append(f"Search blocked by SSRF gateway: {e}")
            return []
        except Exception as e:
            self.errors.append(f"Search request failed for '{query}': {type(e).__name__}: {str(e)}")
            return []

    def _parse_search_html(self, html: str, max_results: int) -> List[Dict[str, str]]:
        """Extracts search results (title, url, snippet) from HTML response."""
        results = []
        link_pattern = re.compile(
            r'<a[^>]+class="result__snippet"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
            re.IGNORECASE | re.DOTALL,
        )
        matches = link_pattern.findall(html)

        for href, snippet in matches:
            clean_snippet = re.sub(r"<[^>]+>", "", snippet).strip()
            clean_url = href.strip()
            if clean_url.startswith("//"):
                clean_url = "https:" + clean_url
            if clean_url.startswith("http"):
                results.append({
                    "title": clean_snippet[:80],
                    "url": clean_url,
                    "snippet": clean_snippet,
                })
            if len(results) >= max_results:
                break

        return results

    def fetch_page(self, url: str) -> Tuple[int, str, str]:
        """
        Fetches an external page. Returns (http_status, html_or_text, content_sha256).
        On error, records to self.errors and returns non-200 status code with empty payload.
        """
        self.pages_fetched += 1
        try:
            resp = safe_fetch(url, timeout=8.0)
            content_bytes = resp.content
            sha256 = hashlib.sha256(content_bytes).hexdigest()
            return resp.status_code, resp.text, sha256
        except SSRFSecurityError as e:
            self.errors.append(f"SSRF violation blocked for {url}: {str(e)}")
            return 403, "", hashlib.sha256(b"").hexdigest()
        except Exception as e:
            self.errors.append(f"Fetch error for {url}: {type(e).__name__}: {str(e)}")
            return 500, "", hashlib.sha256(b"").hexdigest()
