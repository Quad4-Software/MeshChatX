import Transport from "./Transport.js";

/**
 * WiFi/OTA transport for RNode firmware over the device HTTP update endpoint.
 *
 * Most RNode-derived ESP32 firmwares ship a small HTTP server that exposes
 * /update for in-place flashing of the main application image. This transport
 * does not provide a serial-style readable/writable pair; instead it exposes
 * upload(blob, onProgress) which performs an XMLHttpRequest multipart POST
 * with progress events and timeout handling.
 */

const DEFAULT_TIMEOUT_MS = 120000;

function isValidIpv4(trimmed) {
    const parts = trimmed.split(".");
    if (parts.length !== 4) {
        return false;
    }
    for (const part of parts) {
        if (part.length === 0 || part.length > 3) {
            return false;
        }
        for (let i = 0; i < part.length; i++) {
            const d = part.charCodeAt(i);
            if (d < 48 || d > 57) {
                return false;
            }
        }
        const n = Number(part);
        if (n !== Math.floor(n) || n < 0 || n > 255) {
            return false;
        }
    }
    return true;
}

function isValidHostname(trimmed) {
    if (trimmed.length > 253) {
        return false;
    }
    const labels = trimmed.split(".");
    for (const label of labels) {
        if (label.length < 1 || label.length > 63) {
            return false;
        }
        if (label.startsWith("-") || label.endsWith("-")) {
            return false;
        }
        for (let i = 0; i < label.length; i++) {
            const c = label[i];
            const code = c.charCodeAt(0);
            const isDigit = code >= 48 && code <= 57;
            const isLower = code >= 97 && code <= 122;
            const isUpper = code >= 65 && code <= 90;
            const isHyphen = c === "-";
            if (!isDigit && !isLower && !isUpper && !isHyphen) {
                return false;
            }
        }
    }
    return true;
}

export default class WifiTransport extends Transport {
    declare env: any;
    declare host: any;
    declare opened: boolean;
    declare scheme: any;
    declare timeoutMs: any;
    constructor(
        ipAddressOrHost: string,
        options: { timeoutMs?: number; env?: Record<string, any>; scheme?: string } = {}
    ) {
        super("wifi");
        if (!WifiTransport.isValidHost(ipAddressOrHost)) {
            const err = new Error("invalid_host");
            (err as Error & { code?: string; status?: number; body?: unknown }).code = "INVALID_HOST";
            throw err;
        }
        this.host = ipAddressOrHost;
        this.timeoutMs = options.timeoutMs || DEFAULT_TIMEOUT_MS;
        this.env = options.env || (typeof window !== "undefined" ? window : globalThis);
        this.scheme = options.scheme || "http";
    }

    static isValidHost(value: unknown): boolean {
        if (typeof value !== "string") {
            return false;
        }
        const trimmed = value.trim();
        if (!trimmed || trimmed.length > 253) {
            return false;
        }
        return isValidIpv4(trimmed) || isValidHostname(trimmed);
    }

    async open() {
        // No persistent stream, as OTA upload is one-shot. Kept to keep API symmetric.
        this.opened = true;
    }

    async close() {
        this.opened = false;
    }

    /** Upload a firmware blob to /update on the configured device. */
    async upload(blob: Blob, onProgress?: (percentage: number) => void): Promise<unknown> {
        if (!blob) {
            const err = new Error("no_payload");
            (err as Error & { code?: string; status?: number; body?: unknown }).code = "NO_PAYLOAD";
            throw err;
        }
        const Xhr = this.env.XMLHttpRequest;
        if (!Xhr) {
            const err = new Error("xhr_unavailable");
            (err as Error & { code?: string; status?: number; body?: unknown }).code = "XHR_UNAVAILABLE";
            throw err;
        }
        return new Promise<any>((resolve, reject) => {
            const xhr = new Xhr();
            const url = `${this.scheme}://${this.host}/update`;
            xhr.open("POST", url, true);
            xhr.timeout = this.timeoutMs;

            if (xhr.upload && typeof onProgress === "function") {
                xhr.upload.onprogress = (event) => {
                    if (event.lengthComputable && event.total > 0) {
                        const percentage = Math.floor((event.loaded / event.total) * 100);
                        onProgress(percentage);
                    }
                };
            }

            xhr.ontimeout = () => {
                const err = new Error("upload_timeout");
                (err as Error & { code?: string; status?: number; body?: unknown }).code = "UPLOAD_TIMEOUT";
                reject(err);
            };
            xhr.onerror = () => {
                const err = new Error("network_error");
                (err as Error & { code?: string; status?: number; body?: unknown }).code = "NETWORK_ERROR";
                reject(err);
            };
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve({ status: xhr.status, body: xhr.responseText });
                    return;
                }
                const err = new Error(`http_${xhr.status}`);
                (err as Error & { code?: string; status?: number; body?: unknown }).code = "HTTP_ERROR";
                (err as Error & { code?: string; status?: number; body?: unknown }).status = xhr.status;
                (err as Error & { code?: string; status?: number; body?: unknown }).body = xhr.responseText;
                reject(err);
            };

            const formData = new this.env.FormData();
            formData.append("update", blob, "firmware.bin");
            xhr.send(formData);
        });
    }

    canOtaFlash() {
        return true;
    }

    description() {
        return `wifi://${this.host}`;
    }
}
