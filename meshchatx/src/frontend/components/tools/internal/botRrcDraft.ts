export interface RrcDraft {
    hub: string;
    rooms: string;
    nick: string;
    mention_only: boolean;
    prefix: string;
    rate_seconds: string;
}

export function defaultRrcDraft(): RrcDraft {
    return {
        hub: "",
        rooms: "",
        nick: "",
        mention_only: true,
        prefix: "!",
        rate_seconds: "8",
    };
}

export function draftFromBotRrc(rrc: any): RrcDraft {
    const draft = defaultRrcDraft();
    if (!rrc || typeof rrc !== "object") {
        return draft;
    }
    if (rrc.hub) {
        draft.hub = String(rrc.hub);
    }
    if (Array.isArray(rrc.rooms)) {
        draft.rooms = rrc.rooms.join(", ");
    }
    if (rrc.nick) {
        draft.nick = String(rrc.nick);
    }
    if (rrc.mention_only !== undefined) {
        draft.mention_only = Boolean(rrc.mention_only);
    }
    if (rrc.prefix) {
        draft.prefix = String(rrc.prefix);
    }
    if (rrc.rate_seconds !== undefined && rrc.rate_seconds !== null) {
        draft.rate_seconds = String(rrc.rate_seconds);
    }
    return draft;
}

export function buildRrcPayload(draft: RrcDraft): Record<string, any> {
    const rooms = String(draft.rooms || "")
        .split(",")
        .map((r) => r.trim().replace(/^#+/, ""))
        .filter(Boolean);
    return {
        hub: String(draft.hub || "")
            .trim()
            .toLowerCase(),
        rooms,
        nick: String(draft.nick || "").trim() || null,
        mention_only: Boolean(draft.mention_only),
        prefix: String(draft.prefix || "!"),
        rate_seconds: Math.max(0, Math.min(3600, Number(draft.rate_seconds) || 8)),
    };
}
