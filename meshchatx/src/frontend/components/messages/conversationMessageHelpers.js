/**
 * Pure helpers for LXMF message display predicates and clipboard/drag image extraction.
 */

/**
 * @param {object} msg
 * @returns {boolean}
 */
export function isTelemetryOnly(msg) {
    const hasContent = msg.content && msg.content.trim() !== "";
    const hasAttachments = msg.fields?.image || msg.fields?.audio || msg.fields?.file_attachments;
    const hasTelemetry = msg.fields?.telemetry || msg.fields?.telemetry_stream;
    const hasCommands = msg.fields?.commands && msg.fields.commands.some((c) => c["0x01"]);

    return !hasContent && !hasAttachments && !!(hasTelemetry || hasCommands);
}

/**
 * @param {object} msg
 * @returns {boolean}
 */
export function hasRenderableContent(msg) {
    if (msg.content && msg.content.trim() !== "") return true;
    if (msg.fields?.image) return true;
    if (msg.fields?.audio) return true;
    if (msg.fields?.file_attachments) return true;
    if (msg.fields?.telemetry || msg.fields?.telemetry_stream) return true;
    if (msg.fields?.commands && msg.fields.commands.some((c) => c["0x01"] || c["1"] || c["0x1"])) return true;
    return false;
}

/**
 * @param {object} chatItem
 * @param {(item: object) => boolean} shouldHideAutoImageCaption
 * @returns {boolean}
 */
export function isImageOnlyMessage(chatItem, shouldHideAutoImageCaption) {
    const msg = chatItem.lxmf_message;
    if (!msg.fields?.image) return false;
    if (msg.fields?.audio || msg.fields?.file_attachments) return false;
    const content = (msg.content || "").trim();
    if (content && !shouldHideAutoImageCaption(chatItem)) return false;
    if (msg.reply_to_hash) return false;
    if (msg.fields?.telemetry || msg.fields?.telemetry_stream) return false;
    if (msg.fields?.commands && msg.fields.commands.some((c) => c["0x01"] || c["1"] || c["0x1"])) return false;
    return true;
}

/**
 * @param {DataTransfer | null | undefined} dt
 * @returns {File[]}
 */
export function collectImageFilesFromDataTransfer(dt) {
    if (!dt) {
        return [];
    }
    const out = [];
    const seen = new Set();
    const pushIfImage = (f) => {
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
                const f = item.getAsFile();
                pushIfImage(f);
            }
        }
    }
    return out;
}

/**
 * @param {ClipboardEvent} event
 * @returns {File[]}
 */
export function extractClipboardImageFiles(event) {
    const cd = event.clipboardData;
    if (!cd?.items?.length) {
        return [];
    }
    const imageBlobs = [];
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
