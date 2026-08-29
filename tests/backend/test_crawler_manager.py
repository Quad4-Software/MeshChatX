# SPDX-License-Identifier: 0BSD

"""Unit tests for conservative Nomad crawler policy helpers."""

from meshchatx.src.backend.crawler_manager import (
    CrawlerManager,
    content_signals_nocrawl,
    extract_same_node_page_links,
    make_snippet,
    normalize_page_path,
    token_vector,
    cosine_similarity,
)


def test_normalize_page_path_strips_micron_fields():
    assert normalize_page_path("/page/index.mu`cat=x") == "/page/index.mu"
    assert normalize_page_path("page/about.mu") == "/page/about.mu"


def test_content_signals_nocrawl_markers():
    assert content_signals_nocrawl("# nocrawl\nWelcome")
    assert content_signals_nocrawl("nocrawl: deny")
    assert content_signals_nocrawl("Disallow: /")
    assert not content_signals_nocrawl("Hello from the mesh")


def test_extract_same_node_page_links():
    content = """
    Welcome
    `About`/page/about.mu`
    [Forum](/page/forum.mu)
    <a href="/page/links.md">Links</a>
    /page/extra.txt
    """
    links = extract_same_node_page_links(content)
    assert "/page/about.mu" in links
    assert "/page/forum.mu" in links
    assert "/page/links.md" in links
    assert "/page/extra.txt" in links


def test_make_snippet_highlights_query_region():
    text = "aaa " + ("x" * 100) + " needle " + ("y" * 100) + " zzz"
    snippet = make_snippet(text, "needle")
    assert "needle" in snippet
    assert snippet.startswith("...") or "needle" in snippet


def test_token_vector_adjacency_ranks_related_text():
    q = token_vector("reticulum mesh radio")
    a = token_vector("reticulum mesh chat over radio links")
    b = token_vector("cooking recipes and pasta sauce")
    assert cosine_similarity(q, a) > cosine_similarity(q, b)


def test_crawler_manager_opt_out_and_queue(db):
    class Cfg:
        class Int:
            def __init__(self, v):
                self._v = v

            def get(self):
                return self._v

        crawler_max_depth = Int(2)
        crawler_max_pages_per_node = Int(20)
        crawler_max_hops = Int(4)
        crawler_max_rtt_ms = Int(2500)
        crawler_requests_per_day_per_node = Int(1)
        crawler_refresh_days = Int(30)

    mgr = CrawlerManager(db, Cfg())
    dest = "ab" * 16
    mgr.record_opt_out(dest, reason="user", source="user")
    assert mgr.is_opted_out(dest)
    assert mgr.queue_if_allowed(dest, "/page/index.mu") is False
