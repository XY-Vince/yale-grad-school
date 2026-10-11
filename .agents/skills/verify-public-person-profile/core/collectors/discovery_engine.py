"""
discovery_engine.py
Universal Agent Discovery Engine (V7.0).
Executes parameter-driven public search queries across general search engines
and academic registries. Outputs discovery_results.jsonl without target-specific hardcoding.
"""

import json
import re
import ssl
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import certifi


import base64


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
        self.ssl_ctx = ssl.create_default_context(cafile=certifi.where())
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://html.duckduckgo.com/",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        self.discovery_records: List[Dict[str, Any]] = []
        self.discovered_urls: Set[str] = set()
        self.query_logs: List[Dict[str, Any]] = []

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

    def search_web_endpoint(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """Executes a real public web search using standard search engines."""
        results = []
        # 1. Primary: Bing Search
        try:
            url_bing = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
            req_bing = urllib.request.Request(url_bing, headers=self.headers)
            with urllib.request.urlopen(req_bing, context=self.ssl_ctx, timeout=8) as resp:
                if resp.status == 200:
                    html_txt = resp.read().decode("utf-8", errors="ignore")
                    matches = re.finditer(
                        r'<h2[^>]*><a[^>]+href=\"(https?://[^\"]+)\"[^>]*>(.*?)</a></h2>(?:.*?<p[^>]*>(.*?)</p>)?',
                        html_txt,
                        re.DOTALL
                    )
                    for m in matches:
                        raw_href = m.group(1)
                        title_clean = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                        snippet_clean = re.sub(r"<[^>]+>", "", m.group(3) or "").strip()
                        target_url = raw_href
                        m_u = re.search(r'[?&]u=a1([a-zA-Z0-9_-]+)', raw_href.replace("&amp;", "&"))
                        if m_u:
                            b64 = m_u.group(1).replace('-', '+').replace('_', '/')
                            pad = len(b64) % 4
                            if pad:
                                b64 += '=' * (4 - pad)
                            try:
                                target_url = base64.b64decode(b64).decode('utf-8')
                            except Exception:
                                pass
                        if target_url.startswith("http"):
                            results.append({
                                "url": target_url,
                                "title": title_clean[:120],
                                "snippet": snippet_clean or title_clean,
                            })
                            if len(results) >= max_results:
                                break
        except Exception:
            pass

        if results:
            return results

        # 2. Fallback: DuckDuckGo Form POST
        data = urllib.parse.urlencode({"q": query}).encode("utf-8")
        req = urllib.request.Request(
            "https://html.duckduckgo.com/html/",
            data=data,
            headers=self.headers,
        )
        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=8) as resp:
                if resp.status == 200:
                    html_txt = resp.read().decode("utf-8", errors="ignore")
                    matches = re.finditer(r'<a[^>]+class="result__snippet"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html_txt, re.DOTALL)
                    for m in matches:
                        raw_href = m.group(1)
                        parsed = urllib.parse.urlparse(raw_href)
                        qs = urllib.parse.parse_qs(parsed.query)
                        target_url = qs.get("uddg", [raw_href])[0]
                        clean_snippet = re.sub(r"<[^>]+>", "", m.group(2)).strip()
                        results.append({
                            "url": target_url,
                            "title": clean_snippet[:80],
                            "snippet": clean_snippet,
                        })
                        if len(results) >= max_results:
                            break
        except Exception:
            pass
        return results

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

        if not force_live and preloaded_file and preloaded_file.exists():
            for line in preloaded_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line:
                    try:
                        rec = json.loads(line)
                        if rec.get("url") and rec["url"] not in self.discovered_urls:
                            self.discovered_urls.add(rec["url"])
                            self.discovery_records.append(rec)
                    except Exception:
                        pass
            if self.discovery_records:
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
                search_res = self.search_web_endpoint(q, max_results=10)
                self.query_logs.append({
                    "backend": "DiscoveryWebSearch",
                    "query_text": q,
                    "executed_at": datetime.now(timezone.utc).isoformat(),
                    "status": "COMPLETED",
                    "results_count": len(search_res),
                })
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

        with open(results_file, "w", encoding="utf-8") as f:
            for rec in self.discovery_records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")

        return self.discovery_records
