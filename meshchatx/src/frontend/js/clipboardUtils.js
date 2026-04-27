/**
 * Clipboard helpers for browsers without a secure context (e.g. http://0.0.0.0:8000)
 * where navigator.clipboard may be missing or reject.
 */

/**
 * Browsers set `false` on http://0.0.0.0 and similar; `undefined` in some test envs is treated as allowed.
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
