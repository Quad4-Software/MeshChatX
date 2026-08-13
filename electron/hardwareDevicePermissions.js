"use strict";

const HARDWARE_PERMISSIONS = new Set(["serial", "usb", "bluetooth", "hid"]);
const SESSION_PERMISSIONS = new Set([
    ...HARDWARE_PERMISSIONS,
    "media",
    "microphone",
    "camera",
    "notifications",
    "clipboard-sanitized-write",
    "clipboard-read",
    "fullscreen",
    "pointerLock",
]);

function serialPortLabel(port) {
    const displayName = port && port.displayName ? String(port.displayName) : "";
    const portName = port && port.portName ? String(port.portName) : "";
    if (displayName && portName && displayName !== portName) {
        return `${displayName} (${portName})`;
    }
    return displayName || portName || "Serial device";
}

function usbDeviceLabel(device) {
    const product = (device && (device.productName || device.productId)) || "USB device";
    if (device && device.vendorId != null) {
        return `${product} (0x${Number(device.vendorId).toString(16)})`;
    }
    return String(product);
}

function bluetoothDeviceLabel(device) {
    return (device && (device.deviceName || device.deviceId)) || "Bluetooth device";
}

function choiceIndex(buttonIndex, itemCount) {
    if (!Number.isInteger(buttonIndex) || buttonIndex < 0 || buttonIndex >= itemCount) {
        return -1;
    }
    return buttonIndex;
}

function selectedSerialPortId(portList, buttonIndex) {
    const idx = choiceIndex(buttonIndex, portList.length);
    if (idx < 0) {
        return "";
    }
    return portList[idx].portId || "";
}

function selectedUsbDevice(deviceList, buttonIndex) {
    const idx = choiceIndex(buttonIndex, deviceList.length);
    if (idx < 0) {
        return undefined;
    }
    return deviceList[idx];
}

function selectedBluetoothDeviceId(deviceList, buttonIndex) {
    const idx = choiceIndex(buttonIndex, deviceList.length);
    if (idx < 0) {
        return "";
    }
    return deviceList[idx].deviceId || "";
}

async function pickFromList(dialogApi, parentWindow, title, message, labels) {
    const buttons = labels.concat(["Cancel"]);
    const options = {
        type: "question",
        title,
        message,
        buttons,
        cancelId: buttons.length - 1,
        defaultId: 0,
        noLink: true,
    };
    const result = parentWindow
        ? await dialogApi.showMessageBox(parentWindow, options)
        : await dialogApi.showMessageBox(options);
    return choiceIndex(result.response, labels.length);
}

function attachHardwareDevicePermissionHandlers(ses, deps) {
    const dialogApi = deps.dialog;
    const getParentWindow = deps.getParentWindow;

    ses.setPermissionCheckHandler((_webContents, permission) => {
        return SESSION_PERMISSIONS.has(permission);
    });
    ses.setPermissionRequestHandler((_webContents, permission, callback) => {
        callback(SESSION_PERMISSIONS.has(permission));
    });

    ses.on("select-serial-port", (event, portList, _webContents, callback) => {
        event.preventDefault();
        const list = Array.isArray(portList) ? portList : [];
        if (list.length === 0) {
            callback("");
            return;
        }
        void pickFromList(
            dialogApi,
            getParentWindow(),
            "Select serial port",
            "Choose the RNode or serial adapter to use.",
            list.map(serialPortLabel)
        ).then((idx) => {
            callback(selectedSerialPortId(list, idx));
        });
    });

    ses.on("select-usb-device", (event, details, callback) => {
        event.preventDefault();
        const list = details && Array.isArray(details.deviceList) ? details.deviceList : [];
        if (list.length === 0) {
            callback();
            return;
        }
        void pickFromList(
            dialogApi,
            getParentWindow(),
            "Select USB device",
            "Choose the USB device to use.",
            list.map(usbDeviceLabel)
        ).then((idx) => {
            callback(selectedUsbDevice(list, idx));
        });
    });

    ses.on("select-bluetooth-device", (event, deviceList, callback) => {
        event.preventDefault();
        const list = Array.isArray(deviceList) ? deviceList : [];
        if (list.length === 0) {
            callback("");
            return;
        }
        void pickFromList(
            dialogApi,
            getParentWindow(),
            "Select Bluetooth device",
            "Choose the Bluetooth device to use.",
            list.map(bluetoothDeviceLabel)
        ).then((idx) => {
            callback(selectedBluetoothDeviceId(list, idx));
        });
    });
}

module.exports = {
    HARDWARE_PERMISSIONS,
    SESSION_PERMISSIONS,
    serialPortLabel,
    usbDeviceLabel,
    bluetoothDeviceLabel,
    choiceIndex,
    selectedSerialPortId,
    selectedUsbDevice,
    selectedBluetoothDeviceId,
    attachHardwareDevicePermissionHandlers,
};
