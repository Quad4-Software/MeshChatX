# SPDX-License-Identifier: 0BSD
"""HTTP routes: telephone voicemail."""

from __future__ import annotations
# ruff: noqa: F405

from meshchatx.src.backend.http.routes.telephone._names import *  # noqa: F403, F405


def register_telephone_voicemail_routes(routes, app):

    # voicemail status
    @routes.get("/api/v1/telephone/voicemail/status")
    async def telephone_voicemail_status(request):
        greeting_path = os.path.join(
            app.voicemail_manager.greetings_dir,
            "greeting.opus",
        )
        return web.json_response(
            {
                "has_espeak": app.voicemail_manager.has_espeak,
                "is_recording": app.voicemail_manager.is_recording,
                "is_greeting_recording": app.voicemail_manager.is_greeting_recording,
                "has_greeting": os.path.exists(greeting_path),
            },
        )

    # start recording greeting from mic

    # start recording greeting from mic
    @routes.post("/api/v1/telephone/voicemail/greeting/record/start")
    async def telephone_voicemail_greeting_record_start(request):
        app.voicemail_manager.start_greeting_recording()
        return web.json_response({"message": "Started recording greeting"})

    # stop recording greeting from mic

    # stop recording greeting from mic
    @routes.post("/api/v1/telephone/voicemail/greeting/record/stop")
    async def telephone_voicemail_greeting_record_stop(request):
        app.voicemail_manager.stop_greeting_recording()
        return web.json_response({"message": "Stopped recording greeting"})

    # list voicemails

    # list voicemails
    @routes.get("/api/v1/telephone/voicemails")
    async def telephone_voicemails(request):
        search = request.query.get("search")
        limit = int(request.query.get("limit", 50))
        offset = int(request.query.get("offset", 0))
        voicemails_rows = app.database.voicemails.get_voicemails(
            search=search,
            limit=limit,
            offset=offset,
        )

        voicemails = []
        for row in voicemails_rows:
            d = dict(row)
            remote_identity_hash = d.get("remote_identity_hash")
            if remote_identity_hash:
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
            voicemails.append(d)

        return web.json_response(
            {
                "voicemails": voicemails,
                "unread_count": app.database.voicemails.get_unread_count(),
            },
        )

    # mark voicemail as read

    # mark voicemail as read
    @routes.post("/api/v1/telephone/voicemails/{id}/read")
    async def telephone_voicemail_mark_read(request):
        voicemail_id = request.match_info.get("id")
        app.database.voicemails.mark_as_read(voicemail_id)
        return web.json_response({"message": "Voicemail marked as read"})

    # delete voicemail

    # delete voicemail
    @routes.delete("/api/v1/telephone/voicemails/{id}")
    async def telephone_voicemail_delete(request):
        voicemail_id = request.match_info.get("id")
        voicemail = app.database.voicemails.get_voicemail(voicemail_id)
        if voicemail:
            filepath = safe_path_under_dir(
                app.voicemail_manager.recordings_dir,
                voicemail["filename"],
            )
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
            app.database.voicemails.delete_voicemail(voicemail_id)
            return web.json_response({"message": "Voicemail deleted"})
        return web.json_response({"message": "Voicemail not found"}, status=404)

    # serve greeting audio

    # serve greeting audio
    @routes.get("/api/v1/telephone/voicemail/greeting/audio")
    async def telephone_voicemail_greeting_audio(request):
        filepath = os.path.join(
            app.voicemail_manager.greetings_dir,
            "greeting.opus",
        )
        if os.path.exists(filepath):
            return web.FileResponse(
                filepath,
                headers={"Content-Type": "audio/opus"},
            )
        return web.json_response(
            {"message": "Greeting audio not found"},
            status=404,
        )

    # serve voicemail audio

    # serve voicemail audio
    @routes.get("/api/v1/telephone/voicemails/{id}/audio")
    async def telephone_voicemail_audio(request):
        voicemail_id = request.match_info.get("id")
        try:
            voicemail_id = int(voicemail_id)
        except (ValueError, TypeError):
            return web.json_response(
                {"message": "Invalid voicemail ID"},
                status=400,
            )

        if not app.voicemail_manager:
            return web.json_response(
                {"message": "Voicemail manager not available"},
                status=503,
            )

        voicemail = app.database.voicemails.get_voicemail(voicemail_id)
        if voicemail:
            filepath = safe_path_under_dir(
                app.voicemail_manager.recordings_dir,
                voicemail["filename"],
            )
            if filepath and os.path.exists(filepath):
                # Browsers might need a proper content type for .opus files
                return web.FileResponse(
                    filepath,
                    headers={"Content-Type": "audio/opus"},
                )
            RNS.log(
                f"Voicemail: Recording file missing for ID {voicemail_id}: {filepath}",
                RNS.LOG_ERROR,
            )
        return web.json_response(
            {"message": "Voicemail audio not found"},
            status=404,
        )

    # list call recordings

    # generate greeting
    @routes.post("/api/v1/telephone/voicemail/generate-greeting")
    async def telephone_voicemail_generate_greeting(request):
        try:
            text = app.config.voicemail_greeting.get()
            path = await asyncio.to_thread(
                app.voicemail_manager.generate_greeting,
                text,
            )
            return web.json_response(
                {"message": "Greeting generated", "path": path},
            )
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # upload greeting

    # upload greeting
    @routes.post("/api/v1/telephone/voicemail/greeting/upload")
    async def telephone_voicemail_greeting_upload(request):
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
                # Convert to greeting
                path = await asyncio.to_thread(
                    app.voicemail_manager.convert_to_greeting,
                    temp_path,
                )
                return web.json_response(
                    {"message": "Greeting uploaded and converted", "path": path},
                )
            finally:
                if os.path.exists(temp_path):
                    os.remove(temp_path)

        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # delete greeting

    # delete greeting
    @routes.delete("/api/v1/telephone/voicemail/greeting")
    async def telephone_voicemail_greeting_delete(request):
        try:
            app.voicemail_manager.remove_greeting()
            return web.json_response({"message": "Greeting deleted"})
        except Exception as e:
            return web.json_response({"message": str(e)}, status=500)

    # ringtone routes
