# SPDX-License-Identifier: 0BSD
"""HTTP routes: spam/spam."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.spam._names import *  # noqa: F403


def register_spam_spam_routes(routes: Any, app: Any) -> None:

    # get spam keywords

    @routes.get("/api/v1/spam-keywords")
    async def spam_keywords_get(request):
        keywords = app.database.misc.get_spam_keywords()
        keyword_list = [
            {
                "id": k["id"],
                "keyword": k["keyword"],
                "created_at": k["created_at"],
            }
            for k in keywords
        ]
        return web.json_response(
            {
                "spam_keywords": keyword_list,
            },
        )

    @routes.post("/api/v1/spam-keywords")
    async def spam_keywords_add(request):
        data = await request.json()
        keyword = data.get("keyword", "").strip()
        if not keyword:
            return web.json_response({"error": "Keyword is required"}, status=400)

        try:
            app.database.misc.add_spam_keyword(keyword)
            return web.json_response({"message": "ok"})
        except Exception:
            return web.json_response(
                {"error": "Keyword already exists"},
                status=400,
            )

    @routes.delete("/api/v1/spam-keywords/{keyword_id}")
    async def spam_keywords_delete(request):
        keyword_id = request.match_info.get("keyword_id", "")
        try:
            keyword_id = int(keyword_id)
        except (ValueError, TypeError):
            return web.json_response({"error": "Invalid keyword ID"}, status=400)

        try:
            app.database.misc.delete_spam_keyword(keyword_id)
            return web.json_response({"message": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    @routes.post("/api/v1/lxmf-messages/{hash}/spam")
    async def lxmf_messages_spam(request):
        message_hash = request.match_info.get("hash", "")
        data = await request.json()
        is_spam = data.get("is_spam", False)

        try:
            message = app.database.messages.get_lxmf_message_by_hash(message_hash)
            if message:
                message_data = dict(message)
                message_data["is_spam"] = 1 if is_spam else 0
                app.database.messages.upsert_lxmf_message(message_data)
                return web.json_response({"message": "ok"})
            return web.json_response({"error": "Message not found"}, status=404)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)
