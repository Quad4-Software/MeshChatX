// SPDX-License-Identifier: 0BSD

import { rnodeIntegrityKeyForSrc } from "../../../js/rnode/rnodeIntegrityKey.js";

declare global {
    interface Window {
        zip?: any;
        CryptoJS?: any;
        ESPLoader?: any;
        Transport?: any;
        serial?: any;
    }
}

let cachedIntegrity: Record<string, string> | null = null;

export async function loadRnodeIntegrity(): Promise<Record<string, string>> {
    if (cachedIntegrity) return cachedIntegrity;
    try {
        const res = await fetch("/rnode-flasher/js/integrity.json");
        if (!res.ok) throw new Error("Failed to load integrity.json");
        const data = await res.json();
        cachedIntegrity = data.files || {};
        return cachedIntegrity!;
    } catch (e) {
        console.error("RNode: Failed to load integrity hashes:", e);
        throw e;
    }
}

export async function loadScriptWithIntegrity(src: string): Promise<void> {
    const integrity = await loadRnodeIntegrity();
    const filename = rnodeIntegrityKeyForSrc(src, integrity);
    const expectedHash = integrity?.[filename];

    if (!expectedHash) {
        throw new Error(`RNode: SRI hash missing for ${filename || src}. Refusing to load untrusted code.`);
    }

    const res = await fetch(src);
    if (!res.ok) {
        throw new Error(`RNode: failed to fetch ${src} (${res.status})`);
    }
    const buf = await res.arrayBuffer();
    const hash = await crypto.subtle.digest("SHA-384", buf);
    const actualHash = "sha384-" + btoa(String.fromCharCode(...new Uint8Array(hash)));
    if (actualHash !== expectedHash) {
        throw new Error(`RNode: SRI hash mismatch for ${filename}. Possible tampering detected.`);
    }

    const blob = new Blob([buf], { type: "application/javascript" });
    const blobUrl = URL.createObjectURL(blob);
    return new Promise((resolve, reject) => {
        const script = document.createElement("script");
        script.src = blobUrl;
        script.onload = () => {
            URL.revokeObjectURL(blobUrl);
            resolve();
        };
        script.onerror = () => {
            URL.revokeObjectURL(blobUrl);
            reject(new Error(`Failed to load ${src}`));
        };
        document.head.appendChild(script);
    });
}

export async function loadVendorLibraries(force = false): Promise<void> {
    if (!force && window.zip && window.CryptoJS && window.ESPLoader) return;
    const libs = [
        "/rnode-flasher/js/zip.min.js",
        "/rnode-flasher/js/crypto-js@3.9.1-1/core.js",
        "/rnode-flasher/js/crypto-js@3.9.1-1/md5.js",
    ];
    for (const lib of libs) {
        try {
            await loadScriptWithIntegrity(lib);
        } catch {
            // continue best-effort
        }
    }
    try {
        const esptoolPath = "/rnode-flasher/js/esptool-js@0.4.5/bundle.js";
        const esptool = await import(/* @vite-ignore */ esptoolPath);
        window.ESPLoader = esptool.ESPLoader;
        window.Transport = esptool.Transport;

        const serialPolyfillPath = "/rnode-flasher/js/web-serial-polyfill@1.0.15/dist/serial.js";
        const serialPolyfill = await import(/* @vite-ignore */ serialPolyfillPath);
        if (serialPolyfill.serial) {
            window.serial = serialPolyfill.serial;
        }
    } catch (e) {
        console.error("Failed to load ES module vendor libraries:", e);
    }
    if (!(navigator as any).serial && (navigator as any).usb && window.serial) {
        (navigator as any).serial = window.serial;
    }
}

export function readAsBinaryString(blob: Blob): Promise<string> {
    return new Promise((resolve) => {
        const r = new FileReader();
        r.onload = () => resolve(r.result as string);
        r.readAsBinaryString(blob);
    });
}
