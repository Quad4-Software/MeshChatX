// SPDX-License-Identifier: 0BSD

// Tri-state select values: "inherit" clears the override, "true"/"false" set it.
const TRI_STATE_KEYS = [
    "propagation_fallback_enabled",
    "opportunistic_sending",
    "announce_enabled",
    "announce_immediately",
    "first_message_enabled",
    "lxmf_commands_enabled",
    "signature_verification_enabled",
    "require_message_signatures",
    "require_stamps",
    "request_unknown_identities",
    "identity_pinning_enabled",
    "permissions_enabled",
    "message_persistence_enabled",
] as const;

// Free-form numeric fields kept as strings in the draft.
const NUMERIC_KEYS = [
    "direct_delivery_retries",
    "announce_interval_seconds",
    "stamp_cost",
    "rate_limit",
    "cooldown",
    "max_warnings",
    "warning_timeout",
    "message_queue_size",
    "autopeer_maxdepth",
] as const;

export type LxmfTriStateKey = (typeof TRI_STATE_KEYS)[number];
export type LxmfNumericKey = (typeof NUMERIC_KEYS)[number];

export type LxmfConfigDraft = {
    propagation_mode: string;
    propagation_node: string;
    command_prefix: string;
    admins: string;
} & Record<LxmfTriStateKey | LxmfNumericKey, string>;

/** Looser draft shape accepted by buildLxmfConfigPatch (all fields optional). */
export type LxmfConfigDraftInput = {
    propagation_mode?: string;
    propagation_node?: string;
    command_prefix?: string;
    admins?: string;
} & Partial<Record<LxmfTriStateKey | LxmfNumericKey, string>>;

export type BotLxmfConfig = {
    propagation_mode?: string;
    propagation_node?: string;
    command_prefix?: string | null;
    admins?: string[] | null;
} & Partial<Record<LxmfTriStateKey, boolean | null>> &
    Partial<Record<LxmfNumericKey, number | null>>;

export type LxmfConfigPatch = {
    propagation_mode?: string;
    propagation_node?: string | null;
    command_prefix?: string | null;
    admins?: string[] | null;
} & Partial<Record<LxmfTriStateKey, boolean | null>> &
    Partial<Record<LxmfNumericKey, number | null>>;

export function defaultLxmfConfigDraft(): LxmfConfigDraft {
    const draft = {
        propagation_mode: "inherit",
        propagation_node: "",
        command_prefix: "",
        admins: "",
    } as LxmfConfigDraft;
    for (const key of TRI_STATE_KEYS) {
        draft[key] = "inherit";
    }
    for (const key of NUMERIC_KEYS) {
        draft[key] = "";
    }
    return draft;
}

export function draftFromBotLxmfConfig(lxmfConfig: BotLxmfConfig | null | undefined): LxmfConfigDraft {
    const draft = defaultLxmfConfigDraft();
    const cfg: BotLxmfConfig = lxmfConfig && typeof lxmfConfig === "object" ? lxmfConfig : {};
    if (cfg.propagation_mode) {
        draft.propagation_mode = cfg.propagation_mode;
    }
    if (cfg.propagation_node) {
        draft.propagation_node = cfg.propagation_node;
    }
    for (const key of TRI_STATE_KEYS) {
        if (cfg[key] === true || cfg[key] === false) {
            draft[key] = cfg[key] ? "true" : "false";
        }
    }
    for (const key of NUMERIC_KEYS) {
        if (cfg[key] !== undefined && cfg[key] !== null) {
            draft[key] = String(cfg[key]);
        }
    }
    if (cfg.command_prefix !== undefined && cfg.command_prefix !== null) {
        draft.command_prefix = String(cfg.command_prefix);
    }
    if (Array.isArray(cfg.admins)) {
        draft.admins = cfg.admins.join("\n");
    }
    return draft;
}

export function parseAdminsDraft(raw: string | null | undefined): string[] {
    return String(raw || "")
        .split(/[\s,;]+/)
        .map((h) => h.trim().toLowerCase().replace(/[<>]/g, ""))
        .filter((h) => /^[0-9a-f]{32}$/.test(h));
}

export function buildLxmfConfigPatch(
    draft: LxmfConfigDraftInput,
    options: { clearEmpty?: boolean } = {}
): LxmfConfigPatch {
    const clearEmpty = Boolean(options.clearEmpty);
    const patch: LxmfConfigPatch = {};
    const mode = (draft.propagation_mode || "inherit").trim();
    if (mode && mode !== "inherit") {
        patch.propagation_mode = mode;
    } else if (clearEmpty && mode === "inherit") {
        patch.propagation_mode = "inherit";
    }

    const node = (draft.propagation_node || "").trim().toLowerCase();
    if (mode === "manual" && node) {
        patch.propagation_node = node;
    } else if (clearEmpty && mode !== "manual") {
        patch.propagation_node = null;
    }

    for (const key of TRI_STATE_KEYS) {
        const value = draft[key];
        if (value === "true") {
            patch[key] = true;
        } else if (value === "false") {
            patch[key] = false;
        } else if (clearEmpty && value === "inherit") {
            patch[key] = null;
        }
    }

    for (const key of NUMERIC_KEYS) {
        const value = String(draft[key] ?? "").trim();
        if (value) {
            patch[key] = Number(value);
        } else if (clearEmpty) {
            patch[key] = null;
        }
    }

    const prefix = String(draft.command_prefix ?? "");
    if (prefix !== "") {
        patch.command_prefix = prefix;
    } else if (clearEmpty) {
        patch.command_prefix = null;
    }

    const admins = parseAdminsDraft(draft.admins);
    if (admins.length > 0) {
        patch.admins = admins;
    } else if (clearEmpty) {
        patch.admins = null;
    }

    return patch;
}
