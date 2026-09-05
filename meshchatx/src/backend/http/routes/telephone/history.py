# SPDX-License-Identifier: 0BSD
"""HTTP routes: telephone history."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.telephone._names import *  # noqa: F403, F405


def register_telephone_history_routes(routes, app):

    # get call history
    @routes.get("/api/v1/telephone/history")
    async def telephone_history(request):
        limit = int(request.query.get("limit", 10))
        offset = int(request.query.get("offset", 0))
        search = request.query.get("search", None)
        history = app.database.telephone.get_call_history(
            search=search,
            limit=limit,
            offset=offset,
        )

        call_history = []
        for row in history:
            d = dict(row)
            remote_identity_hash = d.get("remote_identity_hash")
            if remote_identity_hash:
                # try to resolve name if unknown or missing
                if (
                    not d.get("remote_identity_name")
                    or d.get("remote_identity_name") == "Unknown"
                ):
                    resolved_name = app.get_name_for_identity_hash(
                        remote_identity_hash,
                    )
                    if resolved_name:
                        d["remote_identity_name"] = resolved_name

                lxmf_hash = app.get_lxmf_destination_hash_for_identity_hash(
                    remote_identity_hash,
                )
                tele_hash = app.get_lxst_telephony_hash_for_identity_hash(
                    remote_identity_hash,
                )
                if lxmf_hash:
                    d["remote_destination_hash"] = lxmf_hash
                    icon = app.database.misc.get_user_icon(lxmf_hash)
                    if icon:
                        d["remote_icon"] = dict(icon)
                if tele_hash:
                    d["remote_telephony_hash"] = tele_hash

                contact = app._resolve_contact_for_hash(remote_identity_hash)
                d["is_contact"] = contact is not None
                if contact:
                    d["contact_image"] = contact.get("custom_image")
            call_history.append(d)

        return web.json_response(
            {
                "call_history": call_history,
            },
        )

    # clear call history

    # clear call history
    @routes.delete("/api/v1/telephone/history")
    async def telephone_history_clear(request):
        app.database.telephone.clear_call_history()
        return web.json_response({"message": "ok"})

    # switch audio profile
