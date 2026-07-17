# SPDX-License-Identifier: MIT
"""USB module for Android (Chaquopy / MeshChatX).

Based on usb4a 0.3.0 by Quan Lin. Context comes from MeshChatX instead of
Kivy org.kivy.android.PythonActivity.
"""

from __future__ import annotations

from jnius import autoclass

Context = autoclass("android.content.Context")
Intent = autoclass("android.content.Intent")
PendingIntent = autoclass("android.app.PendingIntent")
UsbConstants = autoclass("android.hardware.usb.UsbConstants")
UsbRequest = autoclass("android.hardware.usb.UsbRequest")
ByteBuffer = autoclass("java.nio.ByteBuffer")

USB_RECIPIENT_DEVICE = 0x00
USB_RECIPIENT_INTERFACE = 0x01
USB_RECIPIENT_ENDPOINT = 0x02
USB_RECIPIENT_OTHER = 0x03

# Set by meshchat_wrapper from the Android Activity before RNS starts.
context = None


class USBError(IOError):
    """USB Error class."""


def set_context(android_context) -> None:
    """Install the Android Context used for UsbManager lookups."""
    global context
    context = android_context


def get_context():
    """Return the injected Activity / Context."""
    if context is None:
        raise RuntimeError(
            "USB context is not set. MeshChatX must pass the Activity into "
            "meshchat_wrapper.start_server before opening RNode USB ports.",
        )
    return context


def get_usb_manager():
    """Get USB manager object from the system."""
    return get_context().getSystemService("usb")


def _device_list_values(usb_manager):
    device_map = usb_manager.getDeviceList()
    values = device_map.values()
    try:
        return list(values.toArray())
    except Exception:
        try:
            return list(values)
        except Exception:
            result = []
            iterator = values.iterator()
            while iterator.hasNext():
                result.append(iterator.next())
            return result


def get_usb_device_list():
    """Get USB device list."""
    return _device_list_values(get_usb_manager())


def get_usb_device(device_name):
    """Get a USB device object by device name path."""
    for usb_device in get_usb_device_list():
        if usb_device and str(usb_device.getDeviceName()) == str(device_name):
            return usb_device
    return None


def has_usb_permission(usb_device):
    """True when permission is granted for the given USB device."""
    return bool(get_usb_manager().hasPermission(usb_device))


def request_usb_permission(usb_device):
    """Request permission for the given USB device."""
    usb_manager = get_usb_manager()
    action = "com.meshchatx.USB_PERMISSION"
    intent = Intent(action)
    try:
        pintent = PendingIntent.getBroadcast(get_context(), 0, intent, 0)
    except Exception:
        pintent = PendingIntent.getBroadcast(
            get_context(),
            0,
            intent,
            PendingIntent.FLAG_IMMUTABLE,
        )
    usb_manager.requestPermission(usb_device, pintent)


def build_usb_control_request_type(direction, usb_type, recipient):
    """Build USB control request type for USB communication."""
    return direction | usb_type | recipient


def arraycopy(source, sourcepos, dest, destpos, numelem):
    """Python version of System.arraycopy() in Java."""
    dest[destpos : destpos + numelem] = source[sourcepos : sourcepos + numelem]
