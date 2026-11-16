"""
discovery_engine.py
Universal Agent Discovery Engine (V7.0).
Executes parameter-driven public search queries across general search engines
and academic registries. Outputs discovery_results.jsonl without target-specific hardcoding.
"""

import base64
import html
import json
import re
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup

from .base import SSRFSecurityError, safe_fetch


def extract_significant_tokens(clues: List[str]) -> List[str]:
    """Extracts non-stopword alphanumeric search tokens from clues."""
    stop_words = {
        "currently", "at", "the", "in", "of", "and", "or", "for", "with",
        "to", "from", "by", "on", "as", "is", "was", "are", "were", "a", "an"
    }
    tokens = []
    seen = set()
    for c in clues:
        clean = re.sub(r"[^\w\s-]", " ", c)
        for part in clean.split():
            tok = part.strip()
            tok_norm = tok.lower().replace("-", "")
            if len(tok) >= 2 and tok_norm not in stop_words and tok_norm not in seen:
                seen.add(tok_norm)
                tokens.append(tok)
    return tokens


class UniversalDiscoveryEngine:
    """
    Executes automated query-family exploration and discovery.
    Halts when 3 consecutive query families produce no new candidates or sources.
    """

    def __init__(self, query_budget: int = 30):
        self.query_budget = query_budget
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }
        self.discovery_records: List[Dict[str, Any]] = []
        self.discovered_urls: Set[str] = set()
        self.query_logs: List[Dict[str, Any]] = []
        self.last_search_attempts: List[Dict[str, Any]] = []

    def generate_query_families(self, name: str, clues: List[str]) -> List[Tuple[str, List[str]]]:
        """
        Generates standard query families driven entirely by target name and clues.
        Zero target-specific branches.
        """
        norm_name = name.strip()
        sig_tokens = extract_significant_tokens(clues)

        families: List[Tuple[str, List[str]]] = []

        # Family 1: Exact Name Base
        families.append(("NAME_BASE", [f'"{norm_name}"']))

        # Family 2: Name + Individual Clues
        f2_queries = []
        for c in clues:
            c_clean = c.strip()
            if c_clean:
                f2_queries.append(f'"{norm_name}" {c_clean}')
                if "-" in c_clean:
                    f2_queries.append(f'"{norm_name}" {c_clean.replace("-", " ")}')
                    f2_queries.append(f'"{norm_name}" {c_clean.replace("-", "")}')
        if f2_queries:
            families.append(("NAME_CLUES", f2_queries[:5]))

        # Family 3: Name + Multi-Token Combinations
        if len(sig_tokens) >= 2:
            f3_queries = [
                f'"{norm_name}" {" ".join(sig_tokens[:2])}',
            ]
            if len(sig_tokens) >= 3:
                f3_queries.append(f'"{norm_name}" {sig_tokens[0]} {sig_tokens[2]}')
            families.append(("NAME_MULTI_CLUES", f3_queries))

        # Family 4: Name + Career / Academic Roles
        families.append(("NAME_ROLES", [
            f'"{norm_name}" "faculty" OR "fellow" OR "student" OR "researcher"',
            f'"{norm_name}" "professor" OR "scientist" OR "postdoc"',
        ]))

        # Family 5: Name + Curriculum Vitae / Bio
        families.append(("NAME_BIO", [
            f'"{norm_name}" "curriculum vitae" OR "resume" OR "bio"',
        ]))

        return families

    def search_web_endpoint(self, query: str, max_results: int = 10) -> Tuple[List[Dict[str, str]], str, Optional[str]]:
        """
        Executes a real public web search using standard search engines.
        Returns: (results, status, error_details)
        status: 'COMPLETED', 'BLOCKED', or 'FAILED'
        """
        self.last_search_attempts = []
        endpoints = [
            ("Bing", "https://www.bing.com/search?q=" + urllib.parse.quote(query), "GET", None),
            ("DuckDuckGo", "https://html.duckduckgo.com/html/", "POST",
             urllib.parse.urlencode({"q": query}).encode("utf-8")),
        ]
        for engine, url, method, data in endpoints:
            attempt = {"engine": engine, "url": url, "method": method, "http_status": None}
            self.last_search_attempts.append(attempt)
            try:
                headers = dict(self.headers)
                if engine == "DuckDuckGo":
                    headers.update({
                        "Referer": "https://html.duckduckgo.com/",
                        "Content-Type": "application/x-www-form-urlencoded",
                    })
                response = safe_fetch(url, timeout=8, method=method, data=data, headers=headers)
                attempt["http_status"] = response.status_code
                if response.status_code != 200:
                    attempt["status"] = "BLOCKED" if response.status_code in (401, 403, 429) else "FAILED"
                    attempt["error"] = f"HTTP {response.status_code}"
                    continue
                html_txt = response.content.decode("utf-8", errors="replace")
                results = []
                if engine == "Bing":
                    matches = re.finditer(
                        r'<h2[^>]*><a[^>]+href=\"(https?://[^\"]+)\"[^>]*>(.*?)</a></h2>(?:.*?<p[^>]*>(.*?)</p>)?',
                        html_txt, re.DOTALL,
                    )
                    for match in matches:
                        raw_href = html.unescape(match.group(1))
                        target_url = raw_href
                        encoded = re.search(r"[?&]u=a1([a-zA-Z0-9_-]+)", raw_href)
                        if encoded:
                            b64 = encoded.group(1).replace("-", "+").replace("_", "/")
                            try:
                                target_url = base64.b64decode(b64 + "=" * (-len(b64) % 4)).decode("utf-8")
                            except (ValueError, UnicodeError):
                                pass
                        title = html.unescape(re.sub(r"<[^>]+>", "", match.group(2))).strip()
                        snippet = html.unescape(re.sub(r"<[^>]+>", "", match.group(3) or "")).strip()
                        if target_url.startswith(("http://", "https://")):
                            results.append({"url": target_url, "title": title[:120], "snippet": snippet or title})
                        if len(results) >= max_results:
                            break
                else:
                    soup = BeautifulSoup(html_txt, "html.parser")
                    by_url = {}
                    snippets = {}
                    for node in soup.select("a.result__a, .result__snippet"):
                        link = node if node.name == "a" and node.get("href") else None
                        if link is None:
                            container = node.find_parent(class_="result")
                            link = container.select_one("a.result__a[href]") if container else None
                        if link is None:
                            continue
                        raw_href = link.get("href", "")
                        target_url = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query).get(
                            "uddg", [raw_href]
                        )[0]
                        if not target_url.startswith(("http://", "https://")):
                            continue
                        text = node.get_text(" ", strip=True)
                        if not text:
                            continue
                        if target_url not in by_url:
                            if len(results) >= max_results:
                                continue
                            by_url[target_url] = {"url": target_url, "title": "", "snippet": ""}
                            results.append(by_url[target_url])
                        item = by_url[target_url]
                        if "result__a" in node.get("class", []):
                            item["title"] = text[:120]
                        else:
                            if len(text) > len(snippets.get(target_url, "")):
                                snippets[target_url] = text
                        item["snippet"] = snippets.get(target_url) or item["title"]
                    for item in results:
                        if not item["title"]:
                            item["title"] = item["snippet"][:120]
                if results:
                    attempt["status"] = "COMPLETED"
                    attempt["results_count"] = len(results)
                    return results, "COMPLETED", None
                if re.search(r"\bno results found\b|\bthere are no results for\b|class=[\"']no-results",
                             html_txt, re.IGNORECASE):
                    attempt["status"] = "NO_RESULTS"
                else:
                    attempt["status"] = "FAILED"
                    attempt["error"] = "HTTP 200 but no recognized result or empty-result marker"
            except (requests.RequestException, SSRFSecurityError, OSError, ValueError) as exc:
                attempt["status"] = "BLOCKED" if isinstance(exc, SSRFSecurityError) else "FAILED"
                attempt["error"] = f"{type(exc).__name__}: {exc}"

        errors = "; ".join(
            f"{attempt['engine']}: {attempt['error']}" for attempt in self.last_search_attempts
            if attempt.get("error")
        ) or None
        if any(attempt["status"] == "NO_RESULTS" for attempt in self.last_search_attempts):
            return [], "COMPLETED", errors
        if all(attempt["status"] == "BLOCKED" for attempt in self.last_search_attempts):
            return [], "BLOCKED", errors
        return [], "FAILED", errors

    def run_discovery(
        self,
        name: str,
        clues: List[str],
        output_dir: Path,
        preloaded_file: Optional[Path] = None,
        force_live: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Runs the discovery process and emits discovery_results.jsonl.
        Only reuses preloaded discovery file if explicitly provided and force_live is False.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        results_file = output_dir / "discovery_results.jsonl"

        if not force_live and preloaded_file is not None:
            input_bytes = preloaded_file.read_bytes()
            for line_number, line in enumerate(input_bytes.decode("utf-8").splitlines(), 1):
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"Invalid discovery record at line {line_number}") from exc
                    if not isinstance(rec, dict) or not isinstance(rec.get("url"), str) or not rec["url"]:
                        raise ValueError(f"Discovery record at line {line_number} needs a URL")
                    if rec["url"] not in self.discovered_urls:
                        self.discovered_urls.add(rec["url"])
                        self.discovery_records.append(rec)
            with results_file.open("xb") as output:
                output.write(input_bytes)
            self.query_logs.append({
                "backend": "CuratedDiscovery",
                "query_text": str(preloaded_file),
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "status": "LOADED",
                "results_count": len(self.discovery_records),
            })
            return self.discovery_records

        families = self.generate_query_families(name, clues)
        consecutive_stagnant_families = 0
        total_queries = 0

        for fam_name, queries in families:
            new_in_family = 0
            for q in queries:
                if total_queries >= self.query_budget:
                    break
                total_queries += 1
                search_res, q_status, q_err = self.search_web_endpoint(q, max_results=10)
                q_log = {
                    "backend": "DiscoveryWebSearch",
                    "query_text": q,
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                    "status": q_status,
                    "results_count": len(search_res),
                    "attempts": list(self.last_search_attempts),
                }
                if q_err:
                    q_log["error"] = q_err
                self.query_logs.append(q_log)
                for rank, res in enumerate(search_res, 1):
                    url = res["url"]
                    if url not in self.discovered_urls:
                        self.discovered_urls.add(url)
                        new_in_family += 1

                        c_id = "CAND-01"
                        rationale = f"Discovered via search query '{q}'"
                        if any(tok.lower() in res["snippet"].lower() for tok in extract_significant_tokens(clues)):
                            rationale += " with clue token match."
                        else:
                            rationale += " (general name occurrence)."

                        record = {
                            "query": q,
                            "rank": rank,
                            "url": url,
                            "title": res["title"],
                            "snippet": res["snippet"],
                            "candidate_identity": c_id,
                            "relevance_rationale": rationale,
                            "discovered_at": datetime.now(timezone.utc).isoformat(),
                        }
                        self.discovery_records.append(record)

                time.sleep(0.5)

            if new_in_family == 0:
                consecutive_stagnant_families += 1
            else:
                consecutive_stagnant_families = 0

            if consecutive_stagnant_families >= 3 or total_queries >= self.query_budget:
                break

        with open(results_file, "x", encoding="utf-8") as f:
            for rec in self.discovery_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        return self.discovery_records
