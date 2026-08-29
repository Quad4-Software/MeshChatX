# SPDX-License-Identifier: 0BSD
"""Conservative NomadNet page crawler policy.

Announce-driven discovery, hop and RTT caps, one request per node per day,
shallow depth, hard page caps, prioritization, permanent opt-out, and
opt-in enablement.
"""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime, timedelta
from typing import Any

import RNS

UNKNOWN_HOPS = 64

# Front page is depth 0. Max depth 2 means index plus two levels down.
DEFAULT_MAX_DEPTH = 2
DEFAULT_MAX_PAGES_PER_NODE = 20
DEFAULT_MAX_HOPS = 4
DEFAULT_MAX_RTT_MS = 2500.0
DEFAULT_REQUESTS_PER_DAY = 1
DEFAULT_REFRESH_DAYS = 30

NOCRAWL_PATTERNS = (
    re.compile(r"(?im)^\s*#\s*nocrawl\b"),
    re.compile(r"(?im)^\s*nocrawl\s*[:=]\s*(deny|disallow|true|1|yes)\b"),
    re.compile(r"(?im)\bmeshchatx[_-]?nocrawl\b"),
    re.compile(r"(?im)^\s*robots\s*:\s*none\b"),
    re.compile(r"(?im)^\s*disallow\s*:\s*/\s*$"),
)

# Same-node page paths only. External destination hashes are ignored.
_PAGE_PATH_RE = re.compile(
    r"(?:`[^`]*`|/page/|\[[^\]]*\]\()\s*(/page/[A-Za-z0-9_./+-]+(?:\.[A-Za-z0-9]+)?)",
)
_BARE_PAGE_RE = re.compile(
    r"(?<![A-Za-z0-9_/])(/page/[A-Za-z0-9_./+-]+(?:\.[A-Za-z0-9]+)?)"
)
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\((/page/[^)\s]+)\)")
_HTML_HREF_RE = re.compile(
    r"""href\s*=\s*["'](/page/[^"'#?\s]+)""",
    re.IGNORECASE,
)
_MICRON_LINK_RE = re.compile(r"`[^`]*`(`)?(/page/[^`\s]+)(`)?")

_TOKEN_RE = re.compile(r"[a-z0-9]{2,}", re.IGNORECASE)
_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "are",
        "but",
        "not",
        "you",
        "all",
        "can",
        "had",
        "her",
        "was",
        "one",
        "our",
        "out",
        "has",
        "have",
        "this",
        "that",
        "with",
        "from",
        "they",
        "been",
        "said",
        "each",
        "which",
        "their",
        "will",
        "page",
        "http",
        "https",
        "nomad",
        "index",
    },
)


def normalize_page_path(page_path: str | None, default: str = "/page/index.mu") -> str:
    raw = (page_path or "").strip() or default
    path_only = raw.split("`", 1)[0].strip()
    if not path_only.startswith("/"):
        path_only = "/" + path_only
    if path_only.startswith("/page/") is False and path_only != "/":
        # Keep non-page request paths out of the crawl graph.
        return path_only
    # Drop query-like junk after path
    path_only = path_only.split("?", 1)[0].split("#", 1)[0]
    return path_only or default


def content_signals_nocrawl(content: str | None) -> bool:
    if not content:
        return False
    text = content[:20000]
    return any(p.search(text) for p in NOCRAWL_PATTERNS)


def extract_same_node_page_links(
    content: str | None, *, max_links: int = 40
) -> list[str]:
    """Return unique /page/... paths linked from page content."""
    if not content:
        return []
    found: list[str] = []
    seen: set[str] = set()

    def add(path: str) -> None:
        cleaned = normalize_page_path(path)
        if not cleaned.startswith("/page/"):
            return
        # Skip file downloads and obvious binaries
        lower = cleaned.lower()
        if "/file/" in lower:
            return
        if cleaned in seen:
            return
        seen.add(cleaned)
        found.append(cleaned)

    for regex in (_MD_LINK_RE, _HTML_HREF_RE, _MICRON_LINK_RE, _BARE_PAGE_RE):
        for match in regex.finditer(content):
            groups = [g for g in match.groups() if g and g.startswith("/page/")]
            target = groups[0] if groups else match.group(0)
            if target.startswith("/page/"):
                add(target)
            if len(found) >= max_links:
                return found

    for match in _PAGE_PATH_RE.finditer(content):
        add(match.group(1))
        if len(found) >= max_links:
            break
    return found


