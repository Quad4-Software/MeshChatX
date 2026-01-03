import os
import re
import shutil
import subprocess
from typing import Any

try:
    import requests

    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from argostranslate import package, translate

    HAS_ARGOS_LIB = True
except ImportError:
    HAS_ARGOS_LIB = False

HAS_ARGOS_CLI = shutil.which("argos-translate") is not None
HAS_ARGOS = HAS_ARGOS_LIB or HAS_ARGOS_CLI

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


class TranslatorHandler:
    def __init__(self, libretranslate_url: str | None = None, enabled: bool = False):
        self.enabled = enabled
        self.libretranslate_url = libretranslate_url or os.getenv(
            "LIBRETRANSLATE_URL",
            "http://localhost:5000",
        )
        self.has_argos = HAS_ARGOS
        self.has_argos_lib = HAS_ARGOS_LIB
        self.has_argos_cli = HAS_ARGOS_CLI
        self.has_requests = HAS_REQUESTS

    def get_supported_languages(self, libretranslate_url: str | None = None):
        languages = []
        if not self.enabled:
            return languages

        url = libretranslate_url or self.libretranslate_url

        if self.has_requests:
            try:
                response = requests.get(f"{url}/languages", timeout=5)
                if response.status_code == 200:
                    libretranslate_langs = response.json()
                    languages.extend(
                        {
                            "code": lang.get("code"),
                            "name": lang.get("name"),
                            "source": "libretranslate",
                        }
                        for lang in libretranslate_langs
                    )
                    return languages
            except Exception as e:
                # Log or handle the exception appropriately
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

        return languages

    def translate_text(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        use_argos: bool = False,
        libretranslate_url: str | None = None,
    ) -> dict[str, Any]:
        if not self.enabled:
            msg = "Translator is disabled"
            raise RuntimeError(msg)

        if not text:
            msg = "Text cannot be empty"
            raise ValueError(msg)

        if use_argos and self.has_argos:
            return self._translate_argos(text, source_lang, target_lang)

        if self.has_requests:
            try:
                url = libretranslate_url or self.libretranslate_url
                return self._translate_libretranslate(
                    text,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    libretranslate_url=url,
                )
            except Exception as e:
                if self.has_argos:
                    return self._translate_argos(text, source_lang, target_lang)
                raise e

        if self.has_argos:
            return self._translate_argos(text, source_lang, target_lang)

        msg = "No translation backend available. Install requests for LibreTranslate or argostranslate for local translation."
        raise RuntimeError(msg)

    def _translate_libretranslate(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        libretranslate_url: str | None = None,
    ) -> dict[str, Any]:
        if not self.has_requests:
            msg = "requests library not available"
            raise RuntimeError(msg)

        url = libretranslate_url or self.libretranslate_url
        response = requests.post(
            f"{url}/translate",
            json={
                "q": text,
                "source": source_lang,
                "target": target_lang,
                "format": "text",
            },
            timeout=30,
        )

        if response.status_code != 200:
            msg = f"LibreTranslate API error: {response.status_code} - {response.text}"
            raise RuntimeError(msg)

        result = response.json()
        return {
            "translated_text": result.get("translatedText", ""),
            "source_lang": result.get("detectedLanguage", {}).get(
                "language",
                source_lang,
            ),
            "target_lang": target_lang,
            "source": "libretranslate",
        }

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
            raise RuntimeError(msg)

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

        executable = shutil.which("argos-translate")
        if not executable:
            msg = "argos-translate executable not found in PATH"
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
            result = subprocess.run(args, capture_output=True, text=True, check=True)  # noqa: S603
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
            raise RuntimeError(msg)
        except Exception as e:
            msg = f"Argos Translate CLI error: {e!s}"
            raise RuntimeError(msg)

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
            result = subprocess.run(  # noqa: S603
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
            result = subprocess.run(  # noqa: S603
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
        except subprocess.TimeoutExpired:
            msg = f"Installation of {package_name} timed out after 5 minutes"
            raise RuntimeError(msg)
        except subprocess.CalledProcessError as e:
            msg = f"Failed to install {package_name}: {e.stderr or str(e)}"
            raise RuntimeError(msg)
        except Exception as e:
            msg = f"Error installing {package_name}: {e!s}"
            raise RuntimeError(msg)
