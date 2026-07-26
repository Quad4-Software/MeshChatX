// SPDX-License-Identifier: 0BSD

/**
 * Adversarial fuzz and membership oracles for locale/theme regressions.
 */

import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, it, expect } from "vitest";
import { listLocaleCodes, normalizeUiLocaleCode } from "../../meshchatx/src/frontend/js/localeLoader.js";
import { uiLocalePackOracle } from "../../meshchatx/src/frontend/js/localeThemeOracles.js";

const ROOT = resolve(import.meta.dirname, "../..");

function readSource(rel) {
    return readFileSync(resolve(ROOT, rel), "utf8");
}

function mulberry32(seed) {
    let t = seed >>> 0;
    return () => {
        t += 0x6d2b79f5;
        let r = Math.imul(t ^ (t >>> 15), 1 | t);
        r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
        return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
}

function randomUnicodeString(rng, maxLen) {
    const len = Math.floor(rng() * maxLen);
    let s = "";
    for (let i = 0; i < len; i += 1) {
        const pick = Math.floor(rng() * 4);
        if (pick === 0) {
            s += String.fromCharCode(32 + Math.floor(rng() * 95));
        } else if (pick === 1) {
            s += String.fromCharCode(0x0400 + Math.floor(rng() * 64));
        } else if (pick === 2) {
            s += String.fromCharCode(0x4e00 + Math.floor(rng() * 64));
        } else {
            s += ["\u0000", "\n", "\t", "/", "\\", "..", "<script>", "🚀"][Math.floor(rng() * 8)];
        }
    }
    return s;
}

function extractMethodBody(src, methodName) {
    const startRe = new RegExp(`async\\s+${methodName}\\s*\\([^)]*\\)\\s*\\{`);
    const start = src.search(startRe);
    if (start < 0) {
        return "";
    }
    let depth = 0;
    let i = src.indexOf("{", start);
    const begin = i;
    for (; i < src.length; i += 1) {
        const ch = src[i];
        if (ch === "{") {
            depth += 1;
        } else if (ch === "}") {
            depth -= 1;
            if (depth === 0) {
                return src.slice(begin + 1, i);
            }
        }
    }
    return "";
}

const DOC_MANUAL_LANGS = ["en", "de", "es", "jp", "nl", "pl", "pt-br", "tr", "uk", "zh-cn"];
const RETICULUM_ONLY = DOC_MANUAL_LANGS.filter((code) => !listLocaleCodes().includes(code));

describe("localeTheme adversarial / fuzz", () => {
    it("fuzz: normalizeUiLocaleCode never throws and oracle pack membership holds", () => {
        const packs = new Set(listLocaleCodes());
        const rng = mulberry32(0x1a2b3c4d);
        for (let n = 0; n < 600; n += 1) {
            const raw =
                n < RETICULUM_ONLY.length
                    ? RETICULUM_ONLY[n]
                    : n % 5 === 0
                      ? null
                      : n % 7 === 0
                        ? undefined
                        : randomUnicodeString(rng, 48);
            const code = uiLocalePackOracle(raw);
            expect(packs.has(code)).toBe(true);
            expect(typeof normalizeUiLocaleCode(raw)).toBe("string");
        }
    });

    it("oracle: Reticulum-only manual codes must not equal normalized UI pack", () => {
        for (const docLang of RETICULUM_ONLY) {
            const ui = normalizeUiLocaleCode(docLang);
            expect(ui).not.toBe(docLang);
            expect(listLocaleCodes()).toContain(ui);
        }
    });

    it("contract: App updateConfig prefers HTTP PATCH when window.api is available", () => {
        const app = readSource("meshchatx/src/frontend/components/App.vue");
        const body = extractMethodBody(app, "updateConfig");
        expect(body).toContain("patchServerConfig");
        expect(body).toMatch(/if\s*\(\s*window\.api\?\.patch\s*\)/);
        const patchIdx = body.indexOf("patchServerConfig");
        const wsIdx = body.indexOf("WebSocketConnection.send");
        if (wsIdx >= 0) {
            expect(patchIdx).toBeGreaterThan(-1);
            expect(patchIdx).toBeLessThan(wsIdx);
        }
    });

    it("contract: DocsPage setLanguage does not PATCH config.language", () => {
        const docs = readSource("meshchatx/src/frontend/components/docs/DocsPage.vue");
        const body = extractMethodBody(docs, "setLanguage");
        expect(body).not.toContain("api.patch");
        expect(body).not.toContain("config.language");
        expect(body).toContain("reticulumDocsLang");
    });

    it("contract: CallPage requestAudioPermission prompts getUserMedia before refreshAudioDevices", () => {
        const call = readSource("meshchatx/src/frontend/components/call/CallPage.vue");
        const body = extractMethodBody(call, "requestAudioPermission");
        const gum = body.indexOf("getUserMedia");
        const refresh = body.indexOf("refreshAudioDevices");
        const enumerateCall = body.indexOf(".enumerateDevices(");
        expect(gum).toBeGreaterThan(-1);
        expect(refresh).toBeGreaterThan(gum);
        if (enumerateCall >= 0) {
            expect(enumerateCall).toBeGreaterThan(gum);
        }
        const beforeGum = body.slice(0, gum);
        expect(beforeGum).not.toMatch(/\.enumerateDevices\s*\(/);
        expect(beforeGum).not.toContain("no_audio_input_found");
        expect(body).toMatch(/getUserMedia\(\{\s*audio:\s*true\s*\}/);
    });

    it("contract: localeLoader setLocale normalizes before loading messages", () => {
        const loader = readSource("meshchatx/src/frontend/js/localeLoader.js");
        expect(loader).toContain("normalizeUiLocaleCode");
        expect(loader).toMatch(/export async function setLocale[\s\S]*normalizeUiLocaleCode/);
    });

    it("contract: WebGL engine clears background when WASM buffers are not ready", () => {
        const engine = readSource("meshchatx/src/frontend/js/networkVisualiserWebGLEngine.js");
        expect(engine).toMatch(/buf\.ok === false[\s\S]*clearBackground/);
    });

    it("contract: security middleware sets Permissions-Policy for microphone", () => {
        const mw = readSource("meshchatx/src/backend/http/middleware.py");
        expect(mw).toContain("Permissions-Policy");
        expect(mw).toContain("microphone=(self)");
        expect(mw).toContain("bluetooth=(self)");
        expect(mw).toContain("serial=(self)");
        expect(mw).toContain("usb=(self)");
    });
});
