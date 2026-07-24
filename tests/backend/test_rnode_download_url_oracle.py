# SPDX-License-Identifier: 0BSD

"""Oracle: RNode firmware download URL allowlist rejects lookalike hosts."""

from __future__ import annotations


def _url_allowed(url: str, allowed_prefixes: list[str]) -> bool:
    return any(url.startswith(a) for a in allowed_prefixes)


def test_rnode_download_prefix_oracle_rejects_lookalike_hosts():
    allowed = [
        "https://github.com/",
        "https://codeload.github.com/",
        "https://objects.githubusercontent.com/",
        "https://release-assets.githubusercontent.com/",
    ]
    # Accept
    assert _url_allowed(
        "https://github.com/markqvist/RNode_Firmware/releases/download/v1/x.zip",
        allowed,
    )
    assert _url_allowed(
        "https://objects.githubusercontent.com/github-production-release-asset-2e65be/1/x",
        allowed,
    )
    # Reject lookalikes / SSRF bait
    assert not _url_allowed("https://github.com.evil.example/markqvist/x.zip", allowed)
    assert not _url_allowed("https://evil.example/https://github.com/x.zip", allowed)
    assert not _url_allowed("http://127.0.0.1/firmware.zip", allowed)
    assert not _url_allowed("https://github.com.attacker/x", allowed)
