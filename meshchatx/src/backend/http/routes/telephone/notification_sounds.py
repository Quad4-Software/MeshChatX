# SPDX-License-Identifier: 0BSD
"""HTTP routes: telephone notification_sounds."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.telephone._names import *  # noqa: F403, F405


def register_telephone_notification_sounds_routes(routes, app):

    # notification sound routes
    @routes.get("/api/v1/notification-sounds")
    async def notification_sounds_get(request):
        sounds = app.database.notification_sounds.get_all()
        return web.json_response(
            [
                {
                    "id": s["id"],
                    "filename": s["filename"],
                    "display_name": s["display_name"],
                    "is_primary": bool(s["is_primary"]),
                    "created_at": s["created_at"],
                }
                for s in sounds
            ],
        )

    @routes.get("/api/v1/notification-sounds/status")
    async def notification_sound_status(request):
        try:
            sound_id = None

            preferred_id = app.config.notification_sound_preferred_id.get()
            if preferred_id and preferred_id > 0:
                sound_id = preferred_id

            if sound_id is None:
                primary = app.database.notification_sounds.get_primary()
                if primary:
                    sound_id = primary["id"]

            has_sound = sound_id is not None
            sound = (
                app.database.notification_sounds.get_by_id(sound_id)
                if sound_id
                else None
            )

            return web.json_response(
                {
                    "has_sound": has_sound and sound is not None,
                    "enabled": app.config.notification_sound_enabled.get(),
                    "filename": sound["filename"] if sound else None,
                    "id": sound_id,
                    "volume": app.config.notification_sound_volume.get() / 100.0,
                },
            )
        except Exception as e:
            logger.error(f"Error in notification_sound_status: {e}")
            return web.json_response(
                {
                    "has_sound": False,
                    "enabled": app.config.notification_sound_enabled.get(),
                    "filename": None,
                    "id": None,
                    "volume": app.config.notification_sound_volume.get() / 100.0,
                },
            )

    @routes.get("/api/v1/notification-sounds/{id}/audio")
    async def notification_sound_audio(request):
        sound_id = int(request.match_info["id"])
        sound = app.database.notification_sounds.get_by_id(sound_id)
        if not sound:
            return web.Response(status=404)

        if not app.notification_sound_manager:
            return web.Response(status=503)

        filepath = app.notification_sound_manager.get_ringtone_path(
            sound["storage_filename"],
        )
        if not filepath or not os.path.exists(filepath):
            return web.Response(status=404)

        safe_name = os.path.basename(str(sound.get("filename") or "sound.opus"))
        safe_name = (
            safe_name.replace('"', "").replace("\r", "").replace("\n", "")
            or "sound.opus"
        )
        return web.FileResponse(
            filepath,
            headers={
                "Content-Type": "audio/ogg",
                "Content-Disposition": f'attachment; filename="{safe_name}"',
            },
        )

    @routes.post("/api/v1/notification-sounds/upload")
    async def notification_sound_upload(request):
        if not app.notification_sound_manager:
            return web.json_response(
                {"message": "Notification sound manager unavailable"},
                status=503,
            )
        try:
            reader = await request.multipart()
            field = await first_multipart_file_field(reader)
            if field is None:
                return web.json_response(
                    {"message": "File field required"},
                    status=400,
                )

            filename = field.filename or "upload"
            extension = os.path.splitext(filename)[1].lower()
            if extension not in [".mp3", ".ogg", ".wav", ".m4a", ".flac"]:
                return web.json_response(
                    {"message": f"Unsupported file type: {extension}"},
                    status=400,
                )

            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
                temp_path = f.name
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

            try:
                storage_filename = await asyncio.to_thread(
                    app.notification_sound_manager.convert_to_ringtone,
                    temp_path,
                )

                sound_id = app.database.notification_sounds.add(
                    filename=filename,
                    storage_filename=storage_filename,
                )

                return web.json_response(
                    {
                        "message": "Notification sound uploaded and converted",
                        "id": sound_id,
                        "filename": filename,
                        "storage_filename": storage_filename,
                    },
                )
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.patch("/api/v1/notification-sounds/{id}")
    async def notification_sound_patch(request):
        try:
            sound_id = int(request.match_info["id"])
            data = await request.json()

            display_name = data.get("display_name")
            is_primary = 1 if data.get("is_primary") else None

            app.database.notification_sounds.update(
                sound_id,
                display_name=display_name,
                is_primary=is_primary,
            )

            return web.json_response({"message": "Notification sound updated"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.delete("/api/v1/notification-sounds/{id}")
    async def notification_sound_delete(request):
        try:
            sound_id = int(request.match_info["id"])
            sound = app.database.notification_sounds.get_by_id(sound_id)
            if sound:
                if app.notification_sound_manager:
                    app.notification_sound_manager.remove_ringtone(
                        sound["storage_filename"],
                    )
                app.database.notification_sounds.delete(sound_id)
            return web.json_response({"message": "Notification sound deleted"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # contacts routes
