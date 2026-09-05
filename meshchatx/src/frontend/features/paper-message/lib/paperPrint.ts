// SPDX-License-Identifier: 0BSD

import ToastUtils from "../../../js/ToastUtils.js";
import Utils from "../../../js/Utils.js";
import type { PaperPrintOptions } from "./types.js";

/**
 * Open print window and trigger print for the generated QR code canvas
 */
export function printPaperQr({ canvas, destinationHash = "" }: PaperPrintOptions): boolean {
    if (!canvas) {
        return false;
    }
    const dataUrl = canvas.toDataURL("image/png");
    if (!dataUrl) {
        return false;
    }
    const printWindow = window.open("", "_blank");
    if (!printWindow) {
        ToastUtils.error("Pop-up blocked. Please allow pop-ups to print.");
        return false;
    }
    const safeDataUrl = Utils.escapeHtml(dataUrl);
    const safeRecipient = Utils.escapeHtml(destinationHash);
    printWindow.document.write(`
        <html>
            <head>
                <title>LXMF Paper Message</title>
                <style>
                    body { display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; font-family: sans-serif; }
                    img { width: 400px; height: 400px; margin-bottom: 20px; }
                    .hash { font-family: monospace; font-size: 12px; color: #666; }
                    @media print { body { height: auto; padding: 20px; } }
                </style>
            </head>
            <body>
                <h1>LXMF Paper Message</h1>
                <img src="${safeDataUrl}" />
                <div class="hash">Recipient: ${safeRecipient}</div>
                <p>Scan this code with an LXMF-compatible app to read the message.</p>
                <script>window.onload = () => { window.print(); window.close(); }</${"script"}>
            </body>
        </html>
    `);
    printWindow.document.close();
    return true;
}

/**
 * Trigger download of the QR code canvas image as PNG
 */
export function downloadPaperQr(canvas: HTMLCanvasElement, filename?: string): void {
    if (!canvas) {
        return;
    }
    const dataUrl = canvas.toDataURL("image/png");
    if (!dataUrl) {
        return;
    }
    const link = document.createElement("a");
    link.download = filename || `lxmf-paper-message-${Date.now()}.png`;
    link.href = dataUrl;
    link.click();
}
