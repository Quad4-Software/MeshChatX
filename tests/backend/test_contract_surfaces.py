# SPDX-License-Identifier: 0BSD
"""Contract surface tests: WS topic taxonomy and bundled plugin manifests.

These tests fail when a contract drifts: a broadcast type landing on a topic
that does not exist, a new type silently classifying as "other", or a bundled
plugin manifest losing validity or locale labels.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from meshchatx.src.backend.plugin_manager import PluginManager
from meshchatx.src.backend.plugin_permissions import (
    KNOWN_HOOKS,
    KNOWN_MANAGERS,
    declared_permission_ids,
)
from meshchatx.src.backend.websocket_runtime import (
    _TYPE_TOPIC,
    WS_ALL_TOPICS,
    topic_for_type,
)
from tests.backend.ws_contract_helpers import load_ws_manifest

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_WS_FIXTURE = os.path.join(
    _REPO, "tests", "backend", "fixtures", "ws_message_manifest.json"
)
_BUNDLED_PLUGINS = os.path.join(_REPO, "meshchatx", "src", "backend", "data", "plugins")
_EN_LOCALE = os.path.join(_REPO, "meshchatx", "src", "frontend", "locales", "en.json")

# Broadcast types intentionally delivered on the catch-all "other" topic.
# Update this allowlist only when a new catch-all type is introduced on purpose.
# Types that should reach topic-scoped subscribers belong in _TYPE_TOPIC or
# topic_for_type instead.
_TYPES_ALLOWED_ON_OTHER = frozenset(
    {
        "blocked_destinations",
        "identity_switched",
        "new_voicemail",
        "reticulum_reload_status",
        "rncp.fetch.completed",
        "rncp.send.completed",
        "rncp.transfer.progress",
        "rnsh.output",
        "rnsh.session.change",
        "rnx.output",
        "rnx.session.change",
        "startup_status",
    },
)


def _broadcast_types() -> set[str]:
    manifest = load_ws_manifest(Path(_WS_FIXTURE))
    return {t for t in manifest.get("server_broadcast", []) if isinstance(t, str)}


def test_type_topic_map_targets_known_topics():
    bad = {t: topic for t, topic in _TYPE_TOPIC.items() if topic not in WS_ALL_TOPICS}
    assert not bad, f"_TYPE_TOPIC entries pointing at unknown topics: {bad}"


def test_broadcast_types_never_silently_fall_to_other():
    """Broadcast types must not silently fall to "other".

    A type landing on "other" means subscribers of every real topic never
    receive it. Require an explicit allowlist instead.
    """
    stray = {
        t
        for t in _broadcast_types()
        if topic_for_type(t) == "other" and t not in _TYPES_ALLOWED_ON_OTHER
    }
    assert not stray, (
        f"Broadcast types with no explicit topic mapping (resolve to 'other'): "
        f"{sorted(stray)}. Add a mapping in websocket_runtime._TYPE_TOPIC or "
        f"topic_for_type, or extend _TYPES_ALLOWED_ON_OTHER if intentional."
    )


def test_known_topic_prefixes_cover_known_families():
    # Families that must never fall through to "other".
    for probe, expected in (
        ("lxmf.delivery", "lxmf"),
        ("rrc.message", "rrc"),
        ("plugin.event", "plugin"),
        ("rns.link.event", "rns.link"),
        ("nomadnet.page.download", "nomad"),
        ("config.changed", "config"),
        ("telephone_ringing", "telephone"),
        ("filesync.chunk", "filesync"),
    ):
        assert topic_for_type(probe) == expected


def test_bundled_plugin_manifests_validate():
    assert os.path.isdir(_BUNDLED_PLUGINS)
    manifests = []
    for entry in sorted(os.listdir(_BUNDLED_PLUGINS)):
        manifest_path = os.path.join(_BUNDLED_PLUGINS, entry, "plugin.json")
        assert os.path.isfile(manifest_path), (
            f"missing manifest for bundled plugin {entry}"
        )
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
        # Use the real validator as the authority.
        validated = PluginManager._validate_manifest(PluginManager, manifest)
        assert validated["id"].startswith("com.meshchatx.")
        manifests.append(manifest)
    assert manifests, "no bundled plugins found"


def test_bundled_plugin_permissions_use_known_capabilities():
    for entry in sorted(os.listdir(_BUNDLED_PLUGINS)):
        manifest_path = os.path.join(_BUNDLED_PLUGINS, entry, "plugin.json")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
        permissions = manifest.get("permissions") or {}
        for hook in permissions.get("hooks") or []:
            assert hook in KNOWN_HOOKS, f"{entry}: unknown hook {hook}"
        for manager in permissions.get("managers") or []:
            assert manager in KNOWN_MANAGERS, f"{entry}: unknown manager {manager}"


def test_declared_permissions_have_en_labels():
    """Permission ids in bundled manifests must have en.json labels.

    Missing plugins.permissions entries leave install dialogs showing raw
    capability ids.
    """
    with open(_EN_LOCALE, encoding="utf-8") as handle:
        en = json.load(handle)

    def lookup(key: str):
        cur = en
        for part in key.split("."):
            if not isinstance(cur, dict):
                return None
            cur = cur.get(part)
        return cur if isinstance(cur, str) else None

    for entry in sorted(os.listdir(_BUNDLED_PLUGINS)):
        manifest_path = os.path.join(_BUNDLED_PLUGINS, entry, "plugin.json")
        with open(manifest_path, encoding="utf-8") as handle:
            manifest = json.load(handle)
        for perm_id in declared_permission_ids(manifest):
            kind, _, name = perm_id.partition(":")
            # storage/network/ui modes and hooks have static label keys.
            label_key = f"plugins.permissions.{kind}.{name}"
            if kind == "managers":
                top, _, sub = name.partition(".")
                value = lookup(f"plugins.permissions.managers.{top}.{sub}")
            else:
                value = lookup(label_key)
            assert value is not None, (
                f"{entry}: permission {perm_id!r} has no en.json label at {label_key}"
            )
