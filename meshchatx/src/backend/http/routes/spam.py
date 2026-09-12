# SPDX-License-Identifier: 0BSD
"""HTTP routes: spam."""

from __future__ import annotations

from aiohttp import web

from meshchatx.src.backend.constants import API_V1_PREFIX
from meshchatx.src.backend.http.errors import (
    http_bad_request,
    http_error_from_exception,
    http_not_found,
    http_payload_too_large,
)
from meshchatx.src.backend.http.uploads import (
    PayloadTooLargeError,
    read_json_limited,
)


def register_spam_routes(routes, app):

    # get spam keywords
    @routes.get(API_V1_PREFIX + "/spam-keywords")
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

    # add spam keyword

    # add spam keyword
    @routes.post(API_V1_PREFIX + "/spam-keywords")
    async def spam_keywords_add(request):
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        keyword = data.get("keyword", "").strip()
        if not keyword:
            return http_bad_request("Keyword is required")

        try:
            app.database.misc.add_spam_keyword(keyword)
            return web.json_response({"message": "ok"})
        except Exception:
            return http_bad_request("Keyword already exists")

    # remove spam keyword

    # remove spam keyword
    @routes.delete(API_V1_PREFIX + "/spam-keywords/{keyword_id}")
    async def spam_keywords_delete(request):
        keyword_id = request.match_info.get("keyword_id", "")
        try:
            keyword_id = int(keyword_id)
        except (ValueError, TypeError):
            return http_bad_request("Invalid keyword ID")

        try:
            app.database.misc.delete_spam_keyword(keyword_id)
            return web.json_response({"message": "ok"})
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # mark message as spam or not spam

    # mark message as spam or not spam
    @routes.post(API_V1_PREFIX + "/lxmf-messages/{hash}/spam")
    async def lxmf_messages_spam(request):
        message_hash = request.match_info.get("hash", "")
        try:
            data = await read_json_limited(request)
        except PayloadTooLargeError:
            return http_payload_too_large()
        is_spam = data.get("is_spam", False)

        try:
            message = app.database.messages.get_lxmf_message_by_hash(message_hash)
            if message:
                message_data = dict(message)
                message_data["is_spam"] = 1 if is_spam else 0
                app.database.messages.upsert_lxmf_message(message_data)
                return web.json_response({"message": "ok"})
            return http_not_found("Message not found")
        except Exception as e:
            return http_error_from_exception(e, fallback_status=500)

    # get offline map metadata
