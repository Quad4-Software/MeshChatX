# SPDX-License-Identifier: 0BSD

"""Runtime patches for RNS's desktop RNodeInterface.

RNS 1.5.4's BLE path has several defects that make ble:// RNode interfaces
unusable or flaky:

- connect_device runs each connection attempt on a fresh asyncio.run() loop,
  and find_target_device scans on yet another loop, so the bond state and
  client teardown end up spread across loops
- self.connected is set before GATT service discovery and notification
  subscription complete, so the interface reports connected before it can
  actually exchange data
- device_bonded only understands BlueZ device.details props, so every device
  looks unbonded on macOS (CoreBluetooth) and BLE never connects
- a transient scan error sets should_run=False, permanently killing the
  connection job
- device_disappeared is set even on a deliberate disconnect, which fails the
  next radio-state validation
- a missing bleak module calls RNS.panic() instead of raising, killing the
  whole process when panic containment is not installed yet
- close() spins forever waiting for connect_job_running

This module installs a fixed BLEConnection plus an RNodeInterface subclass
that resolves bt:// ports (classic Bluetooth via the OS serial-port bridge)
through bt_serial_ports. The built-in dispatch in RNS.Reticulum is patched
by replacing the module attributes before Reticulum construction.
"""

from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)

_PATCHED = False


def _is_android() -> bool:
    try:
        from meshchatx.src.backend.rnode_support import _is_chaquopy_android

        return _is_chaquopy_android()
    except Exception:
        return False


def _resolve_bt_port_value(port) -> str | None:
    """Return the serial device for a bt:// port value, or None.

    Returns None when *port* is not a bt:// target. Raises IOError when it is
    a bt:// target that cannot be resolved right now.
    """
    port_str = str(port or "").strip()
    if not port_str.lower().startswith("bt://"):
        return None
    from meshchatx.src.backend.bt_serial_ports import resolve_bt_target

    target = port_str[len("bt://") :].strip()
    resolved = resolve_bt_target(target)
    logger.info(
        "Resolved RNode bt://%s target to serial port %s",
        target or "<auto>",
        resolved,
    )
    return resolved


_ORIGINAL_RNODE_CLASS = None


def _make_rnode_subclass():
    """Build the RNodeInterface subclass used for dispatch.

    RNS's RNodeInterface references itself through its module global (e.g.
    RNodeInterface.RECONNECT_WAIT inside methods), so replacing the module
    attribute with a plain factory would break those lookups. A subclass
    keeps every inherited attribute reachable through the same name.
    """
    from RNS.Interfaces.RNodeInterface import RNodeInterface

    class MeshChatRNodeInterface(RNodeInterface):
        def open_port(self):
            # Resolve bt:// lazily on every open attempt so a device paired
            # after startup is picked up by the existing reconnect loop
            # instead of permanently disabling the interface.
            resolved = _resolve_bt_port_value(self.port)
            if resolved is not None:
                self.port = resolved
            super().open_port()

    return MeshChatRNodeInterface


