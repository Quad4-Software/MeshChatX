# SPDX-License-Identifier: MIT
"""Minimal Android BLE stack for RNS RNodeInterface on Chaquopy.

API-compatible with the subset of ``able`` that Reticulum's Android
RNodeInterface imports. Uses org.able.BLE (Java) plus Chaquopy proxies
instead of Kivy / pyjnius.
"""

from __future__ import annotations

from able.structures import Advertisement, Services

GATT_SUCCESS = 0
STATE_CONNECTED = 2
STATE_DISCONNECTED = 0

__all__ = [
    "Advertisement",
    "BluetoothDispatcher",
    "GATT_SUCCESS",
    "Services",
    "STATE_CONNECTED",
    "STATE_DISCONNECTED",
]


def __getattr__(name: str):
    if name == "BluetoothDispatcher":
        from able.dispatcher import BluetoothDispatcher

        return BluetoothDispatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
