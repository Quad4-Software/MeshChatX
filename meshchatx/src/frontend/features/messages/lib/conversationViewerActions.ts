// SPDX-License-Identifier: 0BSD

import DialogUtils from "../../../js/DialogUtils.js";
import GlobalState from "../../../js/GlobalState.js";
import MarkdownRenderer from "../../../js/MarkdownRenderer.js";
import ToastUtils from "../../../js/ToastUtils.js";
import Utils from "../../../js/Utils.js";
import WebSocketConnection from "../../../js/WebSocketConnection.js";
import { t } from "../../../js/i18n.js";
import { resolveGeoText } from "../../../js/geoLinkify.js";
import { handleRichHtmlLinkClick } from "../../../js/NomadRichHtmlLinks.js";
import { findMapUriInContent, mapLinkKindFromMessage, parseMeshchatMapUri } from "../../../js/mapLinkUtils.js";
import {
    isOpportunisticDeferredDelivery,
    outboundBubbleStatusIconName,
    outboundBubbleStatusTitleKey,
} from "../../../js/outboundMessageStatus.js";
import {
    applyRelayShareLink,
    findRelayUriInContent,
    parseMeshchatRelayUri,
    parseRelayUri,
} from "../../../js/relayLinkUtils.js";
import { formatDate, fromNow } from "../../../libs/datetime.js";
import { AUTO_IMAGE_CAPTION_MAX_CHARS, MESSAGE_BODY_MAX_DISPLAY_CHARS } from "./constants.js";
import {
    hasFileAttachments,
    hasMessageBubble,
    isImageOnlyMessage,
    type ChatItemLike,
} from "./conversationMessageHelpers.js";
import { outboundStateTitle, outboundTransferStatsLabel, transferProgressPercent } from "./conversationOutboundUi.js";
import { isPaperMessageIngested, markPaperMessageIngested } from "./conversationPaperIngest.js";
import type {
    ConversationViewerActions,
    ConversationViewerActionDeps,
    LxmfMessageLike,
    MessageBubbleViewModel,
    MessageChatItem,
    ParsedMessageItems,
} from "./viewerActions.js";

