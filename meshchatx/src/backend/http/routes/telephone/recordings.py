# SPDX-License-Identifier: 0BSD
"""HTTP routes: telephone recordings."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.telephone._names import *  # noqa: F403, F405


def register_telephone_recordings_routes(routes, app):

    # list call recordings
    @routes.get("/api/v1/telephone/recordings")
    async def telephone_recordings(request):
        search = request.query.get("search", None)
        limit = int(request.query.get("limit", 10))
        offset = int(request.query.get("offset", 0))
        recordings_rows = app.database.telephone.get_call_recordings(
            search=search,
            limit=limit,
            offset=offset,
        )
        recordings = []
        for row in recordings_rows:
            d = dict(row)
            remote_identity_hash = d.get("remote_identity_hash")
            if remote_identity_hash:
                lxmf_hash = app.get_lxmf_destination_hash_for_identity_hash(
                    remote_identity_hash,
                )
                if lxmf_hash:
                    icon = app.database.misc.get_user_icon(lxmf_hash)
                    if icon:
                        d["remote_icon"] = dict(icon)
            recordings.append(d)

        return web.json_response({"recordings": recordings})

    # serve call recording audio

    # serve call recording audio
    @routes.get("/api/v1/telephone/recordings/{id}/audio/{side}")
    async def telephone_recording_audio(request):
        recording_id = request.match_info.get("id")
        try:
            recording_id = int(recording_id)
        except (ValueError, TypeError):
            return web.json_response(
                {"message": "Invalid recording ID"},
                status=400,
            )

        side = request.match_info.get("side")
        if side not in ("rx", "tx"):
            return web.json_response(
                {"message": "Invalid recording side"},
                status=400,
            )
        recording = app.database.telephone.get_call_recording(recording_id)
        if recording:
            filename = recording[f"filename_{side}"]
            if not filename:
                return web.json_response(
                    {"message": f"No {side} recording found"},
                    status=404,
                )

            filepath = safe_path_under_dir(
                app.telephone_manager.recordings_dir,
                filename,
            )
            if filepath and os.path.exists(filepath):
                return web.FileResponse(
                    filepath,
                    headers={"Content-Type": "audio/opus"},
                )

        return web.json_response({"message": "Recording not found"}, status=404)

    # delete call recording

    # delete call recording
    @routes.delete("/api/v1/telephone/recordings/{id}")
    async def telephone_recording_delete(request):
        recording_id = request.match_info.get("id")
        recording = app.database.telephone.get_call_recording(recording_id)
        if recording:
            for side in ["rx", "tx"]:
                filename = recording[f"filename_{side}"]
                if filename:
                    filepath = safe_path_under_dir(
                        app.telephone_manager.recordings_dir,
                        filename,
                    )
                    if filepath and os.path.exists(filepath):
                        os.remove(filepath)
            app.database.telephone.delete_call_recording(recording_id)
        return web.json_response({"message": "ok"})

    # generate greeting
