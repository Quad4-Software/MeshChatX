/**
 * One-line preview text for the conversation list / sidebar (LXMF latest row).
 * Handles plain content, Columba reactions, location/telemetry fields,
 * Sideband location-request commands, and media-only payloads (image, audio,
 * file attachments). Pairs with the Python helper
 * lxmf_sidebar_preview_for_conversation_latest_row.
 */

import { reactionEmojiFromLxmfMessageFields } from "./lxmfReactions.js";

function sidebarActorName(msg, { myLxmfAddressHash, peerDisplayName, t }) {
    const incoming = Boolean(msg?.is_incoming);
    const src = String(msg?.source_hash || "").toLowerCase();
    const me = String(myLxmfAddressHash || "").toLowerCase();
    const senderIsYou = !incoming && me && src === me;
    if (incoming) {
        return peerDisplayName || "Anonymous Peer";
    }
    if (senderIsYou) {
        return typeof t === "function" ? t("messages.reaction_you") : "You";
    }
    return peerDisplayName || "Anonymous Peer";
}

function fieldsHaveSidebandLocationRequest(fields) {
    if (!fields?.commands || !Array.isArray(fields.commands)) {
        return false;
    }
    return fields.commands.some(
        (c) => c && (c["0x01"] !== undefined || c["1"] !== undefined || c["0x1"] !== undefined)
    );
}

function fieldsHaveTelemetryLocation(fields) {
    const loc = fields?.telemetry?.location;
    return loc != null && typeof loc === "object";
}

function isOutboundFromSelf(msg, myLxmfAddressHash) {
    if (msg?.is_incoming) {
        return false;
    }
    const src = String(msg?.source_hash || "").toLowerCase();
    const me = String(myLxmfAddressHash || "").toLowerCase();
    return Boolean(me && src === me);
}

/**
 * @param {object} msg
 * @param {{ myLxmfAddressHash: string, peerDisplayName: string, t?: (k: string, v?: object) => string }} ctx
 * @returns {string}
 */
export function lxmfConversationListPreview(msg, { myLxmfAddressHash, peerDisplayName, t }) {
    const raw = msg?.content;
    const content = typeof raw === "string" ? raw.trim() : "";
    if (content) {
        return raw;
    }

    const fields = msg?.fields;
    const name = sidebarActorName(msg, { myLxmfAddressHash, peerDisplayName, t });

    const emoji =
        (msg?.is_reaction && typeof msg?.reaction_emoji === "string" && msg.reaction_emoji) ||
        reactionEmojiFromLxmfMessageFields(fields);
    if (emoji) {
        if (typeof t === "function") {
            return t("messages.conversation_reaction_preview", { name, emoji });
        }
        return `${name} reacted ${emoji}`;
    }

    if (fieldsHaveTelemetryLocation(fields)) {
        const fromSelf = isOutboundFromSelf(msg, myLxmfAddressHash);
        if (typeof t === "function") {
            return fromSelf
                ? t("messages.conversation_location_share_you")
                : t("messages.conversation_location_share_other", { name });
        }
        return fromSelf ? "You shared your location" : `${name} shared their location`;
    }

    if (fields?.telemetry_stream?.length) {
        if (typeof t === "function") {
            return t("messages.conversation_telemetry_stream_preview", { name });
        }
        return `${name} sent a telemetry stream`;
    }

    if (fields?.telemetry && typeof fields.telemetry === "object" && Object.keys(fields.telemetry).length > 0) {
        if (typeof t === "function") {
            return t("messages.conversation_telemetry_preview", { name });
        }
        return `${name} sent telemetry`;
    }

    if (fieldsHaveSidebandLocationRequest(fields)) {
        if (typeof t === "function") {
            return msg?.is_incoming
                ? t("messages.conversation_location_request_in_preview", { name })
                : t("messages.conversation_location_request_out_preview", { name });
        }
        return msg?.is_incoming ? `${name} requested your location` : `${name} sent a location request`;
    }

    const imageField = fields?.image;
    if (imageField && typeof imageField === "object" && Object.keys(imageField).length > 0) {
        const fromSelf = isOutboundFromSelf(msg, myLxmfAddressHash);
        if (typeof t === "function") {
            return fromSelf ? t("messages.conversation_image_you") : t("messages.conversation_image_other", { name });
        }
        return fromSelf ? "You sent an image" : `${name} sent an image`;
    }

    const audioField = fields?.audio;
    if (audioField && typeof audioField === "object" && Object.keys(audioField).length > 0) {
        const fromSelf = isOutboundFromSelf(msg, myLxmfAddressHash);
        if (typeof t === "function") {
            return fromSelf ? t("messages.conversation_voice_you") : t("messages.conversation_voice_other", { name });
        }
        return fromSelf ? "You sent a voice note" : `${name} sent a voice note`;
    }

    const files = fields?.file_attachments;
    if (Array.isArray(files) && files.length > 0) {
        const fromSelf = isOutboundFromSelf(msg, myLxmfAddressHash);
        const n = files.length;
        if (typeof t === "function") {
            if (n === 1) {
                return fromSelf ? t("messages.conversation_file_you") : t("messages.conversation_file_other", { name });
            }
            return fromSelf
                ? t("messages.conversation_files_you", { count: n })
                : t("messages.conversation_files_other", { name, count: n });
        }
        if (n === 1) {
            return fromSelf ? "You sent a file" : `${name} sent a file`;
        }
        return fromSelf ? `You sent ${n} files` : `${name} sent ${n} files`;
    }

    return raw ?? "";
}
