// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { detectLaunchEditor, envFlagEnabled } from "../../scripts/vite-dx.mjs";

const ROOT = resolve(import.meta.dirname, "../..");

describe("vite-dx and Vite serve config", () => {
    it("envFlagEnabled accepts 1/true/yes only", () => {
        expect(envFlagEnabled("1")).toBe(true);
        expect(envFlagEnabled("true")).toBe(true);
        expect(envFlagEnabled("YES")).toBe(true);
        expect(envFlagEnabled("0")).toBe(false);
        expect(envFlagEnabled("")).toBe(false);
        expect(envFlagEnabled(undefined)).toBe(false);
    });

    it("detectLaunchEditor prefers LAUNCH_EDITOR then code", () => {
        expect(detectLaunchEditor({ LAUNCH_EDITOR: "webstorm" })).toBe("webstorm");
        expect(detectLaunchEditor({})).toBe("code");
    });

    it("vite.config.js is Svelte-only with localhost serve defaults", () => {
        const vite = readFileSync(resolve(ROOT, "vite.config.js"), "utf8");
        expect(vite).not.toContain("vite-plugin-vue-devtools");
        expect(vite).not.toContain("@vitejs/plugin-vue");
        expect(vite).not.toContain('from "vue"');
        expect(vite).toContain("@sveltejs/vite-plugin-svelte");
        expect(vite).toContain("sourcemap: false");
        expect(vite).toContain("devSourcemap: true");
        expect(vite).toContain('host: "127.0.0.1"');
        expect(vite).toContain("strictPort: true");
        expect(vite).toContain("clearScreen: false");
        expect(vite).toContain('forwardConsole: command === "serve"');
        expect(vite).toContain("tsconfigPaths: true");
        expect(vite).toContain('"micron-parser"');
        expect(vite).toContain("MESHCHAT_VITE_BUNDLED_DEV");
        expect(vite).toContain("bundledDev: true");
    });

    it("Docker frontend stages copy every vite.config.js scripts/ import", () => {
        const vite = readFileSync(resolve(ROOT, "vite.config.js"), "utf8");
        const imports = [...vite.matchAll(/from\s+"(\.\/scripts\/[^"]+)"/g)].map((m) => m[1].replace(/^\.\//, ""));
        expect(imports.length).toBeGreaterThan(0);
        expect(imports).not.toContain("scripts/vite-dx.mjs");
        for (const dockerfile of ["docker/Dockerfile", "docker/Dockerfile.hardened"]) {
            const body = readFileSync(resolve(ROOT, dockerfile), "utf8");
            const frontendStage = body.split(/^FROM /m)[1] || "";
            for (const rel of imports) {
                expect(frontendStage, `${dockerfile} missing COPY ${rel}`).toContain(`COPY ${rel} ${rel}`);
            }
        }
    });

    it("Vite proxy forwards Host and task stacks trust loopback for WS Origin", () => {
        const vite = readFileSync(resolve(ROOT, "vite.config.js"), "utf8");
        expect(vite).toContain("X-Forwarded-Host");
        expect(vite).toContain("setForwardedHost");
        expect(vite).toContain("xfwd: true");
        const devLocal = readFileSync(resolve(ROOT, "scripts/dev-local.sh"), "utf8");
        expect(devLocal).toContain("MESHCHAT_TRUSTED_PROXIES");
        expect(devLocal).toContain("127.0.0.1/32");
        const e2e = readFileSync(resolve(ROOT, "scripts/e2e/start-e2e-stack.sh"), "utf8");
        expect(e2e).toContain("MESHCHAT_TRUSTED_PROXIES");
        expect(e2e).toContain("127.0.0.1/32");
    });

    it("Vite CORS allows opaque null Origin for the Nomad crash-tab sandbox", () => {
        const vite = readFileSync(resolve(ROOT, "vite.config.js"), "utf8");
        expect(vite).toContain('origin === "null"');
        expect(vite).toContain("nomad-crash-tab");
        expect(vite).not.toContain("skipVueDevToolsInCrashTab");
    });

    it("package.json does not list Vue packages", () => {
        const pkg = JSON.parse(readFileSync(resolve(ROOT, "package.json"), "utf8"));
        expect(pkg.dependencies?.vue).toBeUndefined();
        expect(pkg.dependencies?.["vue-router"]).toBeUndefined();
        expect(pkg.dependencies?.["vue-i18n"]).toBeUndefined();
        expect(pkg.devDependencies?.["vite-plugin-vue-devtools"]).toBeUndefined();
        expect(pkg.devDependencies?.["@vitejs/plugin-vue"]).toBeUndefined();
        expect(pkg.devDependencies?.["vue-tsc"]).toBeUndefined();
        expect(pkg.devDependencies?.["@vue/test-utils"]).toBeUndefined();
    });

    it("debugpy in task debug binds 127.0.0.1 only", () => {
        const dev = readFileSync(resolve(ROOT, "scripts/dev-local.sh"), "utf8");
        expect(dev).toContain('debugpy --listen "127.0.0.1:${dbg_port}"');
        expect(dev).not.toContain("--listen 0.0.0.0");
        expect(dev).toContain("MESHCHAT_DEBUGPY");
        const taskfile = readFileSync(resolve(ROOT, "Taskfile.yml"), "utf8");
        expect(taskfile).toContain("MESHCHAT_DEBUGPY=1 bash scripts/dev-local.sh");
    });

    it("debugger launch configs attach debugpy on localhost and Chrome to Vite", () => {
        const launch = JSON.parse(readFileSync(resolve(ROOT, ".vscode/launch.json"), "utf8"));
        const names = launch.configurations.map((c) => c.name);
        expect(names).toContain("Backend: Attach debugpy");
        expect(names).toContain("Frontend: Chrome (Vite)");
        const attach = launch.configurations.find((c) => c.name === "Backend: Attach debugpy");
        expect(attach.connect).toEqual({ host: "127.0.0.1", port: 5678 });
        const chrome = launch.configurations.find((c) => c.name === "Frontend: Chrome (Vite)");
        expect(chrome.url).toBe("http://127.0.0.1:5173");
        const compound = launch.compounds.find((c) => c.name === "MeshChatX: Vite + Python");
        expect(compound.preLaunchTask).toBe("meshchatx: debug");
    });
});
