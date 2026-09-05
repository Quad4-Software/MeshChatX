/* SPDX-License-Identifier: 0BSD */
/**
 * Release channel helpers for About/sidebar badges and Testing/Beta prompts.
 */

export const PRODUCT_CHANNELS = Object.freeze(["testing", "beta", "stable", "local"]);

/**
 * @param {unknown} raw
 * @returns {"testing"|"beta"|"stable"|"local"|string}
 */
export function normalizeReleaseChannel(raw) {
    const c = String(raw || "")
        .trim()
        .toLowerCase();
    if (!c) {
        return "local";
    }
    if (c === "nightly" || c === "testing") {
        return "testing";
    }
    if (c === "preview" || c === "preview-dev" || c === "beta") {
        return "beta";
    }
    if (c === "release" || c === "stable") {
        return "stable";
    }
    if (c === "local") {
        return "local";
    }
    return c;
}

/**
 * @param {unknown} channel
 * @returns {string}
 */
export function channelLabelKey(channel) {
    const c = normalizeReleaseChannel(channel);
    if (c === "testing") {
        return "about.channel_testing";
    }
    if (c === "beta") {
        return "about.channel_beta";
    }
    if (c === "stable") {
        return "about.channel_stable";
    }
    if (c === "local") {
        return "about.channel_local";
    }
    return "about.channel_local";
}

/**
 * Tailwind classes for channel pill.
 * @param {unknown} channel
 * @returns {string}
 */
export function channelBadgeClass(channel) {
    const c = normalizeReleaseChannel(channel);
    if (c === "testing") {
        return "bg-amber-600 text-white";
    }
    if (c === "beta") {
        return "bg-sky-700 text-white";
    }
    if (c === "stable") {
        return "bg-emerald-700 text-white";
    }
    return "bg-zinc-600 text-white";
}

/**
 * @param {{ build_channel?: string, version?: string, display_version?: string, git_commit_short?: string, git_commit?: string }} appInfo
 * @returns {string}
 */
export function channelPromptSeenKey(appInfo) {
    const info = appInfo || {};
    const channel = normalizeReleaseChannel(info.build_channel);
    const version = String(info.display_version || info.version || "unknown").trim() || "unknown";
    const short =
        String(info.git_commit_short || "").trim() ||
        (info.git_commit ? String(info.git_commit).slice(0, 7) : "") ||
        "unknown";
    return `${channel}:${version}:${short}`;
}

/**
 * @param {{ build_channel?: string, channel_prompt_seen?: string } & object} appInfo
 * @returns {boolean}
 */
export function shouldShowChannelPrompt(appInfo) {
    const info = appInfo || {};
    const channel = normalizeReleaseChannel(info.build_channel);
    if (channel !== "testing" && channel !== "beta") {
        return false;
    }
    const key = channelPromptSeenKey(info);
    const seen = String(info.channel_prompt_seen || "").trim();
    return seen !== key;
}

/**
 * Prefer LXMF report destination. Optional http(s) URL is secondary.
 * @param {{ bug_report_lxmf?: string, bug_report_url?: string }} prompt
 * @returns {{ kind: "lxmf"|"url"|"", value: string }}
 */
export function channelBugReportTarget(prompt) {
    const p = prompt && typeof prompt === "object" ? prompt : {};
    const lxmf = typeof p.bug_report_lxmf === "string" ? p.bug_report_lxmf.trim() : "";
    if (lxmf) {
        return { kind: "lxmf", value: lxmf };
    }
    const url = typeof p.bug_report_url === "string" ? p.bug_report_url.trim() : "";
    if (url) {
        return { kind: "url", value: url };
    }
    return { kind: "", value: "" };
}
