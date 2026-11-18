# SPDX-License-Identifier: 0BSD

"""Tests for update settings, manifest rules and the bandwidth guard.

Everything must stay opt-in: defaults perform no network work.
"""

import os
import sys
import time

import pytest

from meshchatx.src.backend import update_types as T
from meshchatx.src.backend.update_types import (
    UpdateError,
    UpdateSettings,
    UpdateUnavailable,
    UpdateVerifyError,
    auto_download_allowed,
    install_kind,
    jittered_interval_hours,
    online_interface_bitrates,
    pinned_signer_hashes,
    safe_artifact_name,
    slow_rns_link,
    updates_disabled,
    validate_https_url,
    validate_manifest,
    version_newer,
)


class FakeConfig:
    """Minimal dict-backed stand-in for ConfigManager."""

    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, default=None):
        return self.values.get(key, default)

    def set(self, key, value):
        self.values[key] = value


# ---------------------------------------------------------------------------
# defaults / disabled
# ---------------------------------------------------------------------------


def test_defaults_are_all_off():
    s = UpdateSettings()
    assert s.enabled is False
    assert s.auto_check is False
    assert s.auto_download is False
    assert s.peer_relay is False
    assert s.apply_policy == "manual"
    assert s.transport == "auto"
    assert s.channel == ""
    assert s.custom_mirrors == []
    assert s.signer_hashes == []
    assert s.rns_seeds == []


def test_from_config_defaults_off_with_empty_config():
    s = UpdateSettings.from_config(FakeConfig())
    assert s.enabled is False
    assert s.auto_check is False


def test_from_config_reads_persisted_values():
    cfg = FakeConfig(
        {
            "updates_enabled": "true",
            "update_auto_check": "true",
            "update_check_interval_hours": "12",
            "update_channel": "beta",
            "update_transport": "rns",
            "update_apply_policy": "on_restart",
            "update_custom_mirrors": '["https://mirror.example.com"]',
            "update_signer_hashes": '["%s"]' % ("ab" * 32),
            "update_rns_seeds": '["%s"]' % ("cd" * 16),
            "update_max_download_mb": "100",
        }
    )
    s = UpdateSettings.from_config(cfg)
    assert s.enabled is True
    assert s.auto_check is True
    assert s.check_interval_hours == 12.0
    assert s.channel == "beta"
    assert s.transport == "rns"
    assert s.apply_policy == "on_restart"
    assert s.custom_mirrors == [
        {"name": "custom", "kind": "static", "base": "https://mirror.example.com"}
    ]
    assert s.signer_hashes == ["ab" * 32]
    assert s.rns_seeds == ["cd" * 16]
    assert s.max_download_mb == 100


def test_from_config_clamps_interval_and_bad_values():
    s = UpdateSettings.from_config(
        FakeConfig(
            {
                "update_check_interval_hours": "1",  # below min -> clamped
                "update_transport": "bogus",  # invalid -> auto
                "update_apply_policy": "bogus",  # invalid -> manual
                "update_channel": "bogus",  # invalid -> ""
                "update_max_download_mb": "999999",  # clamped to 8192
            }
        )
    )
    assert s.check_interval_hours == T.MIN_CHECK_INTERVAL_HOURS
    assert s.transport == "auto"
    assert s.apply_policy == "manual"
    assert s.channel == ""
    assert s.max_download_mb == 8192


def test_updates_disabled_env(monkeypatch):
    monkeypatch.delenv("MESHCHATX_UPDATE_DISABLED", raising=False)
    assert updates_disabled() is False
    monkeypatch.setenv("MESHCHATX_UPDATE_DISABLED", "1")
    assert updates_disabled() is True


def test_updates_disabled_rollout_gate(monkeypatch):
    monkeypatch.delenv("MESHCHATX_UPDATE_DISABLED", raising=False)
    monkeypatch.delenv("MESHCHATX_UPDATE_ROLLOUT", raising=False)
    assert updates_disabled() is True
    monkeypatch.setenv("MESHCHATX_UPDATE_ROLLOUT", "1")
    assert updates_disabled() is False


