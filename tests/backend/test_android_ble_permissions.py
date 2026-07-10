# SPDX-License-Identifier: 0BSD
"""Regression guards for Android BLE permission lint and type stubs."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BLE_JAVA = REPO_ROOT / "android/app/src/main/java/org/able/BLE.java"
TYPINGS = REPO_ROOT / "typings"


def test_ble_java_checks_bluetooth_permissions_before_privileged_calls():
    source = BLE_JAVA.read_text(encoding="utf-8")
    assert '@SuppressLint("MissingPermission")' in source
    assert "hasScanPermission" in source
    assert "hasConnectPermission" in source
    assert "Manifest.permission.BLUETOOTH_SCAN" in source
    assert "Manifest.permission.BLUETOOTH_CONNECT" in source
    assert "ContextCompat.checkSelfPermission" in source
    assert "SecurityException" in source
    for method in (
        "startScan(",
        "stopScan(",
        "connectGatt(",
        "writeCharacteristic(",
        "readCharacteristic(",
        "readRemoteRssi(",
    ):
        assert method in source


def test_android_optional_import_typings_exist_for_basedpyright():
    required = (
        TYPINGS / "java" / "__init__.pyi",
        TYPINGS / "usb4a" / "__init__.pyi",
        TYPINGS / "usb4a" / "usb.pyi",
        TYPINGS / "able" / "__init__.pyi",
        TYPINGS / "jnius" / "__init__.pyi",
    )
    missing = [
        str(path.relative_to(REPO_ROOT)) for path in required if not path.is_file()
    ]
    assert missing == []
