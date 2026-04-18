# SPDX-License-Identifier: 0BSD

"""Optional integration checks for Argos CLI (skipped when not installed)."""

import shutil

import pytest

from meshchatx.src.backend.translator_handler import (
    ARGOS_CLI_EXECUTABLE_NAMES,
    TranslatorHandler,
    _find_argos_cli_executable,
)


def _argos_cli_on_path() -> bool:
    return _find_argos_cli_executable() is not None


@pytest.mark.integration
def test_find_argos_cli_matches_shutil_which():
    expected = None
    for name in ARGOS_CLI_EXECUTABLE_NAMES:
        expected = shutil.which(name)
        if expected:
            break
    assert _find_argos_cli_executable() == expected


@pytest.mark.integration
@pytest.mark.skipif(not _argos_cli_on_path(), reason="Argos CLI not on PATH")
def test_translate_en_es_via_cli_round_trip():
    handler = TranslatorHandler(enabled=True)
    assert handler.has_argos_cli
    assert not handler.has_argos_lib

    result = handler.translate_text("Hello", "en", "es", use_argos=True)
    assert result["source"] == "argos"
    assert result["source_lang"] == "en"
    assert result["target_lang"] == "es"
    assert len(result["translated_text"].strip()) > 0


@pytest.mark.integration
@pytest.mark.skipif(not _argos_cli_on_path(), reason="Argos CLI not on PATH")
def test_get_supported_languages_includes_argos_when_libretranslate_down():
    handler = TranslatorHandler(enabled=True)
    langs = handler.get_supported_languages()
    argos = [x for x in langs if x.get("source") == "argos"]
    assert len(argos) >= 1