# ---------------------------------------------------------------------------
# settings patch validation
# ---------------------------------------------------------------------------


def test_validate_patch_accepts_valid_values():
    s = UpdateSettings()
    clean = s.validate_patch(
        {
            "enabled": True,
            "auto_check": True,
            "auto_download": True,
            "peer_relay": True,
            "check_interval_hours": 12,
            "apply_policy": "on_restart",
            "channel": "testing",
            "transport": "clearnet",
            "custom_mirrors": ["https://a.example.com", "https://b.example.com/x"],
            "signer_hashes": ["AB" * 32],
            "max_download_mb": 500,
            "rns_rate_kbps": 128,
            "slow_link_kbps": 500,
            "rns_seeds": ["ef" * 16],
        }
    )
    assert clean["updates_enabled"] is True
    assert clean["update_channel"] == "testing"
    assert clean["update_transport"] == "clearnet"
    assert clean["update_apply_policy"] == "on_restart"
    assert '"https://a.example.com"' in clean["update_custom_mirrors"]
    assert ("ab" * 32) in clean["update_signer_hashes"]
    assert ("ef" * 16) in clean["update_rns_seeds"]


@pytest.mark.parametrize(
    "key,bad",
    [
        ("enabled", "yes"),
        ("auto_check", 1),
        ("auto_download", "true"),
        ("peer_relay", None),
    ],
)
def test_validate_patch_rejects_non_bool(key, bad):
    with pytest.raises(UpdateError):
        UpdateSettings().validate_patch({key: bad})


def test_validate_patch_interval_bounds():
    s = UpdateSettings()
    with pytest.raises(UpdateError):
        s.validate_patch({"check_interval_hours": 1})
    with pytest.raises(UpdateError):
        s.validate_patch({"check_interval_hours": 10000})
    with pytest.raises(UpdateError):
        s.validate_patch({"check_interval_hours": "abc"})
    ok = s.validate_patch({"check_interval_hours": 6})
    assert ok["update_check_interval_hours"] == 6.0


def test_validate_patch_rejects_bad_mirrors():
    s = UpdateSettings()
    for bad in [
        "http://evil.example.com",  # plain http off-loopback
        "https://user:pass@host.example.com",  # credentials
        "ftp://host.example.com",
        "not a url",
        "",
    ]:
        with pytest.raises(UpdateError):
            s.validate_patch({"custom_mirrors": [bad]})
    # loopback http is allowed for local testing
    ok = s.validate_patch({"custom_mirrors": ["http://127.0.0.1:8080"]})
    assert "127.0.0.1" in ok["update_custom_mirrors"]


def test_validate_patch_rejects_malformed_signer_hashes():
    s = UpdateSettings()
    for bad in ["zz" * 32, "ab" * 31, "ab" * 33, 12345, None]:
        with pytest.raises(UpdateError):
            s.validate_patch({"signer_hashes": [bad]})
    # too many
    with pytest.raises(UpdateError):
        s.validate_patch({"signer_hashes": ["ab" * 32] * 9})


def test_validate_patch_rejects_bad_enums_and_numbers():
    s = UpdateSettings()
    with pytest.raises(UpdateError):
        s.validate_patch({"channel": "nightly"})
    with pytest.raises(UpdateError):
        s.validate_patch({"transport": "carrier-pigeon"})
    with pytest.raises(UpdateError):
        s.validate_patch({"apply_policy": "always"})
    with pytest.raises(UpdateError):
        s.validate_patch({"max_download_mb": 0})
    with pytest.raises(UpdateError):
        s.validate_patch({"max_download_mb": "lots"})
    with pytest.raises(UpdateError):
        s.validate_patch({"rns_rate_kbps": 1})
    with pytest.raises(UpdateError):
        s.validate_patch({"slow_link_kbps": -5})
    with pytest.raises(UpdateError):
        s.validate_patch({"rns_seeds": ["not-hex"]})
    with pytest.raises(UpdateError):
        s.validate_patch({"rns_seeds": ["ab" * 32]})  # 64 hex is a hash, not a dest


