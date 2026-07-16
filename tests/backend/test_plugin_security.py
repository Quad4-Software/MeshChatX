# SPDX-License-Identifier: 0BSD

import io
import json
import os
import zipfile

import pytest

from meshchatx.src.backend.plugin_guard import (
    PluginSecurityError,
    normalize_asset_path,
    safe_extract_zip,
    validate_zip_bytes,
)


def _make_manager(tmp_path, app=None):
    from meshchatx.src.backend.plugin_manager import PluginManager

    return PluginManager(str(tmp_path), app=app)


def _write_plugin_dir(root, plugin_id="com.example.secure-plugin"):
    os.makedirs(root, exist_ok=True)
    manifest = {
        "id": plugin_id,
        "version": "1.0.0",
        "apiVersion": 1,
        "name": "Secure Plugin",
        "description": "Security test plugin",
        "frontend": {"entry": "frontend/main.js", "type": "js"},
        "i18n": {"directory": "locales", "defaultLocale": "en"},
    }
    with open(os.path.join(root, "plugin.json"), "w", encoding="utf-8") as handle:
        json.dump(manifest, handle)
    os.makedirs(os.path.join(root, "frontend"), exist_ok=True)
    with open(
        os.path.join(root, "frontend", "main.js"),
        "w",
        encoding="utf-8",
    ) as handle:
        handle.write(
            "export async function activate(api) { api.setUi({ type: 'text', value: 'ok' }); }",
        )
    os.makedirs(os.path.join(root, "locales"), exist_ok=True)
    with open(
        os.path.join(root, "locales", "en.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump({"title": "Secure Plugin"}, handle)


def _zip_directory(source_dir):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for base, _, files in os.walk(source_dir):
            for name in files:
                path = os.path.join(base, name)
                archive.write(path, os.path.relpath(path, source_dir))
    return buffer.getvalue()


class TestPluginGuard:
    def test_normalize_asset_path_rejects_traversal(self):
        with pytest.raises(PluginSecurityError):
            normalize_asset_path("../plugin.json")
        with pytest.raises(PluginSecurityError):
            normalize_asset_path("/etc/passwd")

    def test_validate_zip_bytes_rejects_empty_and_random_payload(self):
        with pytest.raises(PluginSecurityError):
            validate_zip_bytes(b"")
        with pytest.raises(PluginSecurityError):
            validate_zip_bytes(os.urandom(64))

    def test_safe_extract_zip_rejects_zip_slip(self, tmp_path):
        zip_path = tmp_path / "evil.zip"
        extract_dir = tmp_path / "extract"
        extract_dir.mkdir()
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("../escape.txt", "bad")
        with pytest.raises(PluginSecurityError):
            safe_extract_zip(str(zip_path), str(extract_dir))

    def test_install_zip_with_traversal_is_rejected(self, tmp_path):
        manager = _make_manager(tmp_path)
        zip_path = tmp_path / "evil.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("../escape.txt", "bad")
        with pytest.raises(PluginSecurityError):
            manager.install_from_zip_bytes(zip_path.read_bytes())

    def test_install_valid_zip_roundtrip(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "source"
        _write_plugin_dir(str(source))
        plugin = manager.install_from_zip_bytes(_zip_directory(str(source)))
        assert plugin["id"] == "com.example.secure-plugin"
        assert manager.locale_path(plugin["id"], "en").endswith("locales/en.json")

    def test_asset_path_blocks_traversal(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "source"
        _write_plugin_dir(str(source))
        manager.install_from_directory(str(source))
        with pytest.raises(PluginSecurityError):
            manager.asset_path("com.example.secure-plugin", "../plugin.json")

    def test_report_failure_auto_disables_after_budget(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "source"
        _write_plugin_dir(str(source))
        manager.install_from_directory(str(source))
        plugin_id = "com.example.secure-plugin"
        manager.enable(plugin_id)
        for _ in range(5):
            manager.report_failure(plugin_id, "worker crash", "frontend")
        plugin = manager.get_plugin(plugin_id)
        assert plugin is not None
        assert plugin["enabled"] is False
        assert plugin["auto_disabled_reason"]

    def test_enable_rejects_missing_frontend_entry(self, tmp_path):
        manager = _make_manager(tmp_path)
        source = tmp_path / "broken"
        os.makedirs(source, exist_ok=True)
        manifest = {
            "id": "com.example.broken",
            "version": "1.0.0",
            "apiVersion": 1,
            "frontend": {"entry": "frontend/missing.js", "type": "js"},
        }
        with open(os.path.join(source, "plugin.json"), "w", encoding="utf-8") as handle:
            json.dump(manifest, handle)
        manager.install_from_directory(str(source))
        with pytest.raises(FileNotFoundError):
            manager.enable("com.example.broken")

    @pytest.mark.parametrize(
        "payload",
        [
            b"\x91\x0c\xb0\xd9\xe8>\x1eZ \x00\x94\xbe\x9aJ\xf8\xed(u\xa6\xbf\xa9\x05\x8b\x80\xbe\x07\xf7>\x06b\xed",
            b"not-a-zip",
            b"\x00\x01\x02",
        ],
    )
    def test_fuzz_random_install_payloads_are_rejected(self, tmp_path, payload):
        manager = _make_manager(tmp_path)
        with pytest.raises(Exception):
            manager.install_from_zip_bytes(payload)
