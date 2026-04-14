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