def test_validate_https_url_rules():
    assert validate_https_url("https://example.com/x") == "https://example.com/x"
    assert validate_https_url("https://example.com/x/") == "https://example.com/x/"
    assert validate_https_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"
    assert validate_https_url("http://localhost:8000") == "http://localhost:8000"
    assert validate_https_url("http://[::1]:8000") == "http://[::1]:8000"
    assert validate_https_url("http://example.com") is None
    assert validate_https_url("https://user@example.com") is None


def test_safe_artifact_name():
    assert safe_artifact_name("MeshChatX-1.0.AppImage") == "MeshChatX-1.0.AppImage"
    for bad in [
        "../evil",
        "a/b",
        "a\\b",
        "",
        None,
        "-lead",
        "x" * 300,
        "with space",
        "semi;colon",
    ]:
        assert safe_artifact_name(bad) is None, bad


# ---------------------------------------------------------------------------
# manifest validation
# ---------------------------------------------------------------------------


def _manifest(version="9.9.9", channel="stable", artifacts=None, **kw):
    now = time.time()
    m = {
        "schema": 2,
        "app": "reticulum-meshchatx",
        "channel": channel,
        "version": version,
        "issued_at": now - 60,
        "valid_until": now + 86400,
        "min_supported_version": "0.0.1",
        "artifacts": artifacts
        if artifacts is not None
        else [
            {
                "name": "meshchatx-9.9.9-py3-none-any.whl",
                "size": 1234,
                "sha256": "ab" * 32,
                "kind": "wheel",
                "platform": "python",
                "arch": "any",
            }
        ],
    }
    m.update(kw)
    return m


def test_validate_manifest_accepts_matching_artifact():
    arts = validate_manifest(
        _manifest(),
        channel="stable",
        current_version="1.0.0",
    )
    assert len(arts) == 1
    assert arts[0]["name"] == "meshchatx-9.9.9-py3-none-any.whl"
    assert arts[0]["sha256"] == "ab" * 32


def test_validate_manifest_rejects_wrong_schema_and_app():
    with pytest.raises(UpdateVerifyError):
        validate_manifest(
            _manifest(schema=1), channel="stable", current_version="1.0.0"
        )
    with pytest.raises(UpdateVerifyError):
        validate_manifest(
            _manifest(app="other-app"), channel="stable", current_version="1.0.0"
        )


def test_validate_manifest_rejects_wrong_channel():
    with pytest.raises(UpdateVerifyError):
        validate_manifest(
            _manifest(channel="beta"), channel="stable", current_version="1.0.0"
        )
    # empty requested channel accepts manifest channel
    arts = validate_manifest(
        _manifest(channel="beta"), channel="", current_version="1.0.0"
    )
    assert len(arts) == 1


def test_validate_manifest_rejects_expired_and_future():
    now = time.time()
    with pytest.raises(UpdateVerifyError):
        validate_manifest(
            _manifest(valid_until=now - 10, issued_at=now - 100),
            channel="stable",
            current_version="1.0.0",
        )
    with pytest.raises(UpdateVerifyError):
        validate_manifest(
            _manifest(issued_at=now + 7200), channel="stable", current_version="1.0.0"
        )


def test_validate_manifest_downgrade_returns_empty():
    arts = validate_manifest(
        _manifest(version="0.9.0"), channel="stable", current_version="1.0.0"
    )
    assert arts == []
    # explicit allow_downgrade path: enforce_newer=False still returns arts
    arts = validate_manifest(
        _manifest(version="0.9.0"),
        channel="stable",
        current_version="1.0.0",
        enforce_newer=False,
    )
    assert len(arts) == 1


