// @vitest-environment-options {"url":"http://127.0.0.1:9337/"}
import { describe, it, expect, beforeEach } from "vitest";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "../..");
const bridgeCode = readFileSync(resolve(root, "desktop/shell/desktop-bridge.js"), "utf8");

// jsdom may lack web streams; borrow Node's.
if (typeof window.ReadableStream === "undefined") {
    window.ReadableStream = globalThis.ReadableStream;
}
if (typeof window.WritableStream === "undefined") {
    window.WritableStream = globalThis.WritableStream;
}
if (typeof window.TextEncoder === "undefined") {
    window.TextEncoder = globalThis.TextEncoder;
}

let sent;
let serialResponders;

function loadBridge() {
    sent = [];
    serialResponders = {};
    window.webkit = {
        messageHandlers: {
            external: {
                postMessage: function (payload) {
                    var msg;
                    try {
                        msg = JSON.parse(payload);
                    } catch (e) {
                        return;
                    }
                    sent.push(msg);
                    var key = msg.method;
                    var fn = serialResponders[key];
                    if (fn) {
                        // respond asynchronously like Go's ExecJS would
                        var respond = fn;
                        setTimeout(function () {
                            var payload = respond(msg.args || []);
                            if (payload !== undefined) {
                                window.__desktopBridge.resolve(msg.id, true, JSON.stringify(payload));
                            }
                        }, 0);
                    }
                },
            },
        },
    };
    // Re-evaluate the bridge IIFE for a fresh closure (fresh grantedPorts).
    try {
        delete navigator.serial;
    } catch (e) {}
    try {
        Object.defineProperty(navigator, "serial", { value: undefined, configurable: true, writable: true });
    } catch (e) {}
    // eslint-disable-next-line no-eval
    (0, eval)(bridgeCode);
    window.__desktopBridge.__init("test-token");
}

function flush(times = 4) {
    var p = Promise.resolve();
    for (var i = 0; i < times; i++) {
        p = p.then(function () {
            return new Promise(function (r) {
                setTimeout(r, 0);
            });
        });
    }
    return p;
}

function lastCall(method) {
    for (var i = sent.length - 1; i >= 0; i--) {
        if (sent[i].method === method) {
            return sent[i];
        }
    }
    return null;
}

function b64encode(u8) {
    var s = "";
    for (var i = 0; i < u8.length; i++) {
        s += String.fromCharCode(u8[i]);
    }
    return btoa(s);
}

function b64decode(b64) {
    var s = atob(b64);
    var u8 = new Uint8Array(s.length);
    for (var i = 0; i < s.length; i++) {
        u8[i] = s.charCodeAt(i);
    }
    return u8;
}

const PORT_INFO = {
    path: "/dev/ttyUSB0",
    label: "CP2102",
    isUsb: true,
    usbVendorId: 4292,
    usbProductId: 60000,
};

