// SPDX-License-Identifier: 0BSD

/** Draft shapes and payload builders for bot template fields. */

export interface BotCustomCommandDraft {
    name: string;
    response: string;
    description: string;
}

export interface BotCustomDraft {
    welcome: string;
    commands: BotCustomCommandDraft[];
}

export interface BotCustomCommandPayload {
    name: string;
    response: string;
    description?: string;
}

export interface BotCustomPayload {
    commands: BotCustomCommandPayload[];
    welcome?: string;
}

export interface BotRrcDraft {
    hub: string;
    rooms: string;
    nick: string;
    mention_only: boolean;
    prefix: string;
    rate_seconds: string;
}

export interface BotRrcPayload {
    hub: string;
    rooms: string[];
    nick: string | null;
    mention_only: boolean;
    prefix: string;
    rate_seconds: number;
}

export function defaultCustomDraft(): BotCustomDraft {
    return { welcome: "", commands: [] };
}

export function draftFromBotCustom(custom: unknown): BotCustomDraft {
    const draft = defaultCustomDraft();
    if (!custom || typeof custom !== "object") {
        return draft;
    }
    const cfg = custom as { welcome?: unknown; commands?: unknown };
    if (typeof cfg.welcome === "string") {
        draft.welcome = cfg.welcome;
    }
    if (Array.isArray(cfg.commands)) {
        draft.commands = cfg.commands
            .filter((c) => c && typeof c === "object" && (c as { name?: unknown }).name)
            .map((c) => {
                const cmd = c as { name?: unknown; response?: unknown; description?: unknown };
                return {
                    name: String(cmd.name),
                    response: String(cmd.response || ""),
                    description: cmd.description ? String(cmd.description) : "",
                };
            });
    }
    return draft;
}

export function buildCustomPayload(draft: BotCustomDraft): BotCustomPayload {
    const commands = (draft.commands || [])
        .map((c) => ({
            name: String(c.name || "").trim(),
            response: String(c.response || "").trim(),
            description: String(c.description || "").trim(),
        }))
        .filter((c) => c.name && c.response)
        .map((c) => {
            const out: BotCustomCommandPayload = { name: c.name, response: c.response };
            if (c.description) {
                out.description = c.description;
            }
            return out;
        });
    const payload: BotCustomPayload = { commands };
    const welcome = String(draft.welcome || "").trim();
    if (welcome) {
        payload.welcome = welcome;
    }
    return payload;
}

export function defaultRrcDraft(): BotRrcDraft {
    return {
        hub: "",
        rooms: "",
        nick: "",
        mention_only: true,
        prefix: "!",
        rate_seconds: "8",
    };
}

export function draftFromBotRrc(rrc: unknown): BotRrcDraft {
    const draft = defaultRrcDraft();
    if (!rrc || typeof rrc !== "object") {
        return draft;
    }
    const cfg = rrc as {
        hub?: unknown;
        rooms?: unknown;
        nick?: unknown;
        mention_only?: unknown;
        prefix?: unknown;
        rate_seconds?: unknown;
    };
    if (cfg.hub) {
        draft.hub = String(cfg.hub);
    }
    if (Array.isArray(cfg.rooms)) {
        draft.rooms = cfg.rooms.join(", ");
    }
    if (cfg.nick) {
        draft.nick = String(cfg.nick);
    }
    if (cfg.mention_only !== undefined) {
        draft.mention_only = Boolean(cfg.mention_only);
    }
    if (cfg.prefix) {
        draft.prefix = String(cfg.prefix);
    }
    if (cfg.rate_seconds !== undefined && cfg.rate_seconds !== null) {
        draft.rate_seconds = String(cfg.rate_seconds);
    }
    return draft;
}

export function buildRrcPayload(draft: BotRrcDraft): BotRrcPayload {
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
