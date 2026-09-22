// SPDX-License-Identifier: 0BSD

export type LxmfFields = {
    file_attachments?: unknown[];
    image?: unknown;
    audio?: unknown;
    telemetry?: unknown;
    telemetry_stream?: unknown;
    commands?: Array<Record<string, unknown>>;
};

export type LxmfMessageLike = {
    content?: string;
    reply_to_hash?: string | null;
    fields?: LxmfFields;
    hash?: string;
    [key: string]: unknown;
};

export type ChatItemLike = {
    lxmf_message?: LxmfMessageLike;
    is_outbound?: boolean;
};

export function hasFileAttachments(msg: LxmfMessageLike | null | undefined): boolean {
    const files = msg?.fields?.file_attachments;
    return Array.isArray(files) && files.length > 0;
}

export function isTelemetryOnly(msg: LxmfMessageLike | null | undefined): boolean {
    const hasContent = msg?.content && msg.content.trim() !== "";
    const hasAttachments = msg?.fields?.image || msg?.fields?.audio || hasFileAttachments(msg);
    const hasTelemetry = msg?.fields?.telemetry || msg?.fields?.telemetry_stream;
    const hasCommands = msg?.fields?.commands && msg.fields.commands.some((c) => c["0x01"]);

    return !hasContent && !hasAttachments && !!(hasTelemetry || hasCommands);
}

export function hasRenderableContent(msg: LxmfMessageLike | null | undefined): boolean {
    if (!msg) return false;
    if (msg.content && msg.content.trim() !== "") return true;
    if (msg.fields?.image) return true;
    if (msg.fields?.audio) return true;
    if (hasFileAttachments(msg)) return true;
    if (msg.fields?.telemetry || msg.fields?.telemetry_stream) return true;
    if (msg.fields?.commands && msg.fields.commands.some((c) => c["0x01"] || c["1"] || c["0x1"])) return true;
    return false;
}

export function isFileOnlyMessage(
    chatItem: ChatItemLike,
    shouldHideAutoImageCaption: (item: ChatItemLike) => boolean
): boolean {
    const msg = chatItem.lxmf_message;
    if (!msg || !hasFileAttachments(msg)) return false;
    if (msg.fields?.image || msg.fields?.audio) return false;
    const content = (msg.content || "").trim();
    if (content && !shouldHideAutoImageCaption(chatItem)) return false;
    if (msg.reply_to_hash) return false;
    if (msg.fields?.telemetry || msg.fields?.telemetry_stream) return false;
    if (msg.fields?.commands && msg.fields.commands.some((c) => c["0x01"] || c["1"] || c["0x1"])) return false;
    return true;
}

export function isImageOnlyMessage(
    chatItem: ChatItemLike,
    shouldHideAutoImageCaption: (item: ChatItemLike) => boolean
): boolean {
    const msg = chatItem.lxmf_message;
    if (!msg?.fields?.image) return false;
    if (msg.fields?.audio || hasFileAttachments(msg)) return false;
    const content = (msg.content || "").trim();
    if (content && !shouldHideAutoImageCaption(chatItem)) return false;
    if (msg.reply_to_hash) return false;
    if (msg.fields?.telemetry || msg.fields?.telemetry_stream) return false;
    if (msg.fields?.commands && msg.fields.commands.some((c) => c["0x01"] || c["1"] || c["0x1"])) return false;
    return true;
}

export function hasMessageBubble(
    chatItem: ChatItemLike,
    shouldHideAutoImageCaption: (item: ChatItemLike) => boolean
): boolean {
    if (!chatItem?.lxmf_message) {
        return false;
    }
    if (isImageOnlyMessage(chatItem, shouldHideAutoImageCaption)) {
        return false;
    }
    return hasRenderableContent(chatItem.lxmf_message);
}

export function collectImageFilesFromDataTransfer(dt: DataTransfer | null | undefined): File[] {
    if (!dt) {
        return [];
    }
    const out: File[] = [];
    const seen = new Set<string>();
    const pushIfImage = (f: File | null) => {
        if (!f?.type?.startsWith("image/")) {
            return;
        }
        const k = `${f.name}:${f.size}:${f.lastModified}`;
        if (seen.has(k)) {
            return;
        }
        seen.add(k);
        out.push(f);
    };
    if (dt.files?.length) {
        for (let i = 0; i < dt.files.length; i++) {
            pushIfImage(dt.files[i]);
        }
        if (out.length > 0) {
            return out;
        }
    }
    if (dt.items?.length) {
        for (let i = 0; i < dt.items.length; i++) {
            const item = dt.items[i];
            if (item.kind === "file" && item.type?.startsWith("image/")) {
                pushIfImage(item.getAsFile());
            }
        }
    }
    return out;
}

export function extractClipboardImageFiles(event: ClipboardEvent): File[] {
    const cd = event.clipboardData;
    if (!cd?.items?.length) {
        return [];
    }
    const imageBlobs: File[] = [];
    for (let i = 0; i < cd.items.length; i++) {
        const item = cd.items[i];
        if (item.kind === "file" && item.type.startsWith("image/")) {
            const f = item.getAsFile();
            if (f) {
                imageBlobs.push(f);
            }
        }
    }
    return imageBlobs;
}
