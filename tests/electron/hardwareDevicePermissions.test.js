import { describe, expect, it, vi } from "vitest";
import { EventEmitter } from "node:events";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const {
    serialPortLabel,
    usbDeviceLabel,
    bluetoothDeviceLabel,
    choiceIndex,
    selectedSerialPortId,
    selectedUsbDevice,
    selectedBluetoothDeviceId,
    SESSION_PERMISSIONS,
    attachHardwareDevicePermissionHandlers,
} = require("../../electron/hardwareDevicePermissions.js");

describe("electron/hardwareDevicePermissions", () => {
    it("labels serial ports with display name and path", () => {
        expect(
            serialPortLabel({
                displayName: "RNode",
                portName: "/dev/ttyACM0",
                portId: "1",
            })
        ).toBe("RNode (/dev/ttyACM0)");
        expect(serialPortLabel({ portName: "/dev/ttyUSB0" })).toBe("/dev/ttyUSB0");
        expect(serialPortLabel({})).toBe("Serial device");
    });

    it("labels usb and bluetooth devices", () => {
        expect(usbDeviceLabel({ productName: "Heltec", vendorId: 0x10c4 })).toBe("Heltec (0x10c4)");
        expect(bluetoothDeviceLabel({ deviceName: "RNode BLE", deviceId: "aa" })).toBe("RNode BLE");
    });

    it("treats cancel and out-of-range buttons as no selection", () => {
        expect(choiceIndex(2, 2)).toBe(-1);
        expect(choiceIndex(-1, 2)).toBe(-1);
        expect(choiceIndex(0, 2)).toBe(0);
        const ports = [{ portId: "acm0" }, { portId: "usb0" }];
        expect(selectedSerialPortId(ports, 1)).toBe("usb0");
        expect(selectedSerialPortId(ports, 2)).toBe("");
        expect(selectedUsbDevice([{ productName: "x" }], 0)).toEqual({ productName: "x" });
        expect(selectedUsbDevice([{ productName: "x" }], 1)).toBeUndefined();
        expect(selectedBluetoothDeviceId([{ deviceId: "aa" }], 1)).toBe("");
    });

    it("grants serial usb and bluetooth session permissions", () => {
        expect(SESSION_PERMISSIONS.has("serial")).toBe(true);
        expect(SESSION_PERMISSIONS.has("usb")).toBe(true);
        expect(SESSION_PERMISSIONS.has("bluetooth")).toBe(true);
        expect(SESSION_PERMISSIONS.has("media")).toBe(true);
    });

    it("permission handlers only grant the local backend origin", () => {
        const ses = new EventEmitter();
        let checkHandler = null;
        let requestHandler = null;
        ses.setPermissionCheckHandler = (fn) => {
            checkHandler = fn;
        };
        ses.setPermissionRequestHandler = (fn) => {
            requestHandler = fn;
        };
        attachHardwareDevicePermissionHandlers(ses, {
            dialog: { showMessageBox: vi.fn() },
            getParentWindow: () => null,
        });

        expect(checkHandler(null, "serial", "http://127.0.0.1:9337")).toBe(true);
        expect(checkHandler(null, "media", "https://localhost:9337/")).toBe(true);
        expect(checkHandler(null, "geolocation", "http://127.0.0.1:9337")).toBe(false);
        expect(checkHandler(null, "serial", "https://evil.example")).toBe(false);
        expect(checkHandler(null, "serial", "")).toBe(false);
        expect(checkHandler(null, "serial", "http://127.0.0.1:9337@evil.example")).toBe(false);

        const callback = vi.fn();
        requestHandler(null, "media", callback, { requestingUrl: "https://evil.example" });
        expect(callback).toHaveBeenLastCalledWith(false);
        requestHandler(null, "media", callback, { requestingUrl: "http://localhost:9337/" });
        expect(callback).toHaveBeenLastCalledWith(true);
        requestHandler(null, "media", callback, { requestingUrl: "" });
        expect(callback).toHaveBeenLastCalledWith(false);
    });

    it("select-serial-port with an empty list callbacks empty immediately", () => {
        const ses = new EventEmitter();
        ses.setPermissionCheckHandler = vi.fn();
        ses.setPermissionRequestHandler = vi.fn();
        const callback = vi.fn();
        attachHardwareDevicePermissionHandlers(ses, {
            dialog: { showMessageBox: vi.fn() },
            getParentWindow: () => null,
        });
        const event = { preventDefault: vi.fn() };
        ses.emit("select-serial-port", event, [], {}, callback);
        expect(event.preventDefault).toHaveBeenCalledOnce();
        expect(callback).toHaveBeenCalledWith("");
    });

    it("select-serial-port maps dialog choice onto portId", async () => {
        const ses = new EventEmitter();
        ses.setPermissionCheckHandler = vi.fn();
        ses.setPermissionRequestHandler = vi.fn();
        const showMessageBox = vi.fn().mockResolvedValue({ response: 1 });
        attachHardwareDevicePermissionHandlers(ses, {
            dialog: { showMessageBox },
            getParentWindow: () => null,
        });
        const callback = vi.fn();
        const event = { preventDefault: vi.fn() };
        ses.emit(
            "select-serial-port",
            event,
            [
                { portId: "first", portName: "/dev/ttyACM0" },
                { portId: "second", portName: "/dev/ttyUSB0" },
            ],
            {},
            callback
        );
        await vi.waitFor(() => {
            expect(callback).toHaveBeenCalledWith("second");
        });
    });
});