def test_validate_manifest_min_supported_version():
    with pytest.raises(UpdateUnavailable):
        validate_manifest(
            _manifest(min_supported_version="99.0.0"),
            channel="stable",
            current_version="1.0.0",
        )


def test_validate_manifest_filters_platform_arch_and_bad_entries():
    arts = validate_manifest(
        _manifest(
            artifacts=[
                {
                    "name": "win.exe",
                    "size": 10,
                    "sha256": "ab" * 32,
                    "kind": "exe",
                    "platform": "windows",
                    "arch": "x86_64",
                },
                {
                    "name": "mac.dmg",
                    "size": 10,
                    "sha256": "ab" * 32,
                    "kind": "dmg",
                    "platform": "macos",
                    "arch": "any",
                },
                {
                    "name": "good.whl",
                    "size": 10,
                    "sha256": "ab" * 32,
                    "kind": "wheel",
                    "platform": "python",
                    "arch": "any",
                },
                {
                    "name": "../evil",
                    "size": 10,
                    "sha256": "ab" * 32,
                    "kind": "wheel",
                    "platform": "python",
                    "arch": "any",
                },
                {
                    "name": "badsha.whl",
                    "size": 10,
                    "sha256": "zz",
                    "kind": "wheel",
                    "platform": "python",
                    "arch": "any",
                },
                {
                    "name": "huge.whl",
                    "size": 10**15,
                    "sha256": "ab" * 32,
                    "kind": "wheel",
                    "platform": "python",
                    "arch": "any",
                },
            ]
        ),
        channel="stable",
        current_version="1.0.0",
    )
    assert [a["name"] for a in arts] == ["good.whl"]


def test_validate_manifest_bad_shapes():
    for bad in [None, [], "x", 42]:
        with pytest.raises((UpdateVerifyError, TypeError)):
            validate_manifest(bad, channel="stable", current_version="1.0.0")
    with pytest.raises(UpdateVerifyError):
        validate_manifest(
            _manifest(artifacts="nope"), channel="stable", current_version="1.0.0"
        )


# ---------------------------------------------------------------------------
# low bandwidth guard
# ---------------------------------------------------------------------------


class _Iface:
    def __init__(self, bitrate, online=True):
        self.bitrate = bitrate
        self.online = online


def test_online_interface_bitrates_filters():
    ifaces = [_Iface(500_000), _Iface(10_000_000), _Iface(0, online=False)]
    assert online_interface_bitrates(ifaces) == [500_000, 10_000_000]
    assert online_interface_bitrates([]) == []


def test_slow_rns_link_threshold():
    assert slow_rns_link(1000, [_Iface(500_000)]) is True  # 0.5 Mbit
    assert slow_rns_link(1000, [_Iface(2_000_000)]) is False
    assert slow_rns_link(1000, []) is False  # unknown -> do not block
    # mixed: slowest wins
    assert slow_rns_link(1000, [_Iface(900_000), _Iface(50_000_000)]) is True


def test_auto_download_allowed_matrix():
    # auto_download off -> never
    ok, why = auto_download_allowed(UpdateSettings(auto_download=False))
    assert ok is False
    # clearnet transport always allowed
    s = UpdateSettings(auto_download=True, transport="clearnet")
    ok, _ = auto_download_allowed(s)
    assert ok is True
    # rns on slow link -> blocked
    s = UpdateSettings(auto_download=True, transport="rns")
    ok, why = auto_download_allowed(s, interfaces=[_Iface(100_000)])
    assert ok is False and "slow" in why
    # rns on fast link -> allowed
    ok, _ = auto_download_allowed(s, interfaces=[_Iface(10_000_000)])
    assert ok is True
    # auto: slow link, no config -> blocked
    s = UpdateSettings(auto_download=True, transport="auto")
    ok, why = auto_download_allowed(s, interfaces=[_Iface(100_000)])
    assert ok is False
    # auto: fast link -> allowed
    ok, _ = auto_download_allowed(s, interfaces=[_Iface(10_000_000)])
    assert ok is True