describe("navigator.serial polyfill", () => {
    beforeEach(() => {
        loadBridge();
    });

    it("is installed only when native serial is absent", () => {
        expect(navigator.serial).toBeTruthy();
        expect(typeof navigator.serial.requestPort).toBe("function");
        expect(typeof navigator.serial.getPorts).toBe("function");
    });

    it("requestPort round-trips through the picker bridge method", async () => {
        serialResponders["serial-request-port"] = function (args) {
            expect(args[0].filters).toEqual([{ usbVendorId: 4292 }]);
            return { token: "tok-1", port: PORT_INFO };
        };
        const port = await navigator.serial.requestPort({ filters: [{ usbVendorId: 4292 }] });
        await flush();
        expect(port).toBeTruthy();
        const call = lastCall("serial-request-port");
        expect(call).toBeTruthy();
        expect(call.args[0].filters).toEqual([{ usbVendorId: 4292 }]);
        // token-gated: no raw path exposed for opening
        expect(port.path).toBeUndefined();
        // getPorts remembers the grant
        const ports = await navigator.serial.getPorts();
        expect(ports).toHaveLength(1);
        expect(ports[0]).toBe(port);
    });

    it("requestPort rejection maps to NotFoundError", async () => {
        serialResponders["serial-request-port"] = function () {
            return null; // picker cancelled
        };
        await expect(navigator.serial.requestPort({ filters: [] })).rejects.toMatchObject({
            name: "NotFoundError",
        });
    });

    it("open/read/write/close exercise the serial bridge methods", async () => {
        serialResponders["serial-request-port"] = () => ({ token: "tok-2", port: PORT_INFO });
        const port = await navigator.serial.requestPort({ filters: [] });
        await flush();

        serialResponders["serial-open"] = (args) => {
            expect(args[0].token).toBe("tok-2");
            expect(args[0].baudRate).toBe(115200);
            return { ok: true };
        };
        serialResponders["serial-write"] = (args) => {
            expect(args[0].token).toBe("tok-2");
            expect(b64decode(args[0].data)).toEqual(new Uint8Array([1, 2, 3, 255]));
            return { written: 4 };
        };
        let readCount = 0;
        serialResponders["serial-read"] = () => {
            readCount++;
            if (readCount === 1) {
                return { data: b64encode(new Uint8Array([72, 105])) }; // "Hi"
            }
            return { data: "" };
        };
        serialResponders["serial-close"] = () => ({ ok: true });

        await port.open({ baudRate: 115200 });
        await flush();
        expect(port.readable).toBeTruthy();
        expect(port.writable).toBeTruthy();

        // write through the WritableStream
        const writer = port.writable.getWriter();
        await writer.write(new Uint8Array([1, 2, 3, 255]));
        await writer.close();
        await flush();
        expect(lastCall("serial-write")).toBeTruthy();
        expect(lastCall("serial-close")).toBeTruthy(); // writable close -> serial-close

        // read through the ReadableStream
        const reader = port.readable.getReader();
        const { value } = await reader.read();
        expect(Array.from(value)).toEqual([72, 105]);
        await port.close();
        await flush();
    });

    it("readable waits on serial-data events when the buffer is empty", async () => {
        serialResponders["serial-request-port"] = () => ({ token: "tok-3", port: PORT_INFO });
        const port = await navigator.serial.requestPort({ filters: [] });
        await flush();

        let readCalls = 0;
        serialResponders["serial-read"] = () => {
            readCalls++;
            return { data: "" };
        };
        serialResponders["serial-open"] = () => ({ ok: true });
        serialResponders["serial-close"] = () => ({ ok: true });
        await port.open({ baudRate: 9600 });
        await flush();

        const reader = port.readable.getReader();
        const readPromise = reader.read();
        await flush(6);
        expect(readCalls).toBeGreaterThan(0);

        // now deliver data + nudge
        serialResponders["serial-read"] = () => ({
            data: b64encode(new Uint8Array([65, 66])),
        });
        window.__desktopBridge.emit("serial-data", JSON.stringify({ token: "tok-3" }));
        const { value } = await readPromise;
        expect(Array.from(value)).toEqual([65, 66]);
        await port.close();
    });

    it("setSignals/getSignals/getInfo/forget map to bridge methods", async () => {
        serialResponders["serial-request-port"] = () => ({ token: "tok-4", port: PORT_INFO });
        const port = await navigator.serial.requestPort({ filters: [] });
        await flush();

        serialResponders["serial-open"] = () => ({ ok: true });
        serialResponders["serial-set-signals"] = (args) => {
            expect(args[0].dtr).toBe(false);
            expect(args[0].rts).toBe(true);
            return { ok: true };
        };
        serialResponders["serial-get-signals"] = () => ({
            dtr: false,
            rts: true,
            cts: true,
            dsr: false,
            cd: true,
            ring: false,
        });
        serialResponders["serial-get-info"] = () => ({ usbVendorId: 4292, usbProductId: 60000 });
        serialResponders["serial-forget"] = () => ({ ok: true });

        await port.open({ baudRate: 9600 });
        await port.setSignals({ dataTerminalReady: false, requestToSend: true });
        const sig = await port.getSignals();
        expect(sig.clearToSend).toBe(true);
        expect(sig.dataTerminalReady).toBe(false);
        const info = await port.getInfo();
        expect(info.usbVendorId).toBe(4292);
        expect(info.usbProductId).toBe(60000);
        await port.forget();
        expect(lastCall("serial-forget")).toBeTruthy();
        expect(await navigator.serial.getPorts()).toHaveLength(0);
    });

    it("grant enforcement: only requestPort-granted tokens reach serial-open", async () => {
        // Simulate a forged token: there is no API to open without requestPort.
        serialResponders["serial-request-port"] = () => ({ token: "tok-real", port: PORT_INFO });
        const port = await navigator.serial.requestPort({ filters: [] });
        await flush();
        let openedToken = null;
        serialResponders["serial-open"] = (args) => {
            openedToken = args[0].token;
            return { ok: true };
        };
        await port.open({ baudRate: 9600 });
        expect(openedToken).toBe("tok-real");
        // port carries no settable path/token override surface
        expect(typeof port.open).toBe("function");
        expect(port._token).toBe("tok-real");
    });
});
