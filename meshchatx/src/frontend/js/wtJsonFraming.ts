// SPDX-License-Identifier: 0BSD

/**
 * Newline-delimited JSON framing for experimental WebTransport live channel.
 */

export const WT_MAX_FRAME_CHARS = 1024 * 1024;

/**
 * @param {object} obj
 * @returns {string}
 */
export function encodeWtJsonLine(obj) {
    return `${JSON.stringify(obj)}\n`;
}

/**
 * Feed chunks into a line buffer. Returns parsed objects and leftover text.
 * @param {string} buffer
 * @param {string} chunk
 * @returns {{ objects: object[], buffer: string, errors: string[] }}
 */
export function feedWtJsonLines(buffer: string, chunk: string) {
    const errors: string[] = [];
    let buf = (buffer || "") + (chunk || "");
    if (buf.length > WT_MAX_FRAME_CHARS * 2) {
        return { objects: [] as object[], buffer: "", errors: ["frame_overflow"] };
    }
    const objects: object[] = [];
    let idx;
    while ((idx = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, idx);
        buf = buf.slice(idx + 1);
        if (!line.length) {
            continue;
        }
        if (line.length > WT_MAX_FRAME_CHARS) {
            errors.push("line_too_large");
            continue;
        }
        if (line.includes("\0")) {
            errors.push("embedded_nul");
            continue;
        }
        try {
            const parsed = JSON.parse(line);
            if (parsed && typeof parsed === "object") {
                objects.push(parsed);
            } else {
                errors.push("not_object");
            }
        } catch {
            errors.push("invalid_json");
        }
    }
    return { objects, buffer: buf, errors };
}

/**
 * @returns {boolean}
 */
export function clientSupportsWebTransport() {
    return typeof WebTransport === "function";
}
