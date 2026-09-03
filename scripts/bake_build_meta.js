/**
 * Bake git commit and build channel into meshchatx/src/_build_meta_baked.py
 * (gitignored). meshchatx.src.build_meta imports that overlay when present.
 *
 * Invoked from scripts/sync_version.js (pnpm run version:sync / build).
 *
 * Channel detection (first match wins):
 *   MESHCHATX_BUILD_CHANNEL env (normalized to product channel)
 *   GITHUB_REF_NAME / GITHUB_REF (nightly-*, testing-*, beta-*, preview-*, vX.Y.Z)
 *   default: local (is_dev)
 *
 * Product channels: testing, beta, stable, local.
 * Dev channels (testing, beta, local) set IS_DEV_BUILD.
 * Stable tags (vX.Y.Z) clear IS_DEV_BUILD.
 *
 * Also bakes release/channel_prompt.json as CHANNEL_PROMPT_JSON.
 */

const fs = require("fs");
const path = require("path");
const { execFileSync } = require("child_process");

const root = path.resolve(__dirname, "..");
const metaPath = path.join(root, "meshchatx", "src", "_build_meta_baked.py");
const promptPath = path.join(root, "release", "channel_prompt.json");

const DEFAULT_PROMPT = {
    bug_report_lxmf: "f489752fbef161c64d65e385a4e9fc74",
    bug_report_url: "",
    bug_report_steps: [
        "Send an LXMF message to f489752fbef161c64d65e385a4e9fc74",
        "Include version, channel, and git commit from About",
        "Describe steps to reproduce and expected vs actual",
        "Attach logs and screenshots if needed",
        "Note platform: Electron, Android, or self-host",
    ],
    focus_areas: [],
    notes: "",
};

function envTrim(name) {
    const v = process.env[name];
    return typeof v === "string" ? v.trim() : "";
}

function git(args) {
    try {
        return execFileSync("git", args, {
            cwd: root,
            encoding: "utf8",
            stdio: ["ignore", "pipe", "ignore"],
        }).trim();
    } catch {
        return "";
    }
}

function resolveCommit() {
    const fromEnv = envTrim("MESHCHATX_GIT_COMMIT") || envTrim("GIT_COMMIT") || envTrim("GITHUB_SHA");
    if (fromEnv) {
        return fromEnv;
    }
    return git(["rev-parse", "HEAD"]);
}

function shortCommit(full) {
    if (!full) {
        return "";
    }
    if (/^[0-9a-f]{7,40}$/i.test(full)) {
        return full.slice(0, 7).toLowerCase();
    }
    const fromGit = git(["rev-parse", "--short=7", "HEAD"]);
    return fromGit || full.slice(0, 7);
}

function refName() {
    return (
        envTrim("MESHCHATX_BUILD_REF") ||
        envTrim("GITHUB_REF_NAME") ||
        envTrim("GITHUB_REF").replace(/^refs\/(heads|tags)\//, "")
    );
}

function normalizeChannel(raw) {
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

function resolveChannel(ref) {
    const forced = envTrim("MESHCHATX_BUILD_CHANNEL");
    if (forced) {
        return normalizeChannel(forced);
    }
    if (!ref) {
        return "local";
    }
    if (ref.startsWith("nightly-") || ref.startsWith("testing-")) {
        return "testing";
    }
    if (ref.startsWith("preview-dev-") || ref.startsWith("preview-") || ref.startsWith("beta-")) {
        return "beta";
    }
    if (/^v\d+\.\d+\.\d+/.test(ref)) {
        return "stable";
    }
    return "local";
}

function isDevChannel(channel) {
    return channel !== "stable";
}

function loadChannelPrompt() {
    try {
        if (!fs.existsSync(promptPath)) {
            return { ...DEFAULT_PROMPT };
        }
        const parsed = JSON.parse(fs.readFileSync(promptPath, "utf8"));
        if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
            return { ...DEFAULT_PROMPT };
        }
        return {
            bug_report_lxmf:
                typeof parsed.bug_report_lxmf === "string" && parsed.bug_report_lxmf.trim()
                    ? parsed.bug_report_lxmf.trim().toLowerCase()
                    : DEFAULT_PROMPT.bug_report_lxmf,
            bug_report_url: typeof parsed.bug_report_url === "string" ? parsed.bug_report_url.trim() : "",
            bug_report_steps: Array.isArray(parsed.bug_report_steps)
                ? parsed.bug_report_steps.map((s) => String(s)).filter(Boolean)
                : [...DEFAULT_PROMPT.bug_report_steps],
            focus_areas: Array.isArray(parsed.focus_areas)
                ? parsed.focus_areas.map((s) => String(s)).filter(Boolean)
                : [],
            notes: typeof parsed.notes === "string" ? parsed.notes : "",
        };
    } catch {
        return { ...DEFAULT_PROMPT };
    }
}

function pyString(value) {
    return JSON.stringify(String(value ?? ""));
}

function bake() {
    const commit = resolveCommit();
    const short = shortCommit(commit);
    const ref = refName();
    const channel = resolveChannel(ref);
    const isDev = isDevChannel(channel);
    const prompt = loadChannelPrompt();
    const promptJson = JSON.stringify(prompt);

    const content = `# SPDX-License-Identifier: 0BSD
"""Generated by scripts/bake_build_meta.js. Do not commit."""

GIT_COMMIT = ${pyString(commit)}
GIT_COMMIT_SHORT = ${pyString(short)}
BUILD_CHANNEL = ${pyString(channel)}
IS_DEV_BUILD = ${isDev ? "True" : "False"}
CHANNEL_PROMPT_JSON = ${pyString(promptJson)}
`;

    const prev = fs.existsSync(metaPath) ? fs.readFileSync(metaPath, "utf8") : null;
    if (prev !== content) {
        fs.writeFileSync(metaPath, content, "utf8");
        console.log(`Baked build_meta channel=${channel} is_dev=${isDev} commit=${short || "unknown"}`);
    } else {
        console.log(`build_meta unchanged channel=${channel} is_dev=${isDev} commit=${short || "unknown"}`);
    }
}

bake();
