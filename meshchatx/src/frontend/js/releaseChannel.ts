/* SPDX-License-Identifier: 0BSD */
/**
 * Release channel helpers for About/sidebar badges and Testing/Beta prompts.
 */

export const PRODUCT_CHANNELS = Object.freeze(["testing", "beta", "stable", "local"] as const);

export type ProductChannel = (typeof PRODUCT_CHANNELS)[number];

export function normalizeReleaseChannel(raw: unknown): ProductChannel | string {
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

export function channelLabelKey(channel: unknown): string {
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

/** Tailwind classes for channel pill. */
export function channelBadgeClass(channel: unknown): string {
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

export type ChannelPromptAppInfo = {
    build_channel?: string;
    version?: string;
    display_version?: string;
    git_commit_short?: string;
    git_commit?: string;
    channel_prompt_seen?: string;
};

export function channelPromptSeenKey(appInfo: ChannelPromptAppInfo | null | undefined): string {
    const info = appInfo || {};
    const channel = normalizeReleaseChannel(info.build_channel);
    const version = String(info.display_version || info.version || "unknown").trim() || "unknown";
    const short =
        String(info.git_commit_short || "").trim() ||
        (info.git_commit ? String(info.git_commit).slice(0, 7) : "") ||
        "unknown";
    return `${channel}:${version}:${short}`;
}

export function shouldShowChannelPrompt(appInfo: ChannelPromptAppInfo | null | undefined): boolean {
    const info = appInfo || {};
    const channel = normalizeReleaseChannel(info.build_channel);
    if (channel !== "testing" && channel !== "beta") {
        return false;
    }
    const key = channelPromptSeenKey(info);
    const seen = String(info.channel_prompt_seen || "").trim();
    return seen !== key;
}

export type BugReportPrompt = {
    bug_report_lxmf?: string;
    bug_report_url?: string;
    [key: string]: unknown;
};

export type BugReportTarget = {
    kind: "lxmf" | "url" | "";
    value: string;
};

/** Prefer LXMF report destination. Optional http(s) URL is secondary. */
export function channelBugReportTarget(
    prompt: BugReportPrompt | Record<string, unknown> | null | undefined
): BugReportTarget {
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
