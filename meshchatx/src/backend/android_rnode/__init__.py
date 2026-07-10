# SPDX-License-Identifier: 0BSD
"""Install Chaquopy RNode USB / Bluetooth support before RNS starts."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def install_android_rnode_support(activity=None) -> bool:
    """Wire Activity context into usb4a and org.able.BLE.

    Returns True when the Android RNode support path was configured.
    Safe to call on desktop (no-op when Chaquopy java APIs are missing).
    """
    if activity is None:
        logger.warning("install_android_rnode_support called without Activity")
        return False

    configured = False

    try:
        from java import jclass

        ble_cls = jclass("org.able.BLE")
        ble_cls.setAppContext(activity)
        configured = True
        logger.info("Configured org.able.BLE app context for RNode BLE")
    except Exception as exc:
        logger.warning("Could not configure org.able.BLE context: %s", exc)

    try:
        from usb4a import usb as usb4a_usb

        usb4a_usb.set_context(activity)
        configured = True
        logger.info("Configured usb4a context for RNode USB serial")
    except Exception as exc:
        logger.warning("Could not configure usb4a context: %s", exc)

    try:
        import jnius  # noqa: F401

        logger.info("jnius Chaquopy shim importable for RNode serial/Bluetooth")
    except Exception as exc:
        logger.warning("jnius shim not importable: %s", exc)

    try:
        import able  # noqa: F401

        logger.info("able BLE package importable for RNode ble:// ports")
    except Exception as exc:
        logger.warning("able package not importable: %s", exc)

    return configured
