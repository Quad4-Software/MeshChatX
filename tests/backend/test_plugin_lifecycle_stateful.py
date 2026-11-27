# SPDX-License-Identifier: 0BSD

"""RuleBasedStateMachine over the plugin install/enable/disable/remove lifecycle.

The model tracks which plugins exist and whether they are enabled. Invariants
check that the manager agrees with the model after every step and that error
paths never corrupt state.
"""

import json
import os

from hypothesis import settings
from hypothesis.stateful import (
    Bundle,
    RuleBasedStateMachine,
    invariant,
    rule,
)

PLUGIN_IDS = [
    "com.example.alpha",
    "com.example.beta",
    "net.test.gamma",
]


def _write_plugin_dir(base, plugin_id):
    source = os.path.join(str(base), plugin_id)
    os.makedirs(source, exist_ok=True)
    manifest = {
        "id": plugin_id,
        "version": "1.0.0",
        "apiVersion": 1,
        "name": f"Stateful {plugin_id}",
        "permissions": {},
    }
    with open(os.path.join(source, "plugin.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh)
    with open(os.path.join(source, "main.js"), "w", encoding="utf-8") as fh:
        fh.write("// stateful test plugin\n")
    return source


class PluginLifecycleMachine(RuleBasedStateMachine):
    plugins = Bundle("plugins")

    def __init__(self):
        super().__init__()
        import tempfile

        self._tmp = tempfile.TemporaryDirectory()
        self.storage = os.path.join(self._tmp.name, "storage")
        self.sources = os.path.join(self._tmp.name, "sources")
        os.makedirs(self.storage, exist_ok=True)
        os.makedirs(self.sources, exist_ok=True)
        from meshchatx.src.backend.plugin_manager import PluginManager

        self.manager = PluginManager(self.storage)
        # model: plugin_id -> {"installed": bool, "enabled": bool}
        self.model = {}

    def teardown(self):
        self._tmp.cleanup()

    @rule(
        target=plugins,
        pid_idx=__import__("hypothesis").strategies.integers(
            min_value=0, max_value=len(PLUGIN_IDS) - 1
        ),
    )
    def install(self, pid_idx):
        plugin_id = PLUGIN_IDS[pid_idx]
        source = _write_plugin_dir(self.sources, plugin_id)
        try:
            self.manager.install_from_directory(source)
            # Reinstall preserves the persisted enabled state.
            was_enabled = self.model.get(plugin_id, {}).get("enabled", False)
            self.model[plugin_id] = {"installed": True, "enabled": was_enabled}
        except ValueError:
            # Install failures must not partially register the plugin.
            assert plugin_id not in {
                p["id"] for p in self.manager.list_plugins()
            } or self.model.get(plugin_id, {}).get("installed", False)
        return plugin_id

    @rule(plugin=plugins)
    def enable(self, plugin):
        if not self.model.get(plugin, {}).get("installed"):
            return
        result = self.manager.enable(plugin)
        assert result["enabled"] is True
        self.model[plugin]["enabled"] = True

    @rule(plugin=plugins)
    def disable(self, plugin):
        if not self.model.get(plugin, {}).get("installed"):
            return
        result = self.manager.disable(plugin)
        assert result["enabled"] is False
        self.model[plugin]["enabled"] = False

    @rule(plugin=plugins)
    def remove(self, plugin):
        if not self.model.get(plugin, {}).get("installed"):
            return
        self.manager.remove(plugin)
        self.model[plugin] = {"installed": False, "enabled": False}

    @invariant()
    def manager_listing_matches_model(self):
        listed = {p["id"]: p for p in self.manager.list_plugins()}
        for plugin_id, state in self.model.items():
            if state["installed"]:
                assert plugin_id in listed, f"{plugin_id} missing from listing"
                assert listed[plugin_id]["enabled"] == state["enabled"], (
                    f"{plugin_id} enabled={listed[plugin_id]['enabled']} "
                    f"but model expects {state['enabled']}"
                )
            else:
                assert plugin_id not in listed, f"removed {plugin_id} still listed"
        # Nothing may appear in the listing that the model does not know.
        for plugin_id in listed:
            assert self.model.get(plugin_id, {}).get("installed", False), (
                f"unexpected plugin {plugin_id} in listing"
            )

    @invariant()
    def install_dirs_match_listing(self):
        installed_dir = self.manager.installed_dir
        on_disk = set()
        if os.path.isdir(installed_dir):
            on_disk = {
                entry
                for entry in os.listdir(installed_dir)
                if os.path.isfile(os.path.join(installed_dir, entry, "plugin.json"))
            }
        expected = {pid for pid, state in self.model.items() if state["installed"]}
        assert on_disk == expected, (
            f"disk {sorted(on_disk)} != model {sorted(expected)}"
        )


TestPluginLifecycle = PluginLifecycleMachine.TestCase
TestPluginLifecycle.settings = settings(
    max_examples=40,
    stateful_step_count=25,
    deadline=None,
)
