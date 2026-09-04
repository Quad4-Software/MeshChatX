/* SPDX-License-Identifier: 0BSD */
/**
 * Channel / commit bake oracles for scripts/bake_build_meta.js
 */
import { describe, it, expect, afterEach } from "vitest";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const bakeScript = path.join(repoRoot, "scripts", "bake_build_meta.js");
const bakedPath = path.join(repoRoot, "meshchatx", "src", "_build_meta_baked.py");

function readBaked() {
    const text = fs.readFileSync(bakedPath, "utf8");
    const commit = (text.match(/^GIT_COMMIT = "(.*)"$/m) || [])[1] ?? "";
    const short = (text.match(/^GIT_COMMIT_SHORT = "(.*)"$/m) || [])[1] ?? "";
    const channel = (text.match(/^BUILD_CHANNEL = "(.*)"$/m) || [])[1] ?? "";
    const isDev = /^IS_DEV_BUILD = True$/m.test(text);
    return { commit, short, channel, isDev, text };
}

function runBake(envOverrides) {
    const env = { ...process.env, ...envOverrides };
    for (const key of Object.keys(envOverrides)) {
        if (envOverrides[key] === "" || envOverrides[key] == null) {
            delete env[key];
        }
    }
    const result = spawnSync(process.execPath, [bakeScript], {
        cwd: repoRoot,
        env,
        encoding: "utf8",
    });
    expect(result.status, result.stderr || result.stdout).toBe(0);
    return readBaked();
}

describe("bake_build_meta channel oracles", () => {
    let previous = null;

    afterEach(() => {
        if (previous != null) {
            fs.writeFileSync(bakedPath, previous, "utf8");
            previous = null;
        } else if (fs.existsSync(bakedPath)) {
            // leave whatever last bake wrote; file is gitignored
        }
    });

    function snapshot() {
        if (fs.existsSync(bakedPath)) {
            previous = fs.readFileSync(bakedPath, "utf8");
        }
    }

    it("nightly ref bakes testing with short sha and prompt", () => {
        snapshot();
        const meta = runBake({
            MESHCHATX_BUILD_CHANNEL: "",
            GITHUB_REF_NAME: "nightly-2026.07.24-abcdef0",
            GITHUB_SHA: "abcdef0123456789aaaa",
            MESHCHATX_GIT_COMMIT: "",
            GIT_COMMIT: "",
        });
        expect(meta.channel).toBe("testing");
        expect(meta.isDev).toBe(true);
        expect(meta.short).toBe("abcdef0");
        expect(meta.commit.startsWith("abcdef0")).toBe(true);
        expect(meta.text, meta.text.slice(0, 400)).toContain("CHANNEL_PROMPT_JSON");
        expect(meta.text).toContain("bug_report_url");
    });

    it("beta tag bakes beta channel", () => {
        snapshot();
        const meta = runBake({
            MESHCHATX_BUILD_CHANNEL: "",
            GITHUB_REF_NAME: "beta-2026.09.02-deadbee",
            GITHUB_SHA: "deadbeefcafebabe",
            MESHCHATX_GIT_COMMIT: "",
            GIT_COMMIT: "",
        });
        expect(meta.channel).toBe("beta");
        expect(meta.isDev).toBe(true);
    });

    it("stable tag clears is_dev", () => {
        snapshot();
        const meta = runBake({
            MESHCHATX_BUILD_CHANNEL: "",
            GITHUB_REF_NAME: "v4.8.0",
            GITHUB_SHA: "deadbeefcafebabe",
            MESHCHATX_GIT_COMMIT: "",
            GIT_COMMIT: "",
        });
        expect(meta.channel).toBe("stable");
        expect(meta.isDev).toBe(false);
        expect(meta.short).toBe("deadbee");
    });

    it("explicit MESHCHATX_BUILD_CHANNEL=stable wins over nightly ref name", () => {
        snapshot();
        const meta = runBake({
            MESHCHATX_BUILD_CHANNEL: "stable",
            GITHUB_REF_NAME: "nightly-2026.07.24-abcdef0",
            MESHCHATX_GIT_COMMIT: "1234567890abcdef",
        });
        expect(meta.channel).toBe("stable");
        expect(meta.isDev).toBe(false);
        expect(meta.short).toBe("1234567");
    });

    it("legacy release env normalizes to stable", () => {
        snapshot();
        const meta = runBake({
            MESHCHATX_BUILD_CHANNEL: "release",
            GITHUB_REF_NAME: "nightly-2026.07.24-abcdef0",
            MESHCHATX_GIT_COMMIT: "1234567890abcdef",
        });
        expect(meta.channel).toBe("stable");
        expect(meta.isDev).toBe(false);
    });

    it("local/default channel is treated as dev", () => {
        snapshot();
        const meta = runBake({
            MESHCHATX_BUILD_CHANNEL: "local",
            GITHUB_REF_NAME: "",
            GITHUB_REF: "",
            MESHCHATX_GIT_COMMIT: "feedface00",
        });
        expect(meta.channel).toBe("local");
        expect(meta.isDev).toBe(true);
        expect(meta.short).toBe("feedfac");
    });
});
