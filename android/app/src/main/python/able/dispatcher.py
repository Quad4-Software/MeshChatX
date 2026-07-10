# SPDX-License-Identifier: MIT
"""Chaquopy BluetoothDispatcher for RNS RNode BLE."""

from __future__ import annotations

from able.queue import BLEQueue, ble_task, ble_task_done
from able.structures import Services

GATT_SUCCESS = 0

_JAVA = None


def _java():
    global _JAVA
    if _JAVA is not None:
        return _JAVA
    from jnius import autoclass

    bluetooth_adapter = autoclass("android.bluetooth.BluetoothAdapter")
    bluetooth_device = autoclass("android.bluetooth.BluetoothDevice")
    bluetooth_gatt_descriptor = autoclass("android.bluetooth.BluetoothGattDescriptor")
    ble = autoclass("org.able.BLE")
    _JAVA = {
        "BluetoothAdapter": bluetooth_adapter,
        "BluetoothDevice": bluetooth_device,
        "BluetoothGattDescriptor": bluetooth_gatt_descriptor,
        "BLE": ble,
        "ENABLE_NOTIFICATION_VALUE": bluetooth_gatt_descriptor.ENABLE_NOTIFICATION_VALUE,
        "ENABLE_INDICATION_VALUE": bluetooth_gatt_descriptor.ENABLE_INDICATION_VALUE,
        "DISABLE_NOTIFICATION_VALUE": bluetooth_gatt_descriptor.DISABLE_NOTIFICATION_VALUE,
    }
    return _JAVA


def _to_java_bytes(value):
    if value is None:
        return []
    if isinstance(value, (bytes, bytearray)):
        return list(value)
    if isinstance(value, (list, tuple)):
        return list(value)
    try:
        return list(value.encode())
    except AttributeError:
        pass
    try:
        return list(value)
    except TypeError:
        return [value]


def _make_python_bluetooth_proxy(dispatcher):
    from java import dynamic_proxy, jclass

    interface = jclass("org.able.PythonBluetooth")

    class PythonBluetoothProxy(dynamic_proxy(interface)):
        def __init__(self, owner):
            super().__init__()
            self.owner = owner

        def on_error(self, msg):
            self.owner.dispatch("on_error", msg)

        def on_scan_started(self, success):
            self.owner.dispatch("on_scan_started", success)

        def on_scan_result(self, result):
            pass

        def on_scan_completed(self):
            self.owner.dispatch("on_scan_completed")

        def on_services(self, status, services):
            services_dict = Services()
            if status == GATT_SUCCESS and services is not None:
                try:
                    service_list = list(services.toArray())
                except Exception:
                    try:
                        service_list = list(services)
                    except Exception:
                        service_list = []
                for service in service_list:
                    service_uuid = str(service.getUuid().toString())
                    services_dict[service_uuid] = {}
                    try:
                        chars = list(service.getCharacteristics().toArray())
                    except Exception:
                        chars = list(service.getCharacteristics())
                    for characteristic in chars:
                        char_uuid = str(characteristic.getUuid().toString())
                        services_dict[service_uuid][char_uuid] = characteristic
            self.owner.dispatch("on_services", status, services_dict)

        def on_characteristic_changed(self, characteristic):
            self.owner.dispatch("on_characteristic_changed", characteristic)

        def on_characteristic_read(self, characteristic, status):
            self.owner.dispatch("on_gatt_release")
            self.owner.dispatch("on_characteristic_read", characteristic, status)

        def on_characteristic_write(self, characteristic, status):
            self.owner.dispatch("on_gatt_release")
            self.owner.dispatch("on_characteristic_write", characteristic, status)

        def on_descriptor_read(self, descriptor, status):
            self.owner.dispatch("on_gatt_release")
            self.owner.dispatch("on_descriptor_read", descriptor, status)

        def on_descriptor_write(self, descriptor, status):
            self.owner.dispatch("on_gatt_release")
            self.owner.dispatch("on_descriptor_write", descriptor, status)

        def on_connection_state_change(self, status, state):
            self.owner.dispatch("on_connection_state_change", status, state)

        def on_bluetooth_adapter_state_change(self, state):
            self.owner.dispatch("on_bluetooth_adapter_state_change", state)

        def on_rssi_updated(self, rssi, status):
            self.owner.dispatch("on_gatt_release")
            self.owner.dispatch("on_rssi_updated", rssi, status)

        def on_mtu_changed(self, mtu, status):
            self.owner.dispatch("on_gatt_release")
            self.owner.dispatch("on_mtu_changed", mtu, status)

    return PythonBluetoothProxy(dispatcher)


