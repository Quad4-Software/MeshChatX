# SPDX-License-Identifier: 0BSD

import asyncio
import concurrent.futures
import os
import re
import shutil
import subprocess
from typing import Any

from meshchatx.src.backend.http_url_guard import (
    UnsafeOutboundUrlError,
    normalize_loopback_http_service_base,
)

try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False

try:
    from argostranslate import package, translate

    HAS_ARGOS_LIB = True
except ImportError:
    HAS_ARGOS_LIB = False

ARGOS_CLI_EXECUTABLE_NAMES = ("argos-translate", "argostranslate")


def _find_argos_cli_executable() -> str | None:
    """Resolve the Argos CLI on PATH (checked at call time, not import time)."""
    for name in ARGOS_CLI_EXECUTABLE_NAMES:
        path = shutil.which(name)
        if path:
            return path
    return None


LANGUAGE_CODE_TO_NAME = {
    "en": "English",
    "de": "German",
    "es": "Spanish",
    "fr": "French",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "zh": "Chinese",
    "ja": "Japanese",
    "ko": "Korean",
    "ar": "Arabic",
    "hi": "Hindi",
    "nl": "Dutch",
    "pl": "Polish",
    "tr": "Turkish",
    "sv": "Swedish",
    "da": "Danish",
    "no": "Norwegian",
    "fi": "Finnish",
    "cs": "Czech",
    "ro": "Romanian",
    "hu": "Hungarian",
    "el": "Greek",
    "he": "Hebrew",
    "th": "Thai",
    "vi": "Vietnamese",
    "id": "Indonesian",
    "uk": "Ukrainian",
    "bg": "Bulgarian",
    "hr": "Croatian",
    "sk": "Slovak",
    "sl": "Slovenian",
    "et": "Estonian",
    "lv": "Latvian",
    "lt": "Lithuanian",
    "mt": "Maltese",
    "ga": "Irish",
    "cy": "Welsh",
}


def _sync_run_coro(coro):
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


