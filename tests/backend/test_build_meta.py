# SPDX-License-Identifier: 0BSD

from meshchatx.src import build_meta


def test_display_version_adds_dev_suffix(monkeypatch):
    monkeypatch.setattr(build_meta, "BUILD_CHANNEL", "testing")
    monkeypatch.setattr(build_meta, "IS_DEV_BUILD", True)
    assert build_meta.display_version("4.8.0") == "4.8.0-dev"
    assert build_meta.display_version("4.8.0-dev") == "4.8.0-dev"


def test_display_version_stable(monkeypatch):
    monkeypatch.setattr(build_meta, "BUILD_CHANNEL", "stable")
    monkeypatch.setattr(build_meta, "IS_DEV_BUILD", False)
    assert build_meta.display_version("4.8.0") == "4.8.0"


def test_normalize_channel_legacy_names():
    assert build_meta.normalize_channel("nightly") == "testing"
    assert build_meta.normalize_channel("preview") == "beta"
    assert build_meta.normalize_channel("release") == "stable"


def test_as_dict_includes_commit_fields(monkeypatch):
    monkeypatch.setattr(build_meta, "GIT_COMMIT", "abcdef0123456789")
    monkeypatch.setattr(build_meta, "GIT_COMMIT_SHORT", "abcdef0")
    monkeypatch.setattr(build_meta, "BUILD_CHANNEL", "nightly")
    monkeypatch.setattr(build_meta, "IS_DEV_BUILD", True)
    monkeypatch.setattr(
        build_meta,
        "CHANNEL_PROMPT_JSON",
        '{"bug_report_url":"https://example.test","bug_report_steps":["a"],"focus_areas":["b"],"notes":"n"}',
    )
    data = build_meta.as_dict("4.8.0")
    assert data["git_commit"] == "abcdef0123456789"
    assert data["git_commit_short"] == "abcdef0"
    assert data["build_channel"] == "testing"
    assert data["is_dev_build"] is True
    assert data["display_version"] == "4.8.0-dev"
    assert data["channel_prompt"]["focus_areas"] == ["b"]
    assert data["channel_prompt"]["notes"] == "n"
    assert "bug_report_lxmf" in data["channel_prompt"]