def tokenize_for_index(text: str | None) -> list[str]:
    if not text:
        return []
    tokens = []
    for tok in _TOKEN_RE.findall(text.lower()):
        if tok in _STOPWORDS or tok.isdigit():
            continue
        tokens.append(tok)
    return tokens


def token_vector(text: str | None) -> dict[str, float]:
    """TF log-scaled bag of words for local semantic adjacency / ranking."""
    counts: dict[str, int] = {}
    for tok in tokenize_for_index(text):
        counts[tok] = counts.get(tok, 0) + 1
    if not counts:
        return {}
    return {tok: 1.0 + math.log(count) for tok, count in counts.items()}


def cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    shared = 0.0
    for tok, av in a.items():
        bv = b.get(tok)
        if bv is not None:
            shared += av * bv
    if shared <= 0:
        return 0.0
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    if na <= 0 or nb <= 0:
        return 0.0
    return shared / (na * nb)


def make_snippet(content: str | None, query: str | None, *, radius: int = 80) -> str:
    if not content:
        return ""
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    if not query:
        snippet = text[: radius * 2].strip()
        return snippet + ("..." if len(text) > len(snippet) else "")
    lower = text.lower()
    q = query.lower().strip()
    idx = lower.find(q)
    if idx < 0:
        # Fall back to first query token
        for tok in tokenize_for_index(q):
            idx = lower.find(tok)
            if idx >= 0:
                break
    if idx < 0:
        snippet = text[: radius * 2].strip()
        return snippet + ("..." if len(text) > len(snippet) else "")
    start = max(0, idx - radius)
    end = min(len(text), idx + len(q) + radius + 40)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def hops_to(destination_hash: str | bytes) -> int:
    try:
        if isinstance(destination_hash, str):
            dest = bytes.fromhex(destination_hash)
        else:
            dest = destination_hash
        if RNS.Transport.has_path(dest):
            hops = RNS.Transport.hops_to(dest)
            if isinstance(hops, int) and hops >= 0:
                return hops
    except Exception:
        pass
    return UNKNOWN_HOPS


def link_rtt_ms(link) -> float | None:
    """Best-effort RTT from an RNS Link, in milliseconds."""
    if link is None:
        return None
    for attr in ("rtt", "get_rtt"):
        try:
            value = getattr(link, attr, None)
            if callable(value):
                value = value()
            if value is None:
                continue
            rtt = float(value)
            # RNS Link.rtt is typically seconds
            if rtt < 0:
                continue
            if rtt < 30:
                return rtt * 1000.0
            return rtt
        except Exception:
            continue
    return None