class TranslatorHandler:
    def __init__(
        self,
        libretranslate_url: str | None = None,
        translator_argos_enabled: bool = False,
        translator_libretranslate_enabled: bool = False,
    ):
        self.translator_argos_enabled = translator_argos_enabled
        self.translator_libretranslate_enabled = translator_libretranslate_enabled
        self.libretranslate_url = libretranslate_url or os.getenv(
            "LIBRETRANSLATE_URL",
            "http://localhost:5000",
        )
        self.has_argos_lib = HAS_ARGOS_LIB
        self._argos_cli_executable = _find_argos_cli_executable()
        self.has_argos_cli = self._argos_cli_executable is not None
        self.has_argos = self.has_argos_lib or self.has_argos_cli
        self.has_requests = HAS_AIOHTTP

    def _any_backend_config_enabled(self) -> bool:
        return self.translator_argos_enabled or self.translator_libretranslate_enabled

    @property
    def enabled(self) -> bool:
        return self._any_backend_config_enabled()

    @enabled.setter
    def enabled(self, value: bool) -> None:
        self.translator_argos_enabled = value
        self.translator_libretranslate_enabled = value

    async def _fetch_languages_async(self, url: str):
        base = url.rstrip("/")
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(
                f"{base}/languages",
                allow_redirects=False,
            ) as response:
                if response.status == 200:
                    return await response.json()
        return None

    def get_translator_languages_response(
        self,
        libretranslate_url: str | None = None,
    ) -> dict[str, Any]:
        """List installed/reachable language pairs for UI; not gated on enable toggles."""
        languages: list[dict[str, str]] = []
        libretranslate_reachable = False

        url = libretranslate_url or self.libretranslate_url
        explicit_override = (
            libretranslate_url is not None and str(libretranslate_url).strip() != ""
        )
        libre_base = None
        if self.has_requests:
            try:
                libre_base = normalize_loopback_http_service_base(url)
            except UnsafeOutboundUrlError as e:
                if explicit_override:
                    msg = str(e)
                    raise ValueError(msg) from e
                libre_base = None
            if libre_base is not None:
                try:
                    libretranslate_langs = _sync_run_coro(
                        self._fetch_languages_async(libre_base),
                    )
                    if libretranslate_langs is not None:
                        libretranslate_reachable = True
                        languages.extend(
                            {
                                "code": lang.get("code"),
                                "name": lang.get("name"),
                                "source": "libretranslate",
                            }
                            for lang in libretranslate_langs
                        )
                except Exception as e:
                    print(f"Failed to fetch LibreTranslate languages: {e}")

        if self.has_argos_lib:
            try:
                installed_packages = package.get_installed_packages()
                argos_langs = set()
                for pkg in installed_packages:
                    argos_langs.add((pkg.from_code, pkg.from_name))
                    argos_langs.add((pkg.to_code, pkg.to_name))

                for code, name in sorted(argos_langs):
                    languages.append(
                        {
                            "code": code,
                            "name": name,
                            "source": "argos",
                        },
                    )
            except Exception as e:
                print(f"Failed to fetch Argos languages: {e}")
        elif self.has_argos_cli:
            try:
                cli_langs = self._get_argos_languages_cli()
                languages.extend(cli_langs)
            except Exception as e:
                print(f"Failed to fetch Argos languages via CLI: {e}")

        return {
            "languages": languages,
            "libretranslate_reachable": libretranslate_reachable,
        }

    def get_supported_languages(self, libretranslate_url: str | None = None) -> list:
        return self.get_translator_languages_response(
            libretranslate_url=libretranslate_url,
        )["languages"]

    def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        use_argos: bool = False,
        libretranslate_url: str | None = None,
    ) -> dict[str, Any]:
        if not self._any_backend_config_enabled():
            msg = "Translator is disabled"
            raise RuntimeError(msg)

        if not text:
            msg = "Text cannot be empty"
            raise ValueError(msg)

        if use_argos:
            if not self.translator_argos_enabled or not self.has_argos:
                msg = "Argos translation is not enabled or not available"
                raise RuntimeError(msg)
            return self._translate_argos(text, source_lang, target_lang)

        if self.translator_libretranslate_enabled and self.has_requests:
            url_raw = libretranslate_url or self.libretranslate_url
            try:
                url = normalize_loopback_http_service_base(url_raw)
            except UnsafeOutboundUrlError as e:
                msg = str(e)
                raise ValueError(msg) from e
            try:
                return self._translate_libretranslate(
                    text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    libretranslate_url=url,
                )
            except Exception as e:
                if self.translator_argos_enabled and self.has_argos:
                    return self._translate_argos(text, source_lang, target_lang)
                raise e

        if self.translator_argos_enabled and self.has_argos:
            return self._translate_argos(text, source_lang, target_lang)

        msg = "No translation backend available. Install aiohttp for LibreTranslate or argostranslate for local translation."
        raise RuntimeError(msg)

    async def _translate_libretranslate_async(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        libretranslate_url: str,
    ) -> dict[str, Any]:
        base = libretranslate_url.rstrip("/")
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{base}/translate",
                json={
                    "q": text,
                    "source": source_lang,
                    "target": target_lang,
                    "format": "text",
                },
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    body = await response.text()
                    msg = f"LibreTranslate API error: {response.status} - {body}"
                    raise RuntimeError(msg)
                result = await response.json()
        return {
            "translated_text": result.get("translatedText", ""),
            "source_lang": result.get("detectedLanguage", {}).get(
                "language",
                source_lang,
            ),
            "target_lang": target_lang,
            "source": "libretranslate",
        }

    def _translate_libretranslate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        libretranslate_url: str | None = None,
    ) -> dict[str, Any]:
        if not self.has_requests:
            msg = "aiohttp library not available"
            raise RuntimeError(msg)

        url = libretranslate_url or self.libretranslate_url
        return _sync_run_coro(
            self._translate_libretranslate_async(
                text,
                source_lang,
                target_lang,
                url,
            ),
        )

    def _translate_argos(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> dict[str, Any]:
        if source_lang == "auto":
            if self.has_argos_lib:
                detected_lang = self._detect_language(text)
                if detected_lang:
                    source_lang = detected_lang
                else:
                    msg = "Could not auto-detect language. Please select a source language manually."
                    raise ValueError(msg)
            else:
                msg = (
                    "Auto-detection is not supported with CLI-only installation. "
                    "Please select a source language manually or install the Python library: pip install argostranslate"
                )
                raise ValueError(msg)

        if self.has_argos_lib:
            return self._translate_argos_lib(text, source_lang, target_lang)
        if self.has_argos_cli:
            return self._translate_argos_cli(text, source_lang, target_lang)
        msg = "Argos Translate not available (neither library nor CLI)"
        raise RuntimeError(msg)

    def _translate_argos_lib(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> dict[str, Any]:
        try:
            installed_packages = package.get_installed_packages()
            translation_package = None

            for pkg in installed_packages:
                if pkg.from_code == source_lang and pkg.to_code == target_lang:
                    translation_package = pkg
                    break

            if translation_package is None:
                msg = (
                    f"No translation package found for {source_lang} -> {target_lang}. "
                    "Install packages using: argostranslate --update-languages"
                )
                raise ValueError(msg)

            translated_text = translate.translate(text, source_lang, target_lang)
            return {
                "translated_text": translated_text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "source": "argos",
            }
        except Exception as e:
            msg = f"Argos Translate error: {e}"
            raise RuntimeError(msg) from e

    def _translate_argos_cli(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
    ) -> dict[str, Any]:
        if source_lang == "auto" or not source_lang:
            msg = "Auto-detection is not supported with CLI. Please select a source language manually."
            raise ValueError(msg)

        if not target_lang:
            msg = "Target language is required."
            raise ValueError(msg)

        if not isinstance(source_lang, str) or not isinstance(target_lang, str):
            msg = "Language codes must be strings."
            raise ValueError(msg)

        if len(source_lang) != 2 or len(target_lang) != 2:
            msg = f"Invalid language codes: {source_lang} -> {target_lang}"
            raise ValueError(msg)

        executable = self._argos_cli_executable or _find_argos_cli_executable()
        if not executable:
            msg = (
                "Argos Translate CLI not found in PATH "
                f"(tried: {', '.join(ARGOS_CLI_EXECUTABLE_NAMES)})"
            )
            raise RuntimeError(msg)

        try:
            args = [
                executable,
                "--from-lang",
                source_lang,
                "--to-lang",
                target_lang,
                text,
            ]
            result = subprocess.run(args, capture_output=True, text=True, check=True)
            translated_text = result.stdout.strip()
            if not translated_text:
                msg = "Translation returned empty result"
                raise RuntimeError(msg)
            return {
                "translated_text": translated_text,
                "source_lang": source_lang,
                "target_lang": target_lang,
                "source": "argos",
            }
        except subprocess.CalledProcessError as e:
            error_msg = (
                e.stderr.decode()
                if isinstance(e.stderr, bytes)
                else (e.stderr or str(e))
            )
            msg = f"Argos Translate CLI error: {error_msg}"
            raise RuntimeError(msg) from e
        except Exception as e:
            msg = f"Argos Translate CLI error: {e!s}"
            raise RuntimeError(msg) from e

    def _detect_language(self, text: str) -> str | None:
        if not self.has_argos_lib:
            return None

        try:
            from argostranslate import translate

            installed_packages = package.get_installed_packages()
            if not installed_packages:
                return None

            detected = translate.detect_language(text)
            if detected:
                return detected.code
        except Exception as e:
            print(f"Language detection failed: {e}")

        return None

    def _get_argos_languages_cli(self) -> list[dict[str, str]]:
        languages = []
        argospm = shutil.which("argospm")
        if not argospm:
            return languages

        try:
            result = subprocess.run(
                [argospm, "list"],
                capture_output=True,
                text=True,
                timeout=10,
                check=True,
            )
            installed_packages = result.stdout.strip().split("\n")
            argos_langs = set()

            for pkg_name in installed_packages:
                if not pkg_name.strip():
                    continue
                match = re.match(r"translate-([a-z]{2})_([a-z]{2})", pkg_name.strip())
                if match:
                    from_code = match.group(1)
                    to_code = match.group(2)
                    argos_langs.add(from_code)
                    argos_langs.add(to_code)

            for code in sorted(argos_langs):
                name = LANGUAGE_CODE_TO_NAME.get(code, code.upper())
                languages.append(
                    {
                        "code": code,
                        "name": name,
                        "source": "argos",
                    },
                )
        except subprocess.CalledProcessError as e:
            print(f"argospm list failed: {e.stderr or str(e)}")
        except Exception as e:
            print(f"Error parsing argospm output: {e}")

        return languages

    def install_language_package(
        self,
        package_name: str = "translate",
    ) -> dict[str, Any]:
        argospm = shutil.which("argospm")
        if not argospm:
            msg = "argospm not found in PATH. Install argostranslate first."
            raise RuntimeError(msg)

        try:
            result = subprocess.run(
                [argospm, "install", package_name],
                capture_output=True,
                text=True,
                timeout=300,
                check=True,
            )
            return {
                "success": True,
                "message": f"Successfully installed {package_name}",
                "output": result.stdout,
            }
        except subprocess.TimeoutExpired as e:
            msg = f"Installation of {package_name} timed out after 5 minutes"
            raise RuntimeError(msg) from e
        except subprocess.CalledProcessError as e:
            msg = f"Failed to install {package_name}: {e.stderr or str(e)}"
            raise RuntimeError(msg) from e
        except Exception as e:
            msg = f"Error installing {package_name}: {e!s}"
            raise RuntimeError(msg) from e
