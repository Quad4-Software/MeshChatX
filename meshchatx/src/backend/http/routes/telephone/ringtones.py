# SPDX-License-Identifier: 0BSD
"""HTTP routes: telephone ringtones."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.telephone._names import *  # noqa: F403, F405


def register_telephone_ringtones_routes(routes, app):

    # ringtone routes
    @routes.get("/api/v1/telephone/ringtones")
    async def telephone_ringtones_get(request):
        ringtones = app.database.ringtones.get_all()
        return web.json_response(
            [
                {
                    "id": r["id"],
                    "filename": r["filename"],
                    "display_name": r["display_name"],
                    "is_primary": bool(r["is_primary"]),
                    "created_at": r["created_at"],
                }
                for r in ringtones
            ],
        )

    @routes.get("/api/v1/telephone/ringtones/status")
    async def telephone_ringtone_status(request):
        try:
            caller_hash = request.query.get("caller_hash")

            ringtone_id = None

            # 1. check contact preferred ringtone
            if caller_hash:
                contact = app.database.contacts.get_contact_by_identity_hash(
                    caller_hash,
                )
                if contact and contact.get("preferred_ringtone_id"):
                    ringtone_id = contact["preferred_ringtone_id"]

            # 2. check global preferred for non-contacts
            if ringtone_id is None:
                preferred_id = app.config.ringtone_preferred_id.get()
                if preferred_id:
                    ringtone_id = preferred_id

            # 3. fallback to primary
            if ringtone_id is None:
                primary = app.database.ringtones.get_primary()
                if primary:
                    ringtone_id = primary["id"]

            # 4. handle random if selected (-1)
            if ringtone_id == -1:
                import random

                ringtones = app.database.ringtones.get_all()
                if ringtones:
                    ringtone_id = random.choice(ringtones)["id"]
                else:
                    ringtone_id = None

            has_custom = ringtone_id is not None
            ringtone = (
                app.database.ringtones.get_by_id(ringtone_id) if has_custom else None
            )

            return web.json_response(
                {
                    "has_custom_ringtone": has_custom and ringtone is not None,
                    "enabled": app.config.custom_ringtone_enabled.get(),
                    "filename": ringtone["filename"] if ringtone else None,
                    "id": ringtone_id if ringtone_id != -1 else None,
                    "volume": app.config.ringtone_volume.get() / 100.0,
                },
            )
        except Exception as e:
            logger.error(f"Error in telephone_ringtone_status: {e}")
            return web.json_response(
                {
                    "has_custom_ringtone": False,
                    "enabled": app.config.custom_ringtone_enabled.get(),
                    "filename": None,
                    "id": None,
                    "volume": app.config.ringtone_volume.get() / 100.0,
                },
            )

    @routes.get("/api/v1/telephone/ringtones/{id}/audio")
    async def telephone_ringtone_audio(request):
        ringtone_id = int(request.match_info["id"])
        ringtone = app.database.ringtones.get_by_id(ringtone_id)
        if not ringtone:
            return web.json_response({"message": "Ringtone not found"}, status=404)

        download = request.query.get("download") == "1"

        filepath = app.ringtone_manager.get_ringtone_path(
            ringtone["storage_filename"],
        )
        if filepath and os.path.exists(filepath):
            if download:
                safe_name = os.path.basename(
                    str(ringtone.get("filename") or "ringtone.opus"),
                )
                safe_name = (
                    safe_name.replace('"', "").replace("\r", "").replace("\n", "")
                    or "ringtone.opus"
                )
                return web.FileResponse(
                    filepath,
                    headers={
                        "Content-Disposition": f'attachment; filename="{safe_name}"',
                    },
                )
            return web.FileResponse(filepath)
        return web.json_response(
            {"message": "Ringtone audio file not found"},
            status=404,
        )

    @routes.post("/api/v1/telephone/ringtones/upload")
    async def telephone_ringtone_upload(request):
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

            # Save temp file
            with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as f:
                temp_path = f.name
                while True:
                    chunk = await field.read_chunk()
                    if not chunk:
                        break
                    f.write(chunk)

            try:
                # Convert to ringtone
                storage_filename = await asyncio.to_thread(
                    app.ringtone_manager.convert_to_ringtone,
                    temp_path,
                )

                # Add to database
                ringtone_id = app.database.ringtones.add(
                    filename=filename,
                    storage_filename=storage_filename,
                )

                return web.json_response(
                    {
                        "message": "Ringtone uploaded and converted",
                        "id": ringtone_id,
                        "filename": filename,
                        "storage_filename": storage_filename,
                    },
                )
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.patch("/api/v1/telephone/ringtones/{id}")
    async def telephone_ringtone_patch(request):
        try:
            ringtone_id = int(request.match_info["id"])
            data = await request.json()

            display_name = data.get("display_name")
            is_primary = 1 if data.get("is_primary") else None

            app.database.ringtones.update(
                ringtone_id,
                display_name=display_name,
                is_primary=is_primary,
            )

            return web.json_response({"message": "Ringtone updated"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    @routes.delete("/api/v1/telephone/ringtones/{id}")
    async def telephone_ringtone_delete(request):
        try:
            ringtone_id = int(request.match_info["id"])
            ringtone = app.database.ringtones.get_by_id(ringtone_id)
            if ringtone:
                app.ringtone_manager.remove_ringtone(ringtone["storage_filename"])
                app.database.ringtones.delete(ringtone_id)
            return web.json_response({"message": "Ringtone deleted"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # notification sound routes