class CrawlerManager:
    """Policy and queue helpers for identity-scoped Nomad crawling."""

    def __init__(self, database, config):
        self.database = database
        self.config = config

    def _cfg_int(self, name: str, default: int) -> int:
        conf = getattr(self.config, name, None)
        if conf is None:
            return default
        try:
            return int(conf.get())
        except Exception:
            return default

    def _cfg_float(self, name: str, default: float) -> float:
        conf = getattr(self.config, name, None)
        if conf is None:
            return default
        try:
            return float(conf.get())
        except Exception:
            return default

    @property
    def max_depth(self) -> int:
        return max(0, min(2, self._cfg_int("crawler_max_depth", DEFAULT_MAX_DEPTH)))

    @property
    def max_pages_per_node(self) -> int:
        return max(
            1,
            min(
                20,
                self._cfg_int("crawler_max_pages_per_node", DEFAULT_MAX_PAGES_PER_NODE),
            ),
        )

    @property
    def max_hops(self) -> int:
        return max(1, min(16, self._cfg_int("crawler_max_hops", DEFAULT_MAX_HOPS)))

    @property
    def max_rtt_ms(self) -> float:
        return max(
            100.0,
            min(60000.0, self._cfg_float("crawler_max_rtt_ms", DEFAULT_MAX_RTT_MS)),
        )

    @property
    def requests_per_day(self) -> int:
        return max(
            1,
            min(
                3,
                self._cfg_int(
                    "crawler_requests_per_day_per_node", DEFAULT_REQUESTS_PER_DAY
                ),
            ),
        )

    @property
    def refresh_days(self) -> int:
        return max(
            1, min(365, self._cfg_int("crawler_refresh_days", DEFAULT_REFRESH_DAYS))
        )

    def is_opted_out(self, destination_hash: str) -> bool:
        return self.database.misc.is_crawl_opted_out(destination_hash)

    def record_opt_out(
        self,
        destination_hash: str,
        *,
        reason: str = "signal",
        source: str = "signal",
    ) -> None:
        self.database.misc.upsert_crawl_opt_out(
            destination_hash,
            reason=reason,
            source=source,
        )
        # Cancel pending work for this node
        self.database.misc.cancel_crawl_tasks_for_destination(destination_hash)

    def remove_opt_out(self, destination_hash: str) -> None:
        self.database.misc.delete_crawl_opt_out(destination_hash)

    def priority_for(
        self,
        *,
        hops: int,
        depth: int,
        announced_recently: bool = True,
    ) -> float:
        """Lower score is fetched first."""
        hop_term = float(hops if hops < UNKNOWN_HOPS else 48)
        score = hop_term * 100.0 + float(depth) * 10.0
        if not announced_recently:
            score += 25.0
        return score

    def should_accept_node(self, destination_hash: str) -> tuple[bool, str | None, int]:
        if self.is_opted_out(destination_hash):
            return False, "opt_out", UNKNOWN_HOPS
        hops = hops_to(destination_hash)
        # Unknown hops: still allow queueing. Process step defers until a path exists.
        if hops < UNKNOWN_HOPS and hops > self.max_hops:
            return False, "hops", hops
        return True, None, hops

    def path_ready_for_crawl(
        self, destination_hash: str
    ) -> tuple[bool, str | None, int]:
        """Stricter gate used right before a network request."""
        ok, reason, hops = self.should_accept_node(destination_hash)
        if not ok:
            return ok, reason, hops
        if hops >= UNKNOWN_HOPS:
            try:
                dest = bytes.fromhex(destination_hash)
                if not RNS.Transport.has_path(dest):
                    RNS.Transport.request_path(dest)
            except Exception:
                pass
            return False, "no_path", hops
        return True, None, hops

    def node_may_request_today(self, destination_hash: str) -> bool:
        stats = self.database.misc.get_crawl_node_stats(destination_hash)
        if not stats:
            return True
        last = stats.get("last_request_at")
        if not last:
            return True
        try:
            if isinstance(last, str):
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
            else:
                last_dt = last
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=UTC)
        except Exception:
            return True
        window = timedelta(days=1) / max(1, self.requests_per_day)
        return datetime.now(UTC) >= last_dt + window

    def pages_indexed_for_node(self, destination_hash: str) -> int:
        return self.database.misc.count_archived_distinct_paths(destination_hash)

    def homepage_needs_refresh(self, destination_hash: str, page_path: str) -> bool:
        versions = self.database.misc.get_archived_page_versions(
            destination_hash,
            page_path,
        )
        if not versions:
            return True
        created = versions[0].get("created_at")
        if not created:
            return True
        try:
            if isinstance(created, str):
                created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            else:
                created_dt = created
            if created_dt.tzinfo is None:
                created_dt = created_dt.replace(tzinfo=UTC)
        except Exception:
            return True
        return datetime.now(UTC) >= created_dt + timedelta(days=self.refresh_days)

    def queue_if_allowed(
        self,
        destination_hash: str,
        page_path: str,
        *,
        depth: int = 0,
        announced_recently: bool = True,
        force: bool = False,
    ) -> bool:
        """Queue a crawl task when policy allows. Returns True if queued."""
        dest = (destination_hash or "").strip().lower()
        path = normalize_page_path(page_path)
        if not dest or len(dest) != 32:
            return False

        ok, reason, hops = self.should_accept_node(dest)
        if not ok:
            if reason:
                self.database.misc.upsert_crawl_node_stats(
                    dest,
                    skipped_reason=reason,
                    last_hops=hops if hops < UNKNOWN_HOPS else None,
                )
            return False

        if depth > self.max_depth:
            return False

        if self.pages_indexed_for_node(dest) >= self.max_pages_per_node and depth > 0:
            return False

        if not force and not self.node_may_request_today(dest):
            # Still allow queuing deeper pages only when the day's slot is free.
            # Homepage refresh waits for the daily window.
            existing = self.database.misc.get_crawl_task(dest, path)
            if existing and existing.get("status") == "pending":
                return False
            if depth == 0 and not self.homepage_needs_refresh(dest, path):
                return False
            if depth == 0:
                return False

        if depth == 0 and not force and not self.homepage_needs_refresh(dest, path):
            # Completed recently enough. Do not reset.
            existing = self.database.misc.get_crawl_task(dest, path)
            if existing and existing.get("status") == "completed":
                return False

        priority = self.priority_for(
            hops=hops,
            depth=depth,
            announced_recently=announced_recently,
        )
        self.database.misc.upsert_crawl_task(
            dest,
            path,
            status="pending",
            retry_count=0,
            depth=depth,
            priority=priority,
            reset_completed=force or self.homepage_needs_refresh(dest, path),
        )
        return True

    def select_next_tasks(
        self, *, max_retries: int, max_concurrent: int
    ) -> list[dict[str, Any]]:
        return self.database.misc.get_prioritized_crawl_tasks(
            max_retries=max_retries,
            max_concurrent=max_concurrent,
        )

    def mark_node_requested(
        self,
        destination_hash: str,
        *,
        rtt_ms: float | None = None,
        hops: int | None = None,
        skipped_reason: str | None = None,
    ) -> None:
        self.database.misc.upsert_crawl_node_stats(
            destination_hash,
            last_request_at=datetime.now(UTC),
            last_rtt_ms=rtt_ms,
            last_hops=hops,
            skipped_reason=skipped_reason,
        )

    def rtt_exceeds_limit(self, rtt_ms: float | None) -> bool:
        if rtt_ms is None:
            return False
        return rtt_ms > self.max_rtt_ms

    def discover_child_paths(
        self,
        destination_hash: str,
        content: str,
        *,
        parent_depth: int,
        parent_path: str,
    ) -> list[str]:
        if parent_depth >= self.max_depth:
            return []
        remaining = self.max_pages_per_node - self.pages_indexed_for_node(
            destination_hash,
        )
        if remaining <= 0:
            return []
        links = extract_same_node_page_links(content, max_links=remaining + 5)
        parent_norm = normalize_page_path(parent_path)
        out = []
        for link in links:
            if link == parent_norm:
                continue
            out.append(link)
            if len(out) >= remaining:
                break
        return out

    def rank_archives_by_query(
        self,
        rows: list[dict[str, Any]],
        query: str,
    ) -> list[dict[str, Any]]:
        """Re-order LIKE hits by token-vector adjacency to the query."""
        qvec = token_vector(query)
        if not qvec:
            return rows
        scored = []
        for row in rows:
            blob = f"{row.get('page_path') or ''} {row.get('content') or ''}"
            score = cosine_similarity(qvec, token_vector(blob))
            # Prefer path/hash exact-ish hits
            qlower = query.lower()
            path = (row.get("page_path") or "").lower()
            dest = (row.get("destination_hash") or "").lower()
            if qlower in path:
                score += 0.35
            if qlower in dest:
                score += 0.25
            scored.append((score, row))
        scored.sort(key=lambda item: (-item[0], item[1].get("created_at") or ""))
        return [row for _, row in scored]
