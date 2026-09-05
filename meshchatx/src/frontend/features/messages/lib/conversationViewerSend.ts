// SPDX-License-Identifier: 0BSD

import Utils from "../../../js/Utils.js";
import { uuidv4 } from "../../../libs/uuid.js";
import type { ApiClient } from "../../../js/apiClient.js";
import { OUTBOUND_OVERSIZED_CONFIRM_BYTES } from "./constants.js";
import type { LxmfFields, LxmfMessage, ViewerPathSnapshot } from "./conversationViewerCtx.js";
import { warmOutboundPath } from "./conversationViewerPath.js";

export type ComposeAudio = {
    audio_blob: Blob;
    audio_preview_url: string;
    audio_mode?: number;
};

export type OutboundJob = {
    destinationHash: string;
    deliveryMethod: string | null;
    text: string;
    fields: LxmfFields;
    images: Array<{ image_type: string; image_bytes: string; image_size: number }>;
    replyToHash: string | null;
    replyQuotedContent: string | null;
    myLxmfAddressHash: string;
    pendingHash: string | null;
    cancelled?: boolean;
    messageHash?: string;
};

export async function buildOutboundJob(input: {
    destinationHash: string;
    deliveryMethod: string | null;
    text: string;
    files: File[];
    images: File[];
    audio: ComposeAudio | null;
    telemetry?: Record<string, unknown> | null;
    replyToHash?: string | null;
    replyQuotedContent?: string | null;
    myLxmfAddressHash: string;
    confirmOversized: (size: number) => Promise<boolean>;
}): Promise<OutboundJob | null> {
    const fields: LxmfFields = {};
    let totalSize = input.text.length;
    if (input.telemetry) {
        fields.telemetry = input.telemetry;
    }
    if (input.files.length > 0) {
        fields.file_attachments = [];
        for (const file of input.files) {
            totalSize += file.size;
            fields.file_attachments.push({
                file_name: file.name,
                file_size: file.size,
                file_bytes: Utils.arrayBufferToBase64(await file.arrayBuffer()),
            });
        }
    }
    if (input.audio) {
        totalSize += input.audio.audio_blob.size;
        fields.audio = {
            audio_mode: input.audio.audio_mode ?? 0x10,
            audio_size: input.audio.audio_blob.size,
            audio_bytes: Utils.arrayBufferToBase64(await input.audio.audio_blob.arrayBuffer()),
        };
    }
    const images: OutboundJob["images"] = [];
    for (const image of input.images) {
        totalSize += image.size;
        images.push({
            image_type: image.type.replace(/^image\//, "") || "png",
            image_size: image.size,
            image_bytes: Utils.arrayBufferToBase64(await image.arrayBuffer()),
        });
    }
    if (totalSize > OUTBOUND_OVERSIZED_CONFIRM_BYTES && !(await input.confirmOversized(totalSize))) {
        return null;
    }
    return {
        destinationHash: input.destinationHash,
        deliveryMethod: input.deliveryMethod,
        text: input.text,
        fields,
        images,
        replyToHash: input.replyToHash ?? null,
        replyQuotedContent: input.replyQuotedContent ?? null,
        myLxmfAddressHash: input.myLxmfAddressHash,
        pendingHash: null,
    };
}

export function optimisticMessage(job: OutboundJob, needsPath: boolean): LxmfMessage {
    job.pendingHash = `pending-${uuidv4()}`;
    const fields: LxmfFields = {};
    if (job.images[0]) {
        fields.image = {
            image_type: job.images[0].image_type,
            image_size: job.images[0].image_size,
            image_bytes: job.images[0].image_bytes,
        };
    }
    return {
        hash: job.pendingHash,
        content: job.text,
        state: "sending",
        progress: 0,
        created_at: new Date().toISOString(),
        destination_hash: job.destinationHash,
        source_hash: job.myLxmfAddressHash,
        fields: Object.keys(fields).length > 0 ? fields : undefined,
        reply_to_hash: job.replyToHash,
        _pendingPathfinding: needsPath,
    };
}

export async function executeOutboundJob(input: {
    api: ApiClient;
    job: OutboundJob;
    pathSnapshot: ViewerPathSnapshot | null;
    propagationHash?: unknown;
}): Promise<LxmfMessage[]> {
    const { api, job } = input;
    if (job.cancelled) {
        return [];
    }
    await warmOutboundPath(api, job.destinationHash, job.deliveryMethod, input.pathSnapshot, input.propagationHash);
    const images = job.images.length > 0 ? job.images : [null];
    const sent: LxmfMessage[] = [];
    for (let index = 0; index < images.length; index++) {
        if (job.cancelled) {
            break;
        }
        const image = images[index];
        const fields: LxmfFields = index === 0 ? { ...job.fields } : {};
        if (image) {
            fields.image = {
                image_type: image.image_type,
                image_bytes: image.image_bytes,
            };
        }
        const response = await api.post("/api/v1/lxmf-messages/send", {
            delivery_method: job.deliveryMethod,
            lxmf_message: {
                destination_hash: job.destinationHash,
                content: index === 0 ? job.text : "",
                reply_to_hash: index === 0 ? job.replyToHash : null,
                reply_quoted_content: index === 0 ? job.replyQuotedContent : null,
                fields,
            },
        });
        const data = response.data as { lxmf_message?: LxmfMessage } | undefined;
        const message = data?.lxmf_message;
        if (message) {
            job.messageHash = message.hash;
            sent.push(message);
        }
    }
    return sent;
}

export async function cancelOutbound(api: ApiClient, hash: string): Promise<LxmfMessage | null> {
    if (!hash || hash.startsWith("pending-")) {
        return null;
    }
    const response = await api.post(`/api/v1/lxmf-messages/${hash}/cancel`);
    const data = response.data as { lxmf_message?: LxmfMessage } | undefined;
    return data?.lxmf_message ?? null;
}
