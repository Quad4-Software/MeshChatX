# SPDX-License-Identifier: 0BSD
"""HTTP routes: translator/translator."""

from __future__ import annotations

from typing import Any

# ruff: noqa: F401, F403, F405
from meshchatx.src.backend.http.routes.translator._names import *  # noqa: F403


def register_translator_translator_routes(routes: Any, app: Any) -> None:

    @routes.get("/api/v1/translator/languages")
    async def translator_languages(request):
        try:
            libretranslate_url = request.query.get("libretranslate_url")
            if libretranslate_url or (
                app.translator_handler
                and app.translator_handler.translator_libretranslate_enabled
            ):
                app._require_outbound_http("translator language lookup")
            th = app.translator_handler
            out = th.get_translator_languages_response(
                libretranslate_url=libretranslate_url,
            )
            return web.json_response(
                {
                    "languages": out["languages"],
                    "has_argos": th.has_argos,
                    "has_argos_lib": th.has_argos_lib,
                    "has_argos_cli": th.has_argos_cli,
                    "libre_client_available": th.has_requests,
                    "libretranslate_reachable": out["libretranslate_reachable"],
                },
            )
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except OutboundHttpBlockedError as e:
            return web.json_response({"message": str(e)}, status=403)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/translator/translate")
    async def translator_translate(request):
        data = await request.json()
        text = data.get("text", "")
        source_lang = data.get("source_lang", "auto")
        target_lang = data.get("target_lang", "")
        use_argos = bool(data.get("use_argos", False))
        libretranslate_url = data.get("libretranslate_url")
        libretranslate_api_key = data.get("libretranslate_api_key")

        if not text:
            return web.json_response(
                {"message": "Text cannot be empty"},
                status=400,
            )

        if not target_lang:
            return web.json_response(
                {"message": "Target language is required"},
                status=400,
            )

        try:
            if not use_argos:
                app._require_outbound_http("LibreTranslate")
            result = app.translator_handler.translate_text(
                text=text,
                source_lang=source_lang,
                target_lang=target_lang,
                use_argos=use_argos,
                libretranslate_url=libretranslate_url,
                libretranslate_api_key=libretranslate_api_key,
            )
            return web.json_response(result)
        except ValueError as e:
            return web.json_response({"message": str(e)}, status=400)
        except OutboundHttpBlockedError as e:
            return web.json_response({"message": str(e)}, status=403)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )

    @routes.post("/api/v1/translator/install-languages")
    async def translator_install_languages(request):
        data = await request.json()
        package_name = data.get("package", "translate")

        try:
            app._require_outbound_http("Argos language package install")
            result = app.translator_handler.install_language_package(package_name)
            return web.json_response(result)
        except Exception as e:
            return web.json_response(
                {"message": str(e)},
                status=500,
            )
