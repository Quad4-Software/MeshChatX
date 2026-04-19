import Transport from "./Transport.js";

/**
 * Bluetooth LE transport for RNode using the Nordic UART Service (NUS).
 *
 * RNode firmware exposes a serial-over-BLE channel using the standard NUS
 * UUIDs (https://infocenter.nordicsemi.com/topic/sdk_nrf5_v17.0.2/ble_sdk_app_nus_eval.html).
 * The transport adapts that GATT contract to the Web Serial-style readable/
 * writable streams expected by RNode.js.
 *
 * Notes:
 *  - BLE is suitable for management commands, EEPROM operations, TNC
 *    configuration and bluetooth control. It is NOT usable for ESP32 or
 *    nRF52 bootloader flashing because those bootloaders speak UART only.
 *  - Web Bluetooth requires a secure context (https or localhost).
 *  - The MTU is small (~20 bytes by default), so writes are chunked.
 */

export const NUS_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e";
export const NUS_RX_CHARACTERISTIC_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e";
export const NUS_TX_CHARACTERISTIC_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e";

const DEFAULT_WRITE_CHUNK_SIZE = 20;

export default class BluetoothTransport extends Transport {
    /**
     * @param {BluetoothDevice} device
     * @param {{ writeChunkSize?: number, env?: object }} [options]
     */
    constructor(device, options = {}) {
        super("bluetooth");
        if (!device) {
            throw new Error("BluetoothTransport requires a BluetoothDevice");
        }
        this.device = device;
        this.writeChunkSize = options.writeChunkSize || DEFAULT_WRITE_CHUNK_SIZE;
        this.env = options.env || (typeof window !== "undefined" ? window : globalThis);
        this.gattServer = null;
        this.rxCharacteristic = null;
        this.txCharacteristic = null;
        this._notifyHandler = null;
        this._readableController = null;
        this._disconnectedHandler = null;
    }

    /**
     * Trigger a chooser dialog for a NUS-capable RNode.
     * Returns a connected BluetoothTransport (with .open() still required to
     * attach streams).
     */
    static async request(options = {}) {
        const env = options.env || (typeof window !== "undefined" ? window : globalThis);
        if (!env.navigator?.bluetooth) {
            const err = new Error("web_bluetooth_unavailable");
            err.code = "WEB_BLUETOOTH_UNAVAILABLE";
            throw err;
        }
        let device;
        try {
            device = await env.navigator.bluetooth.requestDevice({
                filters: options.filters || [{ services: [NUS_SERVICE_UUID] }],
                optionalServices: [NUS_SERVICE_UUID, ...(options.optionalServices || [])],
            });
        } catch (cause) {
            const message = cause?.message || String(cause);
            if (cause?.name === "NotFoundError" || /User cancelled/i.test(message)) {
                const err = new Error("no_device_selected");
                err.code = "NO_DEVICE_SELECTED";
                err.cause = cause;
                throw err;
            }
            const err = new Error(message);
            err.code = "DEVICE_REQUEST_FAILED";
            err.cause = cause;
            throw err;
        }
        return new BluetoothTransport(device, { env });
    }

    async open(_opts = {}) {
        if (!this.device.gatt) {
            const err = new Error("bluetooth_gatt_unavailable");
            err.code = "GATT_UNAVAILABLE";
            throw err;
        }

        this.gattServer = await this.device.gatt.connect();

        let service;
        try {
            service = await this.gattServer.getPrimaryService(NUS_SERVICE_UUID);
        } catch (cause) {
            const err = new Error("nus_service_not_found");
            err.code = "NUS_SERVICE_NOT_FOUND";
            err.cause = cause;
            await this._safeDisconnect();
            throw err;
        }

        try {
            this.rxCharacteristic = await service.getCharacteristic(NUS_RX_CHARACTERISTIC_UUID);
            this.txCharacteristic = await service.getCharacteristic(NUS_TX_CHARACTERISTIC_UUID);
        } catch (cause) {
            const err = new Error("nus_characteristics_missing");
            err.code = "NUS_CHARACTERISTICS_MISSING";
            err.cause = cause;
            await this._safeDisconnect();
            throw err;
        }

        await this.txCharacteristic.startNotifications();

        this._notifyHandler = (event) => {
            const target = event.target;
            const value = target?.value;
            if (!value) {
                return;
            }
            const bytes = new Uint8Array(value.buffer, value.byteOffset, value.byteLength).slice();
            if (this._readableController) {
                try {
                    this._readableController.enqueue(bytes);
                } catch {
                    // controller already closed
                }
            }
        };
        this.txCharacteristic.addEventListener("characteristicvaluechanged", this._notifyHandler);

        this._disconnectedHandler = () => {
            if (this._readableController) {
                try {
                    this._readableController.close();
                } catch {
                    // ignore
                }
            }
        };
        this.device.addEventListener("gattserverdisconnected", this._disconnectedHandler);

        const transport = this;
        this.readable = new ReadableStream({
            start(controller) {
                transport._readableController = controller;
            },
            cancel() {
                transport._readableController = null;
            },
        });

        const chunkSize = this.writeChunkSize;
        const writeChar = this.rxCharacteristic;
        this.writable = new WritableStream({
            async write(chunk) {
                const bytes = chunk instanceof Uint8Array ? chunk : new Uint8Array(chunk);
                let offset = 0;
                while (offset < bytes.byteLength) {
                    const slice = bytes.subarray(offset, offset + chunkSize);
                    if (typeof writeChar.writeValueWithoutResponse === "function") {
                        await writeChar.writeValueWithoutResponse(slice);
                    } else {
                        await writeChar.writeValue(slice);
                    }
                    offset += chunkSize;
                }
            },
        });
    }

    async close() {
        if (this.txCharacteristic && this._notifyHandler) {
            try {
                this.txCharacteristic.removeEventListener("characteristicvaluechanged", this._notifyHandler);
            } catch {
                // ignore
            }
            try {
                await this.txCharacteristic.stopNotifications();
            } catch {
                // ignore
            }
        }
        if (this.device && this._disconnectedHandler) {
            try {
                this.device.removeEventListener("gattserverdisconnected", this._disconnectedHandler);
            } catch {
                // ignore
            }
        }
        await this._safeDisconnect();
        this.readable = null;
        this.writable = null;
        this.rxCharacteristic = null;
        this.txCharacteristic = null;
        this._notifyHandler = null;
        this._disconnectedHandler = null;
        this._readableController = null;
    }

    async _safeDisconnect() {
        try {
            if (this.gattServer && this.gattServer.connected) {
                this.gattServer.disconnect();
            }
        } catch {
            // ignore
        }
        this.gattServer = null;
    }

    canManageDevice() {
        return true;
    }

    description() {
        return "bluetooth-le";
    }
}
