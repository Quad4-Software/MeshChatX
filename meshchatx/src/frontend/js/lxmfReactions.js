/**
 * Columba-compatible LXMF field-16 reactions: merge reaction rows onto parent messages.
 */

export const COLUMBA_REACTION_EMOJIS = [
    "\u{1F44D}",
    "\u2764\uFE0F",
    "\u{1F602}",
    "\u{1F62E}",
    "\u{1F622}",
    "\u{1F621}",
];

function reactionEmojiFromLxmfMessageFields(fields) {
    if (!fields || typeof fields !== "object") {
        return "";
    }
    const app = fields.app_extensions;
    if (app && typeof app === "object" && app.reaction_to) {
        return typeof app.emoji === "string" ? app.emoji : "";
    }
    return "";
}

/**
 * One-line preview for conversation list / sidebar (plain text or i18n via `t`).
 */
export function lxmfConversationListPreview(msg, { myLxmfAddressHash, peerDisplayName, t }) {
    const raw = msg?.content;
    const content = typeof raw === "string" ? raw.trim() : "";
    if (content) {
        return raw;
    }

    const emoji =
        (msg?.is_reaction && typeof msg?.reaction_emoji === "string" && msg.reaction_emoji) ||
        reactionEmojiFromLxmfMessageFields(msg?.fields);
    if (!emoji) {
        return raw ?? "";
    }

    const incoming = Boolean(msg?.is_incoming);
    const src = String(msg?.source_hash || "").toLowerCase();
    const me = String(myLxmfAddressHash || "").toLowerCase();
    const reactorIsYou = !incoming && me && src === me;

    let name;
    if (incoming) {
        name = peerDisplayName || "Anonymous Peer";
    } else if (reactorIsYou) {
        name = typeof t === "function" ? t("messages.reaction_you") : "You";
    } else {
        name = peerDisplayName || "Anonymous Peer";
    }

    if (typeof t === "function") {
        return t("messages.conversation_reaction_preview", { name, emoji });
    }
    return `${name} reacted ${emoji}`;
}

export function mergeLxmfReactionRowsIntoMessages(messages) {
    if (!Array.isArray(messages) || messages.length === 0) {
        return messages;
    }
    const parents = [];
    const reactions = [];
    for (const m of messages) {
        if (!m) {
            continue;
        }
        if (m.is_reaction) {
            reactions.push(m);
        } else {
            parents.push({ ...m, reactions: [] });
        }
    }
    const byHash = new Map(parents.map((p) => [p.hash, p]));
    for (const r of reactions) {
        const targetId = r.reaction_to;
        if (!targetId) {
            continue;
        }
        const parent = byHash.get(targetId);
        if (!parent) {
            continue;
        }
        const sender = r.reaction_sender || r.source_hash || "";
        const emoji = r.reaction_emoji || "";
        const dup = parent.reactions.some((x) => x.sender === sender && x.emoji === emoji);
        if (!dup) {
            parent.reactions.push({
                emoji,
                sender,
                reactionHash: r.hash,
            });
        }
    }
    return parents;
}
