import Transport from "./Transport.js";

/**
 * Web Serial transport.
 *
 * Wraps an underlying SerialPort (either the native navigator.serial port or
 * the web-serial-polyfill port that bridges WebUSB devices). Most of the
 * real work is delegated to the wrapped port; the wrapper is mainly here so
 * the rest of the codebase has a single uniform API and so error reporting
 * surface area is centralised.
 */
export default class SerialTransport extends Transport {
    /**
     * @param {SerialPort} port wrapped serial port
     * @param {{ polyfilled?: boolean, env?: object }} [options]
     */
    constructor(port, options = {}) {
        super("serial");
        if (!port) {
            throw new Error("SerialTransport requires a SerialPort instance");
        }
        this.port = port;
        this.polyfilled = Boolean(options.polyfilled);
        this.env = options.env || (typeof window !== "undefined" ? window : globalThis);
        this.opened = false;
    }

    /**
     * Request a port from the user via navigator.serial.requestPort. Returns
     * a SerialTransport wrapper or throws a descriptive error.
     *
     * @param {{ filters?: Array, env?: object }} [options]
     */
    static async request(options = {}) {
        const env = options.env || (typeof window !== "undefined" ? window : globalThis);
        if (!env.navigator?.serial) {
            const err = new Error("web_serial_unavailable");
            err.code = "WEB_SERIAL_UNAVAILABLE";
            throw err;
        }
        let port;
        try {
            port = await env.navigator.serial.requestPort({
                filters: options.filters || [],
            });
        } catch (cause) {
            const message = cause?.message || String(cause);
            if (cause?.name === "NotFoundError" || /No port selected/i.test(message)) {
                const err = new Error("no_port_selected");
                err.code = "NO_PORT_SELECTED";
                err.cause = cause;
                throw err;
            }
            const err = new Error(message);
            err.code = "PORT_REQUEST_FAILED";
            err.cause = cause;
            throw err;
        }
        const polyfilled = Boolean(env.serial && env.navigator.serial === env.serial);
        return new SerialTransport(port, { polyfilled, env });
    }

    async open(opts = {}) {
        const baudRate = typeof opts.baudRate === "number" ? opts.baudRate : 115200;
        await this.port.open({ baudRate });
        this.readable = this.port.readable;
        this.writable = this.port.writable;
        this.opened = true;
    }

    async close() {
        this.opened = false;
        try {
            if (typeof this.port.close === "function") {
                await this.port.close();
            }
        } finally {
            this.readable = null;
            this.writable = null;
        }
    }

    async setSignals(signals) {
        if (typeof this.port.setSignals === "function") {
            await this.port.setSignals(signals);
        }
    }

    canFlashEsp32() {
        return true;
    }

    canFlashNrf52() {
        return true;
    }

    canManageDevice() {
        return true;
    }

    description() {
        return this.polyfilled ? "serial-polyfill" : "serial";
    }
}
