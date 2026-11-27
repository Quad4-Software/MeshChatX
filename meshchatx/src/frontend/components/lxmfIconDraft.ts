const DEFAULT_FG = "#6b7280";
const DEFAULT_BG = "#e5e7eb";

export interface BotIconDraft {
    icon_name: string;
    fg_color: string;
    bg_color: string;
}

export function defaultBotIconDraft(spec: any = "robot"): BotIconDraft {
    if (spec && typeof spec === "object") {
        return {
            icon_name: spec.icon_name || "robot",
            fg_color: spec.fg_color || DEFAULT_FG,
            bg_color: spec.bg_color || DEFAULT_BG,
        };
    }
    return {
        icon_name: spec || "robot",
        fg_color: DEFAULT_FG,
        bg_color: DEFAULT_BG,
    };
}
