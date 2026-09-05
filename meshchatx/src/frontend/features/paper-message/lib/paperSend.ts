// SPDX-License-Identifier: 0BSD

import ToastUtils from "../../../js/ToastUtils.js";
import { t } from "../../../js/i18n.js";
import type { PaperMessageSendResult } from "./types.js";

/**
 * Send paper message via the LXMF send API endpoint
 */
export async function sendPaperMessageApi(params: {
    destinationHash: string;
    generatedUri: string;
    canvas?: HTMLCanvasElement | null;
}): Promise<PaperMessageSendResult> {
    const { destinationHash, generatedUri, canvas } = params;
    if (!destinationHash || !generatedUri) {
        return { success: false, message: "Missing destination hash or URI" };
    }

    try {
        const lxmfMessage: Record<string, unknown> = {
            destination_hash: destinationHash,
            content: `Please scan the attached Paper Message or manually ingest this URI: ${generatedUri}`,
            fields: {},
        };

        if (canvas) {
            const dataUrl = canvas.toDataURL("image/png");
            if (dataUrl.includes(",")) {
                const imageBytes = dataUrl.split(",")[1];
                (lxmfMessage.fields as Record<string, unknown>).image = {
                    image_type: "png",
                    image_bytes: imageBytes,
                    name: "paper_message_qr.png",
                };
            }
        }

        const response = await window.api.post("/api/v1/lxmf-messages/send", {
            delivery_method: "opportunistic",
            lxmf_message: lxmfMessage,
        });

        const resData = response?.data as { lxmf_message?: unknown; message?: string } | undefined;

        if (resData?.lxmf_message) {
            ToastUtils.success(t("messages.paper_message_sent"));
            return { success: true };
        }
        const errorMsg = resData?.message || "Failed to send paper message";
        ToastUtils.error(errorMsg);
        return { success: false, message: errorMsg };
    } catch (err) {
        console.error("Failed to send paper message:", err);
        ToastUtils.error(t("messages.failed_send_paper"));
        return { success: false, message: String(err) };
    }
}
