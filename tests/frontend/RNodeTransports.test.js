import { describe, it, expect, vi } from "vitest";
import SerialTransport from "@/js/rnode/transports/SerialTransport.js";
import BluetoothTransport, {
    NUS_SERVICE_UUID,
    NUS_RX_CHARACTERISTIC_UUID,
    NUS_TX_CHARACTERISTIC_UUID,
} from "@/js/rnode/transports/BluetoothTransport.js";
import WifiTransport from "@/js/rnode/transports/WifiTransport.js";

describe("SerialTransport.request", () => {
    it("throws WEB_SERIAL_UNAVAILABLE when navigator.serial is missing", async () => {
        const env = { navigator: {} };
        await expect(SerialTransport.request({ env })).rejects.toMatchObject({
            code: "WEB_SERIAL_UNAVAILABLE",
        });
    });

    it("translates NotFoundError to NO_PORT_SELECTED", async () => {
        const env = {
            navigator: {
                serial: {
                    requestPort: vi.fn().mockRejectedValue(
                        Object.assign(new Error("No port selected by the user."), { name: "NotFoundError" })
                    ),
                },
            },
        };
        await expect(SerialTransport.request({ env })).rejects.toMatchObject({
            code: "NO_PORT_SELECTED",
        });
    });

    it("returns a wrapped transport reporting capabilities", async () => {
        const fakePort = { open: vi.fn(), close: vi.fn(), readable: {}, writable: {} };
        const env = {
            navigator: { serial: { requestPort: vi.fn().mockResolvedValue(fakePort) } },
        };
        const transport = await SerialTransport.request({ env });
        expect(transport).toBeInstanceOf(SerialTransport);
        expect(transport.canFlashEsp32()).toBe(true);
        expect(transport.canFlashNrf52()).toBe(true);
        expect(transport.canManageDevice()).toBe(true);
        expect(transport.description()).toBe("serial");
    });

    it("flags polyfilled when navigator.serial is the polyfill module", async () => {
        const fakePort = { open: vi.fn() };
        const polyfill = { requestPort: vi.fn().mockResolvedValue(fakePort) };
        const env = {
            navigator: { serial: polyfill },
            serial: polyfill,
        };
        const transport = await SerialTransport.request({ env });
        expect(transport.polyfilled).toBe(true);
        expect(transport.description()).toBe("serial-polyfill");
    });

    it("forwards baudRate to underlying port.open", async () => {
        const fakePort = {
            open: vi.fn().mockResolvedValue(undefined),
            close: vi.fn().mockResolvedValue(undefined),
            readable: { _r: 1 },
            writable: { _w: 1 },
        };
        const transport = new SerialTransport(fakePort);
        await transport.open({ baudRate: 921600 });
        expect(fakePort.open).toHaveBeenCalledWith({ baudRate: 921600 });
        expect(transport.readable).toBe(fakePort.readable);
        expect(transport.writable).toBe(fakePort.writable);
    });
});

describe("BluetoothTransport.request", () => {
    it("throws WEB_BLUETOOTH_UNAVAILABLE when missing", async () => {
        await expect(BluetoothTransport.request({ env: { navigator: {} } })).rejects.toMatchObject({
            code: "WEB_BLUETOOTH_UNAVAILABLE",
        });
    });
    it("translates NotFoundError to NO_DEVICE_SELECTED", async () => {
        const env = {
            navigator: {
                bluetooth: {
                    requestDevice: vi
                        .fn()
                        .mockRejectedValue(Object.assign(new Error("User cancelled"), { name: "NotFoundError" })),
                },
            },
        };
        await expect(BluetoothTransport.request({ env })).rejects.toMatchObject({
            code: "NO_DEVICE_SELECTED",
        });
    });
    it("uses NUS UUID filters by default", async () => {
        const requestDevice = vi.fn().mockResolvedValue({});
        const env = { navigator: { bluetooth: { requestDevice } } };
        await BluetoothTransport.request({ env });
        const args = requestDevice.mock.calls[0][0];
        expect(args.filters).toEqual([{ services: [NUS_SERVICE_UUID] }]);
        expect(args.optionalServices).toContain(NUS_SERVICE_UUID);
    });
    it("exposes the standard NUS UUIDs", () => {
        expect(NUS_SERVICE_UUID).toBe("6e400001-b5a3-f393-e0a9-e50e24dcca9e");
        expect(NUS_RX_CHARACTERISTIC_UUID).toBe("6e400002-b5a3-f393-e0a9-e50e24dcca9e");
        expect(NUS_TX_CHARACTERISTIC_UUID).toBe("6e400003-b5a3-f393-e0a9-e50e24dcca9e");
    });
});

