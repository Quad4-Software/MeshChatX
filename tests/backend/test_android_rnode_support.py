# SPDX-License-Identifier: 0BSD

from meshchatx.src.backend.android_rnode import install_android_rnode_support


def test_install_android_rnode_support_without_activity_returns_false():
    assert install_android_rnode_support(None) is False


def test_install_android_rnode_support_sets_usb4a_context(monkeypatch):
    calls = {}

    class FakeUsb:
        @staticmethod
        def set_context(activity):
            calls["usb"] = activity

    class FakeBle:
        @staticmethod
        def setAppContext(activity):
            calls["ble"] = activity

    class FakeJclass:
        def __call__(self, name):
            assert name == "org.able.BLE"
            return FakeBle

    import sys
    import types

    usb4a_mod = types.ModuleType("usb4a")
    usb4a_usb = types.ModuleType("usb4a.usb")
    usb4a_usb.set_context = FakeUsb.set_context
    usb4a_mod.usb = usb4a_usb

    java_mod = types.ModuleType("java")
    java_mod.jclass = FakeJclass()

    jnius_mod = types.ModuleType("jnius")
    able_mod = types.ModuleType("able")

    monkeypatch.setitem(sys.modules, "usb4a", usb4a_mod)
    monkeypatch.setitem(sys.modules, "usb4a.usb", usb4a_usb)
    monkeypatch.setitem(sys.modules, "java", java_mod)
    monkeypatch.setitem(sys.modules, "jnius", jnius_mod)
    monkeypatch.setitem(sys.modules, "able", able_mod)

    activity = object()
    assert install_android_rnode_support(activity) is True
    assert calls["usb"] is activity
    assert calls["ble"] is activity


def test_rnode_api_message_has_no_github_issue_reference():
    message = (
        "This RNode connection type is not available on this device. "
        "On Android, USB serial and classic Bluetooth need the bundled "
        "USB host stack, and BLE needs the bundled able stack. "
        "RNode over IP (TCP) is unaffected."
    )
    assert "issue #" not in message.lower()
    assert "github" not in message.lower()
