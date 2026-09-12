# SPDX-License-Identifier: 0BSD

"""Optional login page hint text from environment."""

from __future__ import annotations

from meshchatx.src.env_utils import env_str


def auth_page_hint_from_env() -> str | None:
    raw = (env_str("MESHCHAT_AUTH_PAGE_HINT") or "").strip()
    return raw or None
