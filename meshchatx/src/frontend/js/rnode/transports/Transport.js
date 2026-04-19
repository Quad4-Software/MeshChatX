/**
 * Abstract transport contract used by RNode flasher.
 *
 * Concrete transports (Web Serial, Web Bluetooth NUS, WiFi OTA, ...) expose
 * the same shape as a Web Serial port:
 *
 *  - readable: ReadableStream<Uint8Array>
 *  - writable: WritableStream<Uint8Array>
 *  - open(opts): Promise<void>
 *  - close(): Promise<void>
 *
 * This lets RNode.js and Nrf52DfuFlasher.js stay transport-agnostic.
 *
 * Concrete classes should also expose:
 *  - kind: short string identifier ("serial", "bluetooth", "wifi")
 *  - canFlashEsp32(): boolean
 *  - canFlashNrf52(): boolean
 *  - canManageDevice(): boolean
 *  - description(): short user-facing label
 */

export default class Transport {
    constructor(kind) {
        this.kind = kind;
        this.readable = null;
        this.writable = null;
    }

    async open() {
        throw new Error(`${this.kind} transport: open() not implemented`);
    }

    async close() {
        throw new Error(`${this.kind} transport: close() not implemented`);
    }

    canFlashEsp32() {
        return false;
    }

    canFlashNrf52() {
        return false;
    }

    canManageDevice() {
        return false;
    }

    canOtaFlash() {
        return false;
    }

    description() {
        return this.kind;
    }
}
