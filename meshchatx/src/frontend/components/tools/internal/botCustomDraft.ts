export interface CustomCommandDraft {
    name: string;
    response: string;
    description: string;
}

export interface CustomDraft {
    welcome: string;
    commands: CustomCommandDraft[];
}

export function defaultCustomDraft(): CustomDraft {
    return { welcome: "", commands: [] };
}

export function draftFromBotCustom(custom: any): CustomDraft {
    const draft = defaultCustomDraft();
    if (!custom || typeof custom !== "object") {
        return draft;
    }
    if (typeof custom.welcome === "string") {
        draft.welcome = custom.welcome;
    }
    if (Array.isArray(custom.commands)) {
        draft.commands = custom.commands
            .filter((c: any) => c && typeof c === "object" && c.name)
            .map((c: any) => ({
                name: String(c.name),
                response: String(c.response || ""),
                description: c.description ? String(c.description) : "",
            }));
    }
    return draft;
}

export function buildCustomPayload(draft: CustomDraft): Record<string, any> {
    const commands = (draft.commands || [])
        .map((c) => ({
            name: String(c.name || "").trim(),
            response: String(c.response || "").trim(),
            description: String(c.description || "").trim(),
        }))
        .filter((c) => c.name && c.response)
        .map((c) => {
            const out: Record<string, string> = { name: c.name, response: c.response };
            if (c.description) {
                out.description = c.description;
            }
            return out;
        });
    const payload: Record<string, any> = { commands };
    const welcome = String(draft.welcome || "").trim();
    if (welcome) {
        payload.welcome = welcome;
    }
    return payload;
}
