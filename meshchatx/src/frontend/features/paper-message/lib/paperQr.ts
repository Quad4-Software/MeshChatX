// SPDX-License-Identifier: 0BSD

import QRCode from "qrcode";
import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import {
    LXM_URI_PATTERN,
    PAPER_MESSAGE_HASH_MAX_LEN,
    QR_CODE_MARGIN,
    QR_CODE_WIDTH,
    QR_ERROR_CORRECTION_LEVEL,
} from "./constants.js";

/**
 * Check if the given URI matches supported LXMF, LXMA, or LXM schemes
 */
export function isValidLxmUri(uri: string): boolean {
    return typeof uri === "string" && LXM_URI_PATTERN.test(uri.trim());
}

/**
 * Validate destination hash length
 */
export function isValidDestinationHash(hash: string): boolean {
    return typeof hash === "string" && hash.trim().length === PAPER_MESSAGE_HASH_MAX_LEN;
}

/**
 * Determine whether message details are sufficient to generate a paper message
 */
export function canGeneratePaperMessage(destinationHash: string, content: string): boolean {
    return destinationHash.trim().length === PAPER_MESSAGE_HASH_MAX_LEN && content.length > 0;
}

/**
 * Render given URI to an HTML canvas element using QRCode
 */
export async function renderQrCodeToCanvas(canvas: HTMLCanvasElement, uri: string): Promise<boolean> {
    if (!canvas || !uri) {
        return false;
    }
    try {
        await QRCode.toCanvas(canvas, uri, {
            width: QR_CODE_WIDTH,
            margin: QR_CODE_MARGIN,
            color: {
                dark: "#000000",
                light: "#ffffff",
            },
            errorCorrectionLevel: QR_ERROR_CORRECTION_LEVEL,
        });
        canvas.style.maxWidth = "100%";
        canvas.style.height = "auto";
        canvas.classList.add("rounded-lg");
        return true;
    } catch (err) {
        console.error("Failed to render QR code:", err);
        ToastUtils.error(t("messages.failed_render_qr"));
        return false;
    }
}
