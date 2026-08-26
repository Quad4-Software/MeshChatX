// SPDX-License-Identifier: 0BSD

export function defaultLxmfConfigDraft() {
    return {
        propagation_mode: "inherit",
        propagation_node: "",
        propagation_fallback_enabled: "inherit",
        direct_delivery_retries: "",
        opportunistic_sending: "inherit",
        announce_interval_seconds: "",
        stamp_cost: "",
    };
}

export function draftFromBotLxmfConfig(lxmfConfig) {
    const draft = defaultLxmfConfigDraft();
    const cfg = lxmfConfig && typeof lxmfConfig === "object" ? lxmfConfig : {};
    if (cfg.propagation_mode) {
        draft.propagation_mode = cfg.propagation_mode;
    }
    if (cfg.propagation_node) {
        draft.propagation_node = cfg.propagation_node;
    }
    if (cfg.propagation_fallback_enabled === true || cfg.propagation_fallback_enabled === false) {
        draft.propagation_fallback_enabled = cfg.propagation_fallback_enabled ? "true" : "false";
    }
    if (cfg.direct_delivery_retries !== undefined && cfg.direct_delivery_retries !== null) {
        draft.direct_delivery_retries = String(cfg.direct_delivery_retries);
    }
    if (cfg.opportunistic_sending === true || cfg.opportunistic_sending === false) {
        draft.opportunistic_sending = cfg.opportunistic_sending ? "true" : "false";
    }
    if (cfg.announce_interval_seconds !== undefined && cfg.announce_interval_seconds !== null) {
        draft.announce_interval_seconds = String(cfg.announce_interval_seconds);
    }
    if (cfg.stamp_cost !== undefined && cfg.stamp_cost !== null) {
        draft.stamp_cost = String(cfg.stamp_cost);
    }
    return draft;
}

export function buildLxmfConfigPatch(draft, options = {}) {
    const clearEmpty = Boolean(options.clearEmpty);
    const patch = {};
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

    const fallback = draft.propagation_fallback_enabled;
    if (fallback === "true") {
        patch.propagation_fallback_enabled = true;
    } else if (fallback === "false") {
        patch.propagation_fallback_enabled = false;
    } else if (clearEmpty && fallback === "inherit") {
        patch.propagation_fallback_enabled = null;
    }

    const retries = String(draft.direct_delivery_retries ?? "").trim();
    if (retries) {
        patch.direct_delivery_retries = Number(retries);
    } else if (clearEmpty) {
        patch.direct_delivery_retries = null;
    }

    const opportunistic = draft.opportunistic_sending;
    if (opportunistic === "true") {
        patch.opportunistic_sending = true;
    } else if (opportunistic === "false") {
        patch.opportunistic_sending = false;
    } else if (clearEmpty && opportunistic === "inherit") {
        patch.opportunistic_sending = null;
    }

    const announce = String(draft.announce_interval_seconds ?? "").trim();
    if (announce) {
        patch.announce_interval_seconds = Number(announce);
    } else if (clearEmpty) {
        patch.announce_interval_seconds = null;
    }

    const stamp = String(draft.stamp_cost ?? "").trim();
    if (stamp) {
        patch.stamp_cost = Number(stamp);
    } else if (clearEmpty) {
        patch.stamp_cost = null;
    }

    return patch;
}
