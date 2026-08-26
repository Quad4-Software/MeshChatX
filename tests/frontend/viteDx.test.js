// SPDX-License-Identifier: 0BSD

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { detectLaunchEditor, envFlagEnabled, isVueDevToolsEnabled } from "../../scripts/vite-dx.mjs";

const ROOT = resolve(import.meta.dirname, "../..");

describe("vite-dx Vue DevTools gate", () => {
    it("oracle: only vite serve enables DevTools by default", () => {
        const cases = [
            { command: "serve", env: {}, expected: true },
            { command: "build", env: {}, expected: false },
            { command: "serve", env: { VITEST: "true" }, expected: false },
            { command: "serve", env: { MESHCHAT_VUE_DEVTOOLS: "0" }, expected: false },
            { command: "serve", env: { MESHCHAT_VUE_DEVTOOLS: "false" }, expected: false },
            { command: "serve", env: { MESHCHAT_VUE_DEVTOOLS: "1" }, expected: true },
            { command: "build", env: { MESHCHAT_VUE_DEVTOOLS: "1" }, expected: false },
            { command: undefined, env: {}, expected: false },
        ];
        for (const input of cases) {
            expect(isVueDevToolsEnabled({ command: input.command, env: input.env }), JSON.stringify(input)).toBe(
                input.expected
            );
        }
    });

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

    it("vite.config.js wires the plugin, production DevTools flag, and localhost server", () => {
        const vite = readFileSync(resolve(ROOT, "vite.config.js"), "utf8");
        expect(vite).toContain('from "vite-plugin-vue-devtools"');
        expect(vite).toContain("isVueDevToolsEnabled({ command })");
        expect(vite).toContain('__VUE_PROD_DEVTOOLS__: "false"');
        expect(vite).toContain("sourcemap: false");
        expect(vite).toContain("devSourcemap: true");
        expect(vite).toContain('host: "127.0.0.1"');
        expect(vite).toContain("strictPort: true");
        expect(vite).toContain("clearScreen: false");
        expect(vite).toContain('forwardConsole: command === "serve"');
        expect(vite).toContain("chunkImportMap: false");
        expect(vite).toContain("tsconfigPaths: true");
        expect(vite).toContain("MESHCHAT_VITE_BUNDLED_DEV");
        expect(vite).toContain("bundledDev: true");
    });

    it("Docker frontend stages copy every vite.config.js scripts/ import", () => {
        const vite = readFileSync(resolve(ROOT, "vite.config.js"), "utf8");
        const imports = [...vite.matchAll(/from\s+"(\.\/scripts\/[^"]+)"/g)].map((m) => m[1].replace(/^\.\//, ""));
        expect(imports.length).toBeGreaterThan(0);
        expect(imports).toContain("scripts/vite-dx.mjs");
        for (const dockerfile of ["Dockerfile", "Dockerfile.hardened"]) {
            const body = readFileSync(resolve(ROOT, dockerfile), "utf8");
            const frontendStage = body.split(/^FROM /m)[1] || "";
            for (const rel of imports) {
                expect(frontendStage, `${dockerfile} missing COPY ${rel}`).toContain(`COPY ${rel} ${rel}`);
            }
        }
    });

    it("e2e Vite stack disables Vue DevTools", () => {
        const e2e = readFileSync(resolve(ROOT, "scripts/e2e/start-e2e-stack.sh"), "utf8");
        expect(e2e).toContain("MESHCHAT_VUE_DEVTOOLS=0");
    });

    it("package.json lists vite-plugin-vue-devtools as a devDependency", () => {
        const pkg = JSON.parse(readFileSync(resolve(ROOT, "package.json"), "utf8"));
        expect(pkg.devDependencies["vite-plugin-vue-devtools"]).toBeTruthy();
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
