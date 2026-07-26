# SPDX-License-Identifier: 0BSD

"""Optional login page hint text from environment."""

from __future__ import annotations

import os


def auth_page_hint_from_env() -> str | None:
    raw = os.environ.get("MESHCHAT_AUTH_PAGE_HINT", "").strip()
    return raw or None
