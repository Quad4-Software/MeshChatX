/**
 * Clipboard helpers for browsers without a secure context (e.g. http://0.0.0.0:8000)
 * where navigator.clipboard may be missing or reject.
 */

/**
 * Browsers set `false` on http://0.0.0.0 and similar. `undefined` in some test envs is treated as allowed.
 * @returns {boolean}
 */
export function isWindowSecureContext() {
    if (typeof window === "undefined") {
        return false;
    }
    return window.isSecureContext !== false;
}

/**
 * Whether async clipboard read is expected to work (secure context + API present).
 * @returns {boolean}
 */
export function canUseAsyncClipboardRead() {
    return (
        typeof navigator !== "undefined" &&
        !!navigator.clipboard &&
        typeof navigator.clipboard.readText === "function" &&
        isWindowSecureContext()
    );
}

/**
 * Whether async clipboard image write is expected to work.
 * @returns {boolean}
 */
export function canUseAsyncClipboardImageWrite() {
    return (
        typeof navigator !== "undefined" &&
        !!navigator.clipboard &&
        typeof navigator.clipboard.write === "function" &&
        typeof ClipboardItem !== "undefined" &&
        isWindowSecureContext()
    );
}

/**
 * @param {string} text
 * @returns {Promise<boolean>}
 */
export async function copyTextToClipboard(text) {
    if (text == null || text === "") {
        return false;
    }
    const s = String(text);
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
        try {
            await navigator.clipboard.writeText(s);
            return true;
        } catch {
            // fall through to execCommand
        }
    }
    try {
        const ta = document.createElement("textarea");
        ta.value = s;
        ta.setAttribute("readonly", "");
        ta.setAttribute("aria-hidden", "true");
        ta.style.position = "fixed";
        ta.style.left = "-9999px";
        ta.style.top = "0";
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        const ok = document.execCommand("copy");
        document.body.removeChild(ta);
        return ok;
    } catch {
        return false;
    }
}

/**
 * Copy an image Blob to the system clipboard (PNG preferred when conversion works).
 * @param {Blob} blob
 * @returns {Promise<boolean>}
 */
export async function copyImageBlobToClipboard(blob) {
    if (!(blob instanceof Blob) || blob.size <= 0) {
        return false;
    }
    if (!canUseAsyncClipboardImageWrite()) {
        return false;
    }
    const type = blob.type && blob.type.startsWith("image/") ? blob.type : "image/png";
    try {
        await navigator.clipboard.write([new ClipboardItem({ [type]: blob })]);
        return true;
    } catch {
        // Many hosts only accept image/png on the clipboard.
    }
    if (type === "image/png") {
        return false;
    }
    try {
        const pngBlob = await convertImageBlobToPng(blob);
        if (!pngBlob) {
            return false;
        }
        await navigator.clipboard.write([new ClipboardItem({ "image/png": pngBlob })]);
        return true;
    } catch {
        return false;
    }
}

/**
 * @param {Blob} blob
 * @returns {Promise<Blob | null>}
 */
async function convertImageBlobToPng(blob) {
    if (typeof createImageBitmap === "function") {
        try {
            const bitmap = await createImageBitmap(blob);
            const canvas = document.createElement("canvas");
            canvas.width = bitmap.width;
            canvas.height = bitmap.height;
            const ctx = canvas.getContext("2d");
            if (!ctx) {
                bitmap.close?.();
                return null;
            }
            ctx.drawImage(bitmap, 0, 0);
            bitmap.close?.();
            return await new Promise<any>((resolve) => {
                canvas.toBlob((out) => resolve(out), "image/png");
            });
        } catch {
            // fall through to HTMLImageElement path
        }
    }
    if (typeof Image === "undefined" || typeof URL === "undefined") {
        return null;
    }
    const objectUrl = URL.createObjectURL(blob);
    try {
        const img = await new Promise<any>((resolve, reject) => {
            const el = new Image();
            el.onload = () => resolve(el);
            el.onerror = () => reject(new Error("image_load_failed"));
            el.src = objectUrl;
        });
        const canvas = document.createElement("canvas");
        canvas.width = img.naturalWidth || img.width;
        canvas.height = img.naturalHeight || img.height;
        const ctx = canvas.getContext("2d");
        if (!ctx) {
            return null;
        }
        ctx.drawImage(img, 0, 0);
        return await new Promise<any>((resolve) => {
            canvas.toBlob((out) => resolve(out), "image/png");
        });
    } catch {
        return null;
    } finally {
        URL.revokeObjectURL(objectUrl);
    }
}

/**
 * @returns {Promise<{ ok: true, text: string } | { ok: false, code: string }>}
 */
export async function readTextFromClipboard() {
    if (typeof navigator === "undefined" || !navigator.clipboard?.readText) {
        return { ok: false, code: "unavailable" };
    }
    if (!isWindowSecureContext()) {
        return { ok: false, code: "insecure_context" };
    }
    try {
        const text = await navigator.clipboard.readText();
        return { ok: true, text: text ?? "" };
    } catch {
        return { ok: false, code: "denied" };
    }
}