class MeshChatBLEConnection:
    """BLE transport used by RNodeInterface for ble:// ports.

    Mirrors RNS 1.5.4's BLEConnection with the fixes listed in the module
    docstring. One asyncio loop is created on the connection thread and reused
    for scanning, connecting and cleanup.
    """

    UART_SERVICE_UUID = "6E400001-B5A3-F393-E0A9-E50E24DCCA9E"
    UART_RX_CHAR_UUID = "6E400002-B5A3-F393-E0A9-E50E24DCCA9E"
    UART_TX_CHAR_UUID = "6E400003-B5A3-F393-E0A9-E50E24DCCA9E"
    bleak = None
    asyncio = None

    SCAN_TIMEOUT = 2.0
    CONNECT_TIMEOUT = 5.0
    CLOSE_WAIT_TIMEOUT = 5.0

    @property
    def is_open(self):
        return self.connected

    @property
    def in_waiting(self):
        return len(self.owner.ble_rx_queue) > 0

    def write(self, data_bytes):
        with self.owner.ble_tx_lock:
            self.owner.ble_tx_queue += data_bytes
            return len(data_bytes)

    def read(self, n):
        with self.owner.ble_rx_lock:
            data = self.owner.ble_rx_queue[:n]
            self.owner.ble_rx_queue = self.owner.ble_rx_queue[n:]
            return data

    def close(self):
        if self.connected and self.ble_device:
            import RNS

            RNS.log(f"Disconnecting BLE device from {self.owner}", RNS.LOG_DEBUG)
            self.must_disconnect = True

            deadline = time.time() + self.CLOSE_WAIT_TIMEOUT
            while self.connect_job_running and time.time() < deadline:
                time.sleep(0.1)

    def __init__(self, owner=None, target_name=None, target_bt_addr=None):
        self.owner = owner
        self.target_name = target_name
        self.target_bt_addr = target_bt_addr
        self.scan_timeout = MeshChatBLEConnection.SCAN_TIMEOUT
        self.ble_device = None
        self.last_client = None
        self.connected = False
        self.running = False
        self.should_run = False
        self.must_disconnect = False
        self.connect_job_running = False
        self.device_disappeared = False
        self.loop = None
        self._windows_paired_addrs = None

        if MeshChatBLEConnection.bleak is None:
            import importlib.util

            if importlib.util.find_spec("bleak") is not None:
                import asyncio

                import bleak

                MeshChatBLEConnection.bleak = bleak
                MeshChatBLEConnection.asyncio = asyncio
            else:
                raise OSError(
                    'RNode over BLE requires the "bleak" module. Install it '
                    "with: python3 -m pip install bleak"
                )

        self.should_run = True
        self.connection_thread = threading.Thread(
            target=self.connection_job, daemon=True
        )
        self.connection_thread.start()

    def cleanup(self):
        self.should_run = False
        try:
            if self.last_client is not None:
                coro = self.last_client.disconnect()
                if self.loop is not None and not self.loop.is_closed():
                    self.loop.run_until_complete(coro)
                else:
                    self.asyncio.run(coro)
        except Exception as e:
            import RNS

            RNS.log(
                f"Error while disconnecting BLE device on cleanup for "
                f"{self.owner}: {e}",
                RNS.LOG_ERROR,
            )

    def connection_job(self):
        self.running = True
        try:
            self.loop = self.asyncio.new_event_loop()
            self.asyncio.set_event_loop(self.loop)
            while self.should_run:
                if self.ble_device is None:
                    self.ble_device = self.find_target_device()

                if self.ble_device is not None and not self.connected:
                    self.connect_device()

                time.sleep(1)
        except Exception as e:
            import RNS

            RNS.log(
                f"BLE connection job for {self.owner} failed: {e}",
                RNS.LOG_ERROR,
            )
        finally:
            try:
                if self.loop is not None and not self.loop.is_closed():
                    self.loop.close()
            except Exception:
                pass
            self.loop = None
            self.cleanup()
            self.running = False
            import RNS

            RNS.log(f"BLE connection job for {self.owner} ended", RNS.LOG_DEBUG)

    def connect_device(self):
        if self.ble_device is None:
            return
        import RNS

        RNS.log(
            f"Connecting BLE device {self.ble_device} for {self.owner}...",
            RNS.LOG_DEBUG,
        )

        device = self.ble_device
        if device is None:
            return

        async def connect_job() -> None:
            self.connect_job_running = True
            async with self.bleak.BleakClient(
                device,
                disconnected_callback=self.device_disconnected,
            ) as ble_client:

                def handle_rx(_device, data):
                    if self.owner is not None:
                        self.owner.ble_receive(data)

                self.ble_device = ble_client
                self.last_client = ble_client
                self.owner.port = str(f"ble://{ble_client.address}")

                uart_service = ble_client.services.get_service(
                    MeshChatBLEConnection.UART_SERVICE_UUID
                )
                if uart_service is None:
                    raise OSError("BLE device has no RNode UART service")
                rx_characteristic = uart_service.get_characteristic(
                    MeshChatBLEConnection.UART_RX_CHAR_UUID
                )
                if rx_characteristic is None:
                    raise OSError("BLE device has no RNode UART RX characteristic")
                await ble_client.start_notify(
                    MeshChatBLEConnection.UART_TX_CHAR_UUID, handle_rx
                )

                # Only report connected after services are discovered and
                # notifications are subscribed, otherwise the interface
                # writes into a half-open channel.
                self.connected = True
                self.device_disappeared = False

                while self.connected:
                    if self.owner is not None and self.owner.ble_waiting():
                        outbound_data = self.owner.get_ble_waiting(
                            rx_characteristic.max_write_without_response_size
                        )
                        await ble_client.write_gatt_char(
                            rx_characteristic, outbound_data, response=False
                        )
                    elif self.must_disconnect:
                        await ble_client.disconnect()
                    else:
                        await self.asyncio.sleep(0.1)

        try:
            self.loop.run_until_complete(connect_job())
        except Exception as e:
            RNS.log(
                f"Could not connect BLE device {self.ble_device} for {self.owner}: {e}",
                RNS.LOG_ERROR,
            )
            self.ble_device = None

        self.connect_job_running = False

    def device_disconnected(self, device):
        import RNS

        RNS.log(f"BLE device for {self.owner} disconnected", RNS.LOG_NOTICE)
        self.connected = False
        self.ble_device = None
        if not self.must_disconnect:
            self.device_disappeared = True

    def find_target_device(self):
        import RNS

        RNS.log(
            f"Searching for attachable BLE device for {self.owner}...",
            RNS.LOG_EXTREME,
        )
        if RNS.vendor.platformutils.is_windows():
            try:
                self._windows_paired_addrs = self._get_windows_paired_ble_addresses()
            except Exception as e:
                RNS.log(
                    f"Could not query paired Windows BLE devices: {e}",
                    RNS.LOG_ERROR,
                )
                self._windows_paired_addrs = None

        target_addr = self.target_bt_addr.lower() if self.target_bt_addr else None

        def device_filter(device, adv):
            service_uuids = getattr(adv, "service_uuids", None) or []
            if MeshChatBLEConnection.UART_SERVICE_UUID.lower() in service_uuids:
                if self.device_bonded(device):
                    if target_addr is None and self.target_name is None:
                        if device.name and device.name.startswith("RNode "):
                            return True

                    device_addr = device.address.lower() if device.address else None
                    if target_addr is None or device_addr == target_addr:
                        if self.target_name is None or (
                            device.name is not None and device.name == self.target_name
                        ):
                            return True
                else:
                    device_addr = device.address.lower() if device.address else None
                    if target_addr is not None and device_addr == target_addr:
                        RNS.log(
                            f"Can't connect to target device "
                            f"{self.target_bt_addr} over BLE, device is "
                            f"not bonded",
                            RNS.LOG_ERROR,
                        )
                    elif (
                        self.target_name is not None and device.name == self.target_name
                    ):
                        RNS.log(
                            f"Can't connect to target device "
                            f"{self.target_name} over BLE, device is "
                            f"not bonded",
                            RNS.LOG_ERROR,
                        )

            return False

        device = None
        try:
            device = self.loop.run_until_complete(
                self.bleak.BleakScanner.find_device_by_filter(
                    device_filter, timeout=self.scan_timeout
                )
            )
        except Exception as e:
            # A transient scan error (adapter busy, powering on, permission
            # prompt pending) must not kill the connection job. Retry on the
            # next pass instead.
            RNS.log(
                f"Error while finding BLE device for {self.owner}: {e}",
                RNS.LOG_ERROR,
            )

        return device

    def device_bonded(self, device):
        try:
            if self._windows_paired_addrs is not None:
                return (
                    device.address is not None
                    and device.address.lower() in self._windows_paired_addrs
                )

            details = getattr(device, "details", None)
            if isinstance(details, dict):
                props = details.get("props")
                if isinstance(props, dict) and "Bonded" in props:
                    return props["Bonded"] is True

            # CoreBluetooth (macOS) and other backends without a dict of
            # BlueZ props expose no pre-connection bond indicator. Pairing is
            # negotiated in-band during connect.
            return True

        except Exception as e:
            import RNS

            RNS.log(
                f"Error while determining device bond status for {device}, "
                f"the contained exception was: {e}",
                RNS.LOG_ERROR,
            )
            return False

    def _get_windows_paired_ble_addresses(self):
        from winrt.windows.devices.bluetooth import (  # type: ignore[import-not-found]
            BluetoothLEDevice,
        )
        from winrt.windows.devices.enumeration import (  # type: ignore[import-not-found]
            DeviceInformation,
        )

        async def _query():
            selector = BluetoothLEDevice.get_device_selector_from_pairing_state(True)
            infos = await DeviceInformation.find_all_async_aqs_filter(selector)
            return {info.id.split("-")[-1].lower() for info in infos}

        return self.loop.run_until_complete(_query())


def install_rns_rnode_patches() -> bool:
    """Patch RNS's RNodeInterface module with the fixed transports.

    Replaces the BLEConnection used for ble:// ports and wraps the interface
    class so bt:// ports resolve through bt_serial_ports. No-op on Android,
    where RNS dispatches its Android-specific RNodeInterface instead.
    Idempotent. Returns True when the patch was applied.
    """
    global _PATCHED, _ORIGINAL_RNODE_CLASS
    if _PATCHED:
        return True
    if _is_android():
        return False
    try:
        from RNS.Interfaces import RNodeInterface as rnode_module
    except ImportError:
        return False

    _ORIGINAL_RNODE_CLASS = rnode_module.RNodeInterface
    rnode_module.BLEConnection = MeshChatBLEConnection
    rnode_module.RNodeInterface = _make_rnode_subclass()
    _PATCHED = True
    logger.info("Installed MeshChatX RNode interface patches (BLE + bt://)")
    return True