class BluetoothDispatcher:
    """Subset of able.BluetoothDispatcher used by RNS RNode BLEConnection."""

    def __init__(
        self, queue_timeout: float = 0.5, enable_ble_code: int = 0xAB1E, **_kwargs
    ):
        java = _java()
        self.queue_timeout = queue_timeout
        self.enable_ble_code = enable_ble_code
        self.queue = BLEQueue(timeout=queue_timeout)
        self._events_interface = _make_python_bluetooth_proxy(self)
        self._ble = java["BLE"](self._events_interface)

    def dispatch(self, event_name, *args):
        handler = getattr(self, event_name, None)
        if callable(handler):
            return handler(*args)
        return None

    @property
    def gatt(self):
        return self._ble.getGatt()

    @property
    def adapter(self):
        return _java()["BluetoothAdapter"].getDefaultAdapter()

    @property
    def bonded_devices(self):
        java = _java()
        adapter = self.adapter
        if adapter is None:
            return []
        ble_types = (
            java["BluetoothDevice"].DEVICE_TYPE_LE,
            java["BluetoothDevice"].DEVICE_TYPE_DUAL,
        )
        try:
            devices = list(adapter.getBondedDevices().toArray())
        except Exception:
            devices = list(adapter.getBondedDevices())
        return [dev for dev in devices if int(dev.getType()) in ble_types]

    def connect_by_device_address(self, address: str, autoconnect: bool = False):
        java = _java()
        address = str(address).upper()
        if not java["BluetoothAdapter"].checkBluetoothAddress(address):
            raise ValueError(f"{address} is not a valid Bluetooth address")
        adapter = self.adapter
        if adapter is None:
            raise OSError("Bluetooth adapter unavailable")
        device = adapter.getRemoteDevice(address)
        self.connect_gatt(device, autoconnect)

    def connect_gatt(self, device, autoconnect: bool = False):
        self._ble.connectGatt(device, autoconnect)

    def close_gatt(self):
        self._ble.closeGatt()

    def discover_services(self):
        gatt = self.gatt
        if gatt is None:
            return False
        return gatt.discoverServices()

    def enable_notifications(self, characteristic, enable=True, indication=False):
        java = _java()
        gatt = self.gatt
        if gatt is None:
            return False
        if not gatt.setCharacteristicNotification(characteristic, enable):
            return False
        if not enable:
            descriptor_value = java["DISABLE_NOTIFICATION_VALUE"]
        elif indication:
            descriptor_value = java["ENABLE_INDICATION_VALUE"]
        else:
            descriptor_value = java["ENABLE_NOTIFICATION_VALUE"]
        try:
            descriptors = list(characteristic.getDescriptors().toArray())
        except Exception:
            descriptors = list(characteristic.getDescriptors())
        for descriptor in descriptors:
            self.write_descriptor(descriptor, descriptor_value)
        return True

    @ble_task
    def write_descriptor(self, descriptor, value):
        payload = _to_java_bytes(value)
        if not descriptor.setValue(payload):
            return
        gatt = self.gatt
        if gatt is None:
            return
        gatt.writeDescriptor(descriptor)

    @ble_task
    def write_characteristic(self, characteristic, value, write_type=None):
        payload = _to_java_bytes(value)
        write_type_int = int(write_type or 0)
        self._ble.writeCharacteristic(characteristic, payload, write_type_int)

    @ble_task
    def request_mtu(self, mtu: int):
        gatt = self.gatt
        if gatt is None:
            return
        gatt.requestMtu(int(mtu))

    @ble_task_done
    def on_gatt_release(self):
        pass

    def on_error(self, msg):
        raise OSError(str(msg))

    def on_scan_started(self, success):
        pass

    def on_scan_completed(self):
        pass

    def on_device(self, device, rssi, advertisement):
        pass

    def on_connection_state_change(self, status, state):
        pass

    def on_bluetooth_adapter_state_change(self, state):
        pass

    def on_services(self, status, services):
        pass

    def on_characteristic_changed(self, characteristic):
        pass

    def on_characteristic_read(self, characteristic, status):
        pass

    def on_characteristic_write(self, characteristic, status):
        pass

    def on_descriptor_read(self, descriptor, status):
        pass

    def on_descriptor_write(self, descriptor, status):
        pass

    def on_rssi_updated(self, rssi, status):
        pass

    def on_mtu_changed(self, mtu, status):
        pass
