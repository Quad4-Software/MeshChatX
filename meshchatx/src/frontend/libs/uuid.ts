// SPDX-License-Identifier: 0BSD

const UUID_V4_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

type UuidCrypto = {
    getRandomValues?: (array: Uint8Array) => Uint8Array;
    randomUUID?: () => string;
};

type UuidOptions = {
    crypto?: UuidCrypto | null;
};

function getCrypto(): UuidCrypto | undefined {
    if (typeof globalThis !== "undefined" && globalThis.crypto) {
        return globalThis.crypto as UuidCrypto;
    }
    return undefined;
}

export function resolveCrypto(options: UuidOptions = {}): UuidCrypto | null | undefined {
    if (Object.prototype.hasOwnProperty.call(options, "crypto")) {
        return options.crypto;
    }
    return getCrypto();
}

export function fillRandomBytes(bytes: Uint8Array, options: UuidOptions = {}): Uint8Array {
    if (!(bytes instanceof Uint8Array)) {
        throw new TypeError("fillRandomBytes expects a Uint8Array");
    }
    const c = resolveCrypto(options);
    if (c && typeof c.getRandomValues === "function") {
        c.getRandomValues(bytes);
        return bytes;
    }
    for (let i = 0; i < bytes.length; i++) {
        bytes[i] = Math.floor(Math.random() * 256) & 0xff;
    }
    return bytes;
}

export function randomUuidV4(options: UuidOptions = {}): string {
    const c = resolveCrypto(options);
    if (c && typeof c.randomUUID === "function") {
        return c.randomUUID();
    }
    const bytes = fillRandomBytes(new Uint8Array(16), { crypto: c ?? null });
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

export function uuidv4(options: UuidOptions = {}): string {
    return randomUuidV4(options);
}

export function isUuidV4(value: unknown): boolean {
    return typeof value === "string" && UUID_V4_RE.test(value);
}

export { UUID_V4_RE };