function imageDataUrl(message: LxmfMessageLike): string {
    const image = message.fields?.image;
    if (typeof image?.image_bytes !== "string") {
        return "";
    }
    const rawType = String(image.image_type || "png")
        .toLowerCase()
        .replace(/^image\//, "");
    const mime = rawType === "jpg" ? "image/jpeg" : rawType === "webm" ? "video/webm" : `image/${rawType}`;
    return `data:${mime};base64,${image.image_bytes}`;
}
function shouldHideAutoImageCaption(chatItem: MessageChatItem): boolean {
    const message = chatItem.lxmf_message;
    const text = String(message.content || "").trim();
    if (!message.fields?.image || !text || text.includes("\n") || text.length > AUTO_IMAGE_CAPTION_MAX_CHARS) {
        return false;
    }
    if (/[\\/<>[\]{}]/.test(text)) {
        return false;
    }
    return /^[\w.\- ()#@%&!+,;=']+\.(png|jpe?g|gif|webp|bmp|heif|heic|avif|svg|ico)$/i.test(text);
}
function canUseImageStrip(chatItem: MessageChatItem): boolean {
    const message = chatItem.lxmf_message;
    return Boolean(
        message.fields?.image &&
        !message.is_spam &&
        !["cancelled", "failed", "rejected"].includes(String(message.state || "")) &&
        !message.reply_to_hash &&
        !message.fields.audio &&
        !message.fields.file_attachments?.length &&
        !message.fields.telemetry &&
        !message.fields.telemetry_stream &&
        !message.fields.commands?.length &&
        (!String(message.content || "").trim() || shouldHideAutoImageCaption(chatItem))
    );
}
function attachmentSize(attachment: unknown, kind: string): string {
    if (!attachment || typeof attachment !== "object") {
        return "0 Bytes";
    }
    const value = attachment as Record<string, unknown>;
    const explicit = Number(value[`${kind}_size`] ?? value.size ?? 0);
    if (explicit > 0) {
        return Utils.formatBytes(explicit);
    }
    const encoded = value[`${kind}_bytes`];
    if (typeof encoded === "string") {
        return Utils.formatBytes(Math.max(0, Math.floor((encoded.length * 3) / 4)));
    }
    return "0 Bytes";
}

function isHex32(value: string): boolean {
    if (value.length !== 32) return false;
    for (let i = 0; i < value.length; i += 1) {
        const code = value.charCodeAt(i);
        const isDigit = code >= 48 && code <= 57;
        const isUpper = code >= 65 && code <= 70;
        const isLower = code >= 97 && code <= 102;
        if (!isDigit && !isUpper && !isLower) return false;
    }
    return true;
}

function takeOptionalBracketField(rest: string, label: string): { value?: string; rest: string } {
    const prefix = ` [${label}: `;
    if (!rest.toLowerCase().startsWith(prefix.toLowerCase())) {
        return { rest };
    }
    const after = rest.slice(prefix.length);
    const close = after.indexOf("]");
    if (close === -1) return { rest };
    const value = after.slice(0, close);
    if (!isHex32(value)) return { rest };
    return { value, rest: after.slice(close + 1) };
}

function normalizeIconColour(value: string | undefined): string {
    const s = String(value || "").trim();
    return /^#?[0-9a-fA-F]{3,8}$/.test(s) ? s : "";
}

// " [ICON: name;fg;bg]" carries the sender's user icon in a shared contact.
// Icon names are not hashes so this needs its own bracket parser.
function takeIconBracketField(rest: string): {
    value?: { icon_name: string; foreground_colour: string; background_colour: string };
    rest: string;
} {
    const prefix = " [ICON:";
    if (!rest.toLowerCase().startsWith(prefix.toLowerCase())) {
        return { rest };
    }
    const after = rest.slice(prefix.length);
    const close = after.indexOf("]");
    if (close === -1) return { rest };
    const inner = after.slice(0, close);
    const [name, fg, bg] = inner.split(";");
    const iconName = String(name || "").trim();
    if (!/^[a-zA-Z0-9_-]+$/.test(iconName)) return { rest };
    return {
        value: {
            icon_name: iconName,
            foreground_colour: normalizeIconColour(fg),
            background_colour: normalizeIconColour(bg),
        },
        rest: after.slice(close + 1),
    };
}

function parseSharedContactContent(
    content: string,
    conversations?: ConversationViewerActionDeps["conversations"]
): { contact: ParsedMessageItems["contact"]; rest: string } | undefined {
    if (!content.toLowerCase().startsWith("contact:")) return undefined;
    let rest = content.slice("contact:".length);
    if (!rest || (rest[0] !== " " && rest[0] !== "\t")) return undefined;
    rest = rest.replace(/^\s+/, "");
    const angleStart = rest.indexOf("<");
    if (angleStart <= 0) return undefined;
    if (!/\s/.test(rest[angleStart - 1] || "")) return undefined;
    const angleEnd = rest.indexOf(">", angleStart + 1);
    if (angleEnd === -1) return undefined;
    const hash = rest.slice(angleStart + 1, angleEnd);
    if (!isHex32(hash)) return undefined;
    const name = rest.slice(0, angleStart).trimEnd();
    if (!name) return undefined;
    rest = rest.slice(angleEnd + 1);
    const lxmf = takeOptionalBracketField(rest, "LXMF");
    rest = lxmf.rest;
    const lxst = takeOptionalBracketField(rest, "LXST");
    rest = lxst.rest;
    const icon = takeIconBracketField(rest);
    rest = icon.rest;
    const contactHash = String(lxmf.value || hash).toLowerCase();
    const existing = (conversations || []).find(
        (item) => String(item.destination_hash || "").toLowerCase() === contactHash
    );
    return {
        contact: {
            name,
            hash,
            lxmf_address: lxmf.value,
            lxst_address: lxst.value,
            lxmf_user_icon: existing?.lxmf_user_icon || icon.value,
        },
        rest,
    };
}

function parseBasicItems(
    chatItem: MessageChatItem,
    conversations?: ConversationViewerActionDeps["conversations"]
): ParsedMessageItems {
    const content = String(chatItem.lxmf_message.content || "");
    if (!content) {
        return {};
    }
    const parsed: ParsedMessageItems = {};
    const contactResult = parseSharedContactContent(content, conversations);
    if (contactResult) {
        parsed.contact = contactResult.contact;
        parsed.isOnlyContact = contactResult.rest.trim() === "";
    }
    const paper = content.match(/(lxm|lxmf):\/\/[a-zA-Z0-9+/=._-]+/i)?.[0];
    if (paper) {
        parsed.paperMessage = paper;
        parsed.isOnlyPaperMessage = content.trim() === paper;
    }
    const mapUri = findMapUriInContent(content);
    if (mapUri) {
        const parsedMap = parseMeshchatMapUri(mapUri);
        if (parsedMap) {
            parsed.mapLink = {
                uri: mapUri,
                parsed: parsedMap,
                kind: mapLinkKindFromMessage(content, parsedMap),
            };
            parsed.isOnlyMapLink = content.trim() === mapUri;
        }
    }
    const relayUri = findRelayUriInContent(content);
    if (relayUri) {
        const parsedRelay = parseMeshchatRelayUri(relayUri);
        if (parsedRelay) {
            parsed.relayLink = {
                uri: relayUri,
                parsed: parsedRelay,
            };
            parsed.isOnlyRelayLink = content.trim() === relayUri;
        }
    }
    return parsed;
}

function pending(chatItem: MessageChatItem): boolean {
    const message = chatItem.lxmf_message;
    return Boolean(
        chatItem.is_outbound &&
        (message._pendingPathfinding || ["outbound", "sending", "generating"].includes(String(message.state || "")))
    );
}

function themedOutbound(chatItem: MessageChatItem): boolean {
    return Boolean(
        chatItem.is_outbound &&
        !chatItem.lxmf_message.is_spam &&
        !chatItem.lxmf_message._pendingPathfinding &&
        !["cancelled", "failed", "rejected"].includes(String(chatItem.lxmf_message.state || ""))
    );
}

function bubbleClass(chatItem: MessageChatItem): string {
    if (!chatItem.is_outbound) {
        return "";
    }
    if (["cancelled", "failed", "rejected"].includes(String(chatItem.lxmf_message.state || ""))) {
        return "bg-sem-action-danger text-white border border-sem-action-danger shadow-xs";
    }
    if (chatItem.lxmf_message._pendingPathfinding) {
        return "bg-sem-surface-muted text-sem-fg border border-sem-border";
    }
    return "bg-sem-action-primary text-white border border-sem-action-primary shadow-xs";
}

function classForOutbound(chatItem: MessageChatItem, themed: string, defaultClass: string, inbound = ""): string {
    if (!chatItem.is_outbound) {
        return inbound;
    }
    return themedOutbound(chatItem) ? themed : defaultClass;
}

type BubbleColorConfig = {
    theme?: string;
    message_outbound_bubble_color?: string | null;
    message_inbound_bubble_color?: string | null;
    message_failed_bubble_color?: string | null;
    message_waiting_bubble_color?: string | null;
};

function bubbleColorConfig(): BubbleColorConfig | undefined {
    return GlobalState.config as BubbleColorConfig | undefined;
}

// Custom hex colors are opt-in: the default values map to semantic tokens so
// theme changes keep working until the user picks a custom color.
function isDefaultBubbleHex(raw: string | null | undefined, defaults: string[]): boolean {
    if (raw == null || String(raw).trim() === "") {
        return true;
    }
    return defaults.includes(String(raw).trim().toLowerCase());
}

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
    const s = String(hex ?? "")
        .trim()
        .replace(/^#/, "");
    if (s.length !== 6 || !/^[0-9a-fA-F]{6}$/.test(s)) {
        return null;
    }
    return {
        r: parseInt(s.slice(0, 2), 16),
        g: parseInt(s.slice(2, 4), 16),
        b: parseInt(s.slice(4, 6), 16),
    };
}

function hexRelativeLuminance(hex: string): number | null {
    const rgb = hexToRgb(hex);
    if (!rgb) {
        return null;
    }
    const toLinear = (c: number) => {
        const x = c / 255;
        return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * toLinear(rgb.r) + 0.7152 * toLinear(rgb.g) + 0.0722 * toLinear(rgb.b);
}

function pickTextColorForBubbleBackground(hex: string): string {
    const lum = hexRelativeLuminance(hex);
    if (lum == null) {
        return "#111827";
    }
    return lum > 0.45 ? "#111827" : "#ffffff";
}

function waitingBubbleBorderForHex(hex: string): string {
    const lum = hexRelativeLuminance(hex);
    if (lum == null) {
        return "1px solid rgba(15, 23, 42, 0.12)";
    }
    return lum > 0.45 ? "1px solid rgba(15, 23, 42, 0.12)" : "1px solid rgba(255, 255, 255, 0.14)";
}

function bubbleStyles(chatItem: MessageChatItem): Record<string, string> {
    const styles: Record<string, string> = {};
    const cfg = bubbleColorConfig();
    const message = chatItem.lxmf_message;
    const isFailed = ["cancelled", "failed"].includes(String(message.state || ""));

    if (isFailed) {
        if (isDefaultBubbleHex(cfg?.message_failed_bubble_color, ["#ef4444", "#dc2626"])) {
            styles["background-color"] = "var(--mc-bubble-failed)";
            styles["color"] = "var(--mc-bubble-failed-text)";
        } else {
            styles["background-color"] = cfg?.message_failed_bubble_color || "#ef4444";
            styles["color"] = "#ffffff";
        }
    } else if (chatItem.is_outbound) {
        if (message._pendingPathfinding) {
            if (isDefaultBubbleHex(cfg?.message_waiting_bubble_color, ["#e5e7eb", "#3f3f46"])) {
                styles["background-color"] = "var(--mc-bubble-waiting)";
                styles["color"] = "var(--mc-bubble-waiting-text)";
                styles["border"] = "1px solid var(--mc-border)";
                return styles;
            }
            const raw = cfg?.message_waiting_bubble_color;
            let hex = raw != null && String(raw).trim() !== "" ? String(raw).trim() : "#e5e7eb";
            if (cfg?.theme === "dark" && /^#e5e7eb$/i.test(hex)) {
                hex = "#3f3f46";
            }
            styles["background-color"] = hex;
            styles["color"] = pickTextColorForBubbleBackground(hex);
            styles["border"] = waitingBubbleBorderForHex(hex);
            return styles;
        }
        if (isDefaultBubbleHex(cfg?.message_outbound_bubble_color, ["#4f46e5"])) {
            return {};
        }
        styles["background-color"] = cfg?.message_outbound_bubble_color || "#4f46e5";
        styles["color"] = "#ffffff";
    } else if (cfg?.message_inbound_bubble_color) {
        styles["background-color"] = cfg.message_inbound_bubble_color;
    }

    return styles;
}

export function createConversationViewerActions(
    deps: ConversationViewerActionDeps
): ConversationViewerActions & { canMergeImageIntoImageStrip: (item: MessageChatItem) => boolean } {
    const lxmfImageUrl = (hash?: string) => (hash ? `/api/v1/lxmf-messages/attachment/${hash}/image` : "");
    const progress = (message: LxmfMessageLike) => {
        if (message._pendingPathfinding) {
            return 0;
        }
        const value = Number(message.progress ?? 0);
        return ["sending", "outbound", "generating"].includes(String(message.state || "")) && value > 0
            ? transferProgressPercent(value, 100)
            : 0;
    };
    const bubbleViewModel = (chatItem: MessageChatItem): MessageBubbleViewModel => {
        const hash = chatItem.lxmf_message.hash;
        const originalContent = String(chatItem.lxmf_message.content || "");
        const translation = hash ? deps.translations?.[hash] : undefined;
        if (translation?.loading) {
            return {
                kind: "loading",
                messageHash: hash,
            };
        }
        if (translation && !translation.showOriginal && translation.translatedText) {
            return {
                kind: "html",
                textForRender: translation.translatedText,
                singleEmoji:
                    translation.translatedText.length < 64 &&
                    MarkdownRenderer.isSingleEmojiMessage(translation.translatedText),
                showFooter: true,
                showOriginalLink: true,
                showTranslationLink: false,
                fromCode: translation.fromCode,
                toCode: translation.toCode,
                messageHash: hash,
            };
        }
        if (translation && translation.showOriginal) {
            return {
                kind: "html",
                textForRender: originalContent,
                singleEmoji: originalContent.length < 64 && MarkdownRenderer.isSingleEmojiMessage(originalContent),
                showFooter: true,
                showOriginalLink: false,
                showTranslationLink: true,
                fromCode: translation.fromCode,
                toCode: translation.toCode,
                messageHash: hash,
            };
        }
        return {
            kind: "html",
            textForRender: originalContent,
            singleEmoji: originalContent.length < 64 && MarkdownRenderer.isSingleEmojiMessage(originalContent),
            showFooter: false,
            messageHash: hash,
        };
    };

    const openRelayShareFromParsed = async (parsed: unknown) => {
        if (!parsed || typeof parsed !== "object") return;
        try {
            await applyRelayShareLink(parsed, { api: window.api });
            window.location.hash = "#/relay-chat";
        } catch {
            window.location.hash = "#/relay-chat";
        }
    };

    return {
        expandedMessageInfo: deps.expandedMessageInfo,
        audioAttachmentUrls: deps.audioAttachmentUrls || {},
        selectedPeer: deps.selectedPeer,
        canMergeImageIntoImageStrip: canUseImageStrip,
        imageGroupSortedChron: (items) =>
            items.slice().sort((a, b) => {
                const aTime = Number(
                    a.lxmf_message.timestamp || new Date(a.lxmf_message.created_at as string).getTime()
                );
                const bTime = Number(
                    b.lxmf_message.timestamp || new Date(b.lxmf_message.created_at as string).getTime()
                );
                return aTime - bTime;
            }),
        imageGroupGalleryUrls: (items) =>
            items
                .slice()
                .sort((a, b) => Number(a.lxmf_message.timestamp || 0) - Number(b.lxmf_message.timestamp || 0))
                .map((item) => imageDataUrl(item.lxmf_message) || lxmfImageUrl(item.lxmf_message.hash)),
        lxmfImageUrl,
        pendingOutboundImageSrc: (item) => imageDataUrl(item.lxmf_message) || lxmfImageUrl(item.lxmf_message.hash),
        openImage: deps.openImage,
        onOutboundImageClick: (item) =>
            deps.openImage(imageDataUrl(item.lxmf_message) || lxmfImageUrl(item.lxmf_message.hash), undefined, [item]),
        onChatItemClick: deps.onChatItemClick,
        onMessageContextMenu: deps.onMessageContextMenu,
        downloadMessageImage: (item) => void deps.downloadMessageImage(item),
        openReactionPicker: deps.openReactionPicker,
        reactionReactorLabel: (sender) => {
            const hash = String(sender || "");
            if (!hash) return "";
            if (hash.toLowerCase() === String(deps.myLxmfAddressHash || "").toLowerCase()) {
                return t("messages.reaction_you");
            }
            const peer = deps.selectedPeer;
            if (hash.toLowerCase() === String(peer?.destination_hash || "").toLowerCase()) {
                return peer?.custom_display_name || peer?.display_name || Utils.formatDestinationHash(hash);
            }
            const conversation = deps.conversations?.find(
                (item) => String(item.destination_hash || "").toLowerCase() === hash.toLowerCase()
            );
            return conversation?.custom_display_name || conversation?.display_name || Utils.formatDestinationHash(hash);
        },
        replyToMessage: deps.replyToMessage,
        retrySendingMessage: deps.retrySendingMessage,
        cancelSendingMessage: deps.cancelSendingMessage,
        deleteChatItem: deps.deleteChatItem,
        showRawMessage: deps.showRawMessage,
        scrollToMessage: deps.scrollToMessage,
        getRepliedMessage: (hash) =>
            deps.chatItems.find((item) => item.lxmf_message.hash === hash)?.lxmf_message || null,
        handleMessageClick: (event) => {
            handleRichHtmlLinkClick(event, {
                onNomadUrl: (url) => {
                    const [hash, ...pathParts] = url.split(":");
                    const path = pathParts.join(":");
                    const base = deps.isPopout ? "/popout/nomadnetwork" : "/nomadnetwork";
                    const query = path ? `?path=${encodeURIComponent(path)}` : "";
                    window.location.hash = `#${base}/${encodeURIComponent(hash)}${query}`;
                },
                onLxmfAddress: (address) => {
                    const base = deps.isPopout ? "/popout/messages" : "/messages";
                    window.location.hash = `#${base}/${encodeURIComponent(address)}`;
                },
                onGeo: (geoText) => {
                    void (async () => {
                        try {
                            const point = await resolveGeoText(geoText);
                            if (!point) {
                                ToastUtils.error(t("map.geo_parse_failed"));
                                return;
                            }
                            const params = new URLSearchParams({
                                lat: point.lat.toFixed(6),
                                lon: point.lon.toFixed(6),
                                zoom: "12",
                                label: String(geoText).trim(),
                            });
                            window.location.hash = `#/map?${params.toString()}`;
                        } catch {
                            ToastUtils.error(t("map.geo_parse_failed"));
                        }
                    })();
                },
                onRrcUrl: (uri) => {
                    openRelayShareFromParsed(parseRelayUri(uri));
                },
                openExternalHttp: (href) => {
                    const warnOnStranger = Boolean(
                        (GlobalState.config as { warn_on_stranger_links?: boolean } | undefined)?.warn_on_stranger_links
                    );
                    if (deps.isStrangerPeer && warnOnStranger) {
                        void DialogUtils.confirm(t("messages.stranger_link_open_confirm", { url: href })).then((ok) => {
                            if (ok) window.open(href, "_blank", "noopener,noreferrer");
                        });
                        return;
                    }
                    window.open(href, "_blank", "noopener,noreferrer");
                },
            });
        },
        setBubbleMessageShowOriginal: (hash, showOriginal) => {
            if (hash) {
                deps.onSetBubbleMessageShowOriginal?.(hash, Boolean(showOriginal));
            }
        },
        copyOversizedMessageBody: (item) => void deps.copyText(String(item.lxmf_message.content || "")),
        downloadLxmfFileAttachment: (item, index) => {
            const name = String(item.lxmf_message.fields?.file_attachments?.[index]?.file_name || "download");
            void deps.downloadLxmfFileAttachment(item, index, name);
        },
        addContact: (name, hash, lxmfAddress, lxstAddress, icon) =>
            void deps.addContact(name, hash, lxmfAddress, lxstAddress, icon),
        ingestPaperMessage: (paperMessage: unknown, hash?: string) => {
            if (typeof paperMessage === "string" && paperMessage) {
                WebSocketConnection.send(JSON.stringify({ type: "lxm.ingest_uri", uri: paperMessage }));
                ToastUtils.loading(t("messages.paper_message_ingest"), 2000);
            }
            if (hash) {
                markPaperMessageIngested(deps.identityKey, hash);
                deps.onPaperIngested?.(hash);
            }
        },
        openMapShareFromParsed: (parsed: unknown) => {
            if (!parsed || typeof parsed !== "object") return;
            const p = parsed as { lat?: number; lon?: number; zoom?: number; layers?: string; label?: string };
            const lat = Number(p.lat);
            const lon = Number(p.lon);
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
            const params = new URLSearchParams({
                lat: String(lat),
                lon: String(lon),
                zoom: String(Math.round(Number(p.zoom ?? 15))),
            });
            if (p.layers) params.set("layers", p.layers);
            if (p.label) params.set("label", p.label);
            window.location.hash = `#/map?${params.toString()}`;
        },
        copyMapShareUri: (uri) => {
            if (uri) {
                void deps.copyText(uri);
                ToastUtils.success(t("messages.map_link_copied"));
            }
        },
        openRelayShareFromParsed,
        copyRelayShareUri: (uri) => {
            if (uri) {
                void deps.copyText(uri);
                ToastUtils.success(t("common.copied"));
            }
        },
        viewLocationOnMap: (location: unknown) => {
            if (!location || typeof location !== "object") return;
            const loc = location as Record<string, unknown>;
            const lat = Number(loc.latitude ?? loc.lat);
            const lon = Number(loc.longitude ?? loc.lon);
            if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
            const params = new URLSearchParams({
                lat: String(lat),
                lon: String(lon),
                zoom: "15",
            });
            window.location.hash = `#/map?${params.toString()}`;
        },
        toggleTracking: async () => {
            const hash = deps.selectedPeer?.destination_hash;
            if (!hash) return;
            const current = Boolean(deps.selectedPeer?.is_tracking);
            const next = !current;
            try {
                const response = await window.api.post(`/api/v1/telemetry/tracking/${hash}/toggle`, {
                    is_tracking: next,
                });
                const data = response.data as { is_tracking?: boolean } | undefined;
                const isTracking = Boolean(data?.is_tracking ?? next);
                deps.onupdatePeerTracking?.({ destination_hash: hash, is_tracking: isTracking });
                ToastUtils.success(isTracking ? t("map.tracking_enabled") : t("map.tracking_disabled"));
            } catch {
                ToastUtils.error(t("map.failed_update_tracking"));
            }
        },
        bubbleViewModel,
        renderMarkdown: (text) => MarkdownRenderer.render(text || ""),
        getParsedItems: (item) => parseBasicItems(item, deps.conversations),
        formatTimeAgo: (value) => fromNow(value),
        formatDateDividerLabel: (value) => formatDate(value, "MMM D, YYYY"),
        formatAttachmentSize: attachmentSize,
        getMessageInfoLines: (message, isOutbound) => {
            const lines = [fromNow(message.created_at)];
            if (isOutbound && message.state) lines.push(outboundStateTitle(message.state));
            if (message.hash) lines.push(message.hash);
            return lines.filter(Boolean);
        },
        messageBodyCharCount: (item) => String(item.lxmf_message.content || "").length,
        bubbleMessageBodyFontSizePx: (model) =>
            Math.round((Number(deps.messageFontSize) || 14) * (model.singleEmoji ? 2.75 : 1)),
        bubbleStyles,
        isImageOnlyMessage: (item) =>
            isImageOnlyMessage(item as ChatItemLike, shouldHideAutoImageCaption as (item: ChatItemLike) => boolean),
        hasMessageBubble: (item) =>
            hasMessageBubble(item as ChatItemLike, shouldHideAutoImageCaption as (item: ChatItemLike) => boolean),
        hasFileAttachments,
        shouldHideAutoImageCaption,
        isMessageBodyTooLargeForDisplay: (item) =>
            String(item.lxmf_message.content || "").length > MESSAGE_BODY_MAX_DISPLAY_CHARS,
        isPaperMessageIngested: (item) => {
            const hash = item.lxmf_message.hash;
            return hash ? isPaperMessageIngested(deps.identityKey, hash) : false;
        },
        isThemeOutboundBubble: themedOutbound,
        isOutboundWaitingBubble: (item) => Boolean(item.is_outbound && item.lxmf_message._pendingPathfinding),
        isOutboundPendingForUi: pending,
        isOpportunisticDeferredDelivery,
        showRichOutboundPendingUi: pending,
        canCancelOutboundSend: (item) => Boolean(item.lxmf_message.hash && pending(item)),
        showOutboundTransferProgress: (message) => progress(message) > 0,
        outboundTransferProgressPercent: progress,
        outboundSendingProgressLabel: (message) => `${progress(message)}%`,
        outboundTransferStatsLabel: (message) => outboundTransferStatsLabel(message),
        outboundBubbleStatusIconName,
        outboundBubbleStatusTitle: (message) => {
            const key = outboundBubbleStatusTitleKey(message);
            return key ? t(key) : outboundStateTitle(message.state);
        },
        outboundBubbleStatusHoverTitle: (message) => outboundStateTitle(message.state),
        outboundBubbleFailedTitle: (message) => outboundStateTitle(message.state),
        outboundBubbleSurfaceClass: bubbleClass,
        outboundBubbleFooterTimeClass: (item) =>
            classForOutbound(item, "text-white/85", "text-sem-fg-muted", "text-sem-fg-muted"),
        outboundBubbleDeliveredIconClass: (item) => classForOutbound(item, "text-blue-200", "text-sem-fg-muted"),
        outboundBubbleSentCheckIconClass: (item) => classForOutbound(item, "text-white", "text-sem-fg-muted"),
        outboundBubblePendingCheckIconClass: (item) =>
            classForOutbound(item, "text-white opacity-50", "text-sem-fg-muted opacity-50"),
        outboundSendingStatusIconClass: (item) => classForOutbound(item, "text-white", "text-sem-fg-muted"),
        outboundExpandedActionsShellClass: (item) =>
            classForOutbound(
                item,
                "border-white/20 bg-white/10",
                "border-sem-border bg-sem-surface-muted",
                "border-sem-border bg-sem-surface-muted"
            ),
        outboundMessageMenuButtonClass: (item) =>
            classForOutbound(item, "text-white/90 hover:text-white", "text-sem-fg-muted", "text-sem-fg-muted"),
        outboundMessageMenuButtonHoverClass: (item) =>
            classForOutbound(item, "hover:bg-white/20", "hover:bg-sem-surface-muted", "hover:bg-sem-surface-muted"),
        outboundReplySnippetTitleClass: (item) =>
            classForOutbound(item, "text-white/80", "text-sem-fg-muted", "text-indigo-500/80"),
        outboundAttachmentCaptionClass: (item) =>
            classForOutbound(item, "text-white/85", "text-sem-fg-muted", "text-sem-fg-muted"),
        outboundEmbeddedCardClass: (item) =>
            classForOutbound(
                item,
                "bg-white/20 text-white border-white/20 hover:bg-white/30",
                "bg-sem-surface-muted text-sem-fg border-sem-border",
                ""
            ),
        outboundEmbeddedSecondaryTextClass: (item) => classForOutbound(item, "text-white/60", "text-sem-fg-muted", ""),
    };
}