describe("WifiTransport", () => {
    it("validates IPv4 hosts", () => {
        expect(WifiTransport.isValidHost("192.168.1.50")).toBe(true);
        expect(WifiTransport.isValidHost("10.0.0.1")).toBe(true);
        expect(WifiTransport.isValidHost("not a host")).toBe(false);
        expect(WifiTransport.isValidHost("bad_host_with_underscore")).toBe(false);
        expect(WifiTransport.isValidHost("")).toBe(false);
        expect(WifiTransport.isValidHost(undefined)).toBe(false);
    });

    it("validates hostnames", () => {
        expect(WifiTransport.isValidHost("rnode.local")).toBe(true);
        expect(WifiTransport.isValidHost("rnode")).toBe(true);
    });

    it("throws INVALID_HOST when constructed with an invalid host", () => {
        expect(() => new WifiTransport("???")).toThrowError(/invalid_host/);
    });

    it("only supports OTA flashing", () => {
        const t = new WifiTransport("192.168.1.50");
        expect(t.canOtaFlash()).toBe(true);
        expect(t.canFlashEsp32()).toBe(false);
        expect(t.canManageDevice()).toBe(false);
        expect(t.description()).toBe("wifi://192.168.1.50");
    });

    it("upload posts firmware via XMLHttpRequest with progress", async () => {
        const xhrInstances = [];
        function FakeXhr() {
            xhrInstances.push(this);
            this.upload = {};
            this.open = vi.fn();
            this.send = vi.fn(() => {
                this.status = 200;
                this.responseText = "ok";
                this.upload.onprogress?.({ lengthComputable: true, loaded: 50, total: 100 });
                this.upload.onprogress?.({ lengthComputable: true, loaded: 100, total: 100 });
                this.onload?.();
            });
        }
        function FakeFormData() {
            this.entries = [];
            this.append = (k, v, n) => this.entries.push({ k, v, n });
        }
        const env = { XMLHttpRequest: FakeXhr, FormData: FakeFormData };
        const t = new WifiTransport("192.168.1.50", { env, timeoutMs: 1000 });
        const progress = vi.fn();
        const blob = { size: 100 };
        const result = await t.upload(blob, progress);
        expect(result.status).toBe(200);
        expect(progress).toHaveBeenCalledWith(50);
        expect(progress).toHaveBeenCalledWith(100);
        expect(xhrInstances[0].open).toHaveBeenCalledWith("POST", "http://192.168.1.50/update", true);
    });

    it("upload rejects with HTTP_ERROR on non-2xx", async () => {
        function FakeXhr() {
            this.upload = {};
            this.open = vi.fn();
            this.send = vi.fn(() => {
                this.status = 500;
                this.responseText = "boom";
                this.onload?.();
            });
        }
        function FakeFormData() {
            this.append = vi.fn();
        }
        const t = new WifiTransport("192.168.1.50", { env: { XMLHttpRequest: FakeXhr, FormData: FakeFormData } });
        await expect(t.upload({})).rejects.toMatchObject({ code: "HTTP_ERROR", status: 500 });
    });

    it("upload rejects with UPLOAD_TIMEOUT on ontimeout", async () => {
        function FakeXhr() {
            this.upload = {};
            this.open = vi.fn();
            this.send = vi.fn(() => this.ontimeout?.());
        }
        function FakeFormData() {
            this.append = vi.fn();
        }
        const t = new WifiTransport("192.168.1.50", { env: { XMLHttpRequest: FakeXhr, FormData: FakeFormData } });
        await expect(t.upload({})).rejects.toMatchObject({ code: "UPLOAD_TIMEOUT" });
    });
});