def test_jittered_interval_within_bounds():
    for _ in range(50):
        v = jittered_interval_hours(24.0)
        assert 24.0 * 0.9 <= v <= 24.0 * 1.1


def test_version_newer():
    assert version_newer("4.13.0", "4.12.0") is True
    assert version_newer("4.12.0", "4.12.0") is False
    assert version_newer("4.11.0", "4.12.0") is False
    assert version_newer("garbage", "4.12.0") is False


def test_pinned_signer_hashes():
    default = pinned_signer_hashes(None)
    assert len(default) == 1
    assert default[0].hex() == T.DEFAULT_SIGNER_HASH
    extra = pinned_signer_hashes(["ab" * 32, "not-hex", "cd" * 32])
    assert [h.hex() for h in extra] == ["ab" * 32, "cd" * 32]


def test_disclosure_lists_mirrors_and_signers():
    s = UpdateSettings(
        custom_mirrors=[
            {"name": "custom", "kind": "static", "base": "https://m.example.com"}
        ]
    )
    d = T.disclosure_for(s, "stable")
    assert d["mirrors"] == [{"name": "custom", "url": "https://m.example.com"}]
    assert d["rns_destination"] == T.RNS_UPDATE_ASPECT
    assert len(d["signer_hashes"]) == 1
    s2 = UpdateSettings()
    d2 = T.disclosure_for(s2, "beta")
    assert len(d2["mirrors"]) == 3
    assert d2["channel"] == "beta"


# ---------------------------------------------------------------------------
# install kind detection
# ---------------------------------------------------------------------------


def _bare_install_env(monkeypatch):
    for var in ("APPIMAGE", "FLATPAK_ID", "container"):
        monkeypatch.delenv(var, raising=False)
    real_exists = os.path.exists
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda p: (
            False if p in ("/.dockerenv", "/run/.containerenv") else real_exists(p)
        ),
    )


def test_install_kind_python_default(monkeypatch):
    _bare_install_env(monkeypatch)
    assert install_kind() == "python"


def test_install_kind_appimage(monkeypatch, tmp_path):
    _bare_install_env(monkeypatch)
    f = tmp_path / "MeshChatX.AppImage"
    f.write_bytes(b"x")
    monkeypatch.setenv("APPIMAGE", str(f))
    assert install_kind() == "appimage"
    f.unlink()
    assert install_kind() == "python"


def test_install_kind_flatpak(monkeypatch):
    _bare_install_env(monkeypatch)
    monkeypatch.setenv("FLATPAK_ID", "io.quad4.meshchatx")
    assert install_kind() == "flatpak"
    monkeypatch.setenv("container", "flatpak")
    assert install_kind() == "flatpak"


def test_install_kind_container(monkeypatch):
    _bare_install_env(monkeypatch)
    monkeypatch.setenv("container", "docker")
    assert install_kind() == "oci"
    monkeypatch.delenv("container", raising=False)
    real_exists = os.path.exists
    monkeypatch.setattr(
        os.path, "exists", lambda p: p == "/.dockerenv" or real_exists(p)
    )
    assert install_kind() == "oci"
    monkeypatch.setattr(
        os.path,
        "exists",
        lambda p: p == "/run/.containerenv" or real_exists(p),
    )
    assert install_kind() == "oci"


def test_install_kind_frozen_packaged(monkeypatch):
    _bare_install_env(monkeypatch)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "platform", "win32")
    assert install_kind() == "exe"
    monkeypatch.setattr(sys, "platform", "darwin")
    assert install_kind() == "dmg"
    monkeypatch.setattr(sys, "platform", "linux")
    assert install_kind() == "python"
