# SPDX-License-Identifier: 0BSD

from meshchatx.src import build_meta


def test_display_version_adds_dev_suffix(monkeypatch):
    monkeypatch.setattr(build_meta, "IS_DEV_BUILD", True)
    assert build_meta.display_version("4.8.0") == "4.8.0-dev"
    assert build_meta.display_version("4.8.0-dev") == "4.8.0-dev"


def test_display_version_release(monkeypatch):
    monkeypatch.setattr(build_meta, "IS_DEV_BUILD", False)
    assert build_meta.display_version("4.8.0") == "4.8.0"


def test_as_dict_includes_commit_fields(monkeypatch):
    monkeypatch.setattr(build_meta, "GIT_COMMIT", "abcdef0123456789")
    monkeypatch.setattr(build_meta, "GIT_COMMIT_SHORT", "abcdef0")
    monkeypatch.setattr(build_meta, "BUILD_CHANNEL", "nightly")
    monkeypatch.setattr(build_meta, "IS_DEV_BUILD", True)
    data = build_meta.as_dict("4.8.0")
    assert data["git_commit"] == "abcdef0123456789"
    assert data["git_commit_short"] == "abcdef0"
    assert data["build_channel"] == "nightly"
    assert data["is_dev_build"] is True
    assert data["display_version"] == "4.8.0-dev"
